#!/usr/bin/env python3
"""Utility script to generate embeddings."""

import os
import sys
import time
from typing import Dict

from llama_index.readers.file.flat.base import FlatReader

# Add the common_embedding.py to the Python path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(scripts_dir)

from common_embeddings import (
    FileMetadataProcessor,
    get_common_arg_parser,
    filter_out_invalid_nodes,
    save_index,
    save_metadata,
    process_documents,
    get_settings,
    print_unreachable_docs_warning
)

OCP_DOCS_ROOT_URL = "https://docs.openshift.com/container-platform/"
OCP_DOCS_VERSION = "4.15"
RUNBOOKS_ROOT_URL = "https://github.com/openshift/runbooks/blob/master/alerts"


class OpenshiftDocsMetadata(FileMetadataProcessor):

    """Generates metadata from plaintext Openshift documentation.
    """
    def __init__(self, root_dir: str, ocp_docs_version: str):
        super().__init__()
        self.root_dir = root_dir
        self.ocp_docs_version = ocp_docs_version

    def url_function(self, file_path: str):

        return (  # noqa: E731
            OCP_DOCS_ROOT_URL
            + self.ocp_docs_version
            + file_path.removeprefix(self.root_dir).removesuffix("txt")
            + "html"
        )


class OpenshiftRunbooksMetadata(FileMetadataProcessor):

    def __init__(self, root_dir: str):
        super().__init__()
        self.root_dir = root_dir

    def url_function(self, file_path: str):

        return self.root_dir + file_path.removeprefix(self.root_dir)


if __name__ == "__main__":

    start_time = time.time()
    parser = get_common_arg_parser()
    parser.add_argument("-r", "--runbooks", help="Runbooks folder path")
    parser.add_argument("-v", "--ocp-version", help="OCP version", default=OCP_DOCS_VERSION)
    args = parser.parse_args()
    print(f"Arguments used: {args}")

    # OLS-823: sanitize directory
    PERSIST_FOLDER = os.path.normpath("/" + args.output).lstrip("/")
    if PERSIST_FOLDER == "":
        PERSIST_FOLDER = "."

    EMBEDDINGS_ROOT_DIR = os.path.abspath(args.folder)
    if EMBEDDINGS_ROOT_DIR.endswith("/"):
        EMBEDDINGS_ROOT_DIR = EMBEDDINGS_ROOT_DIR[:-1]
    RUNBOOKS_ROOT_DIR = os.path.abspath(args.runbooks)
    if RUNBOOKS_ROOT_DIR.endswith("/"):
        RUNBOOKS_ROOT_DIR = RUNBOOKS_ROOT_DIR[:-1]

    os.environ["HF_HOME"] = args.model_dir
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    settings, embedding_dimension, storage_context = get_settings(
        args.chunk, args.overlap, args.model_dir)

    metadata_processor = OpenshiftDocsMetadata(EMBEDDINGS_ROOT_DIR, args.ocp_version)

    # Load documents
    documents = process_documents(
        args.folder, metadata_func=metadata_processor.file_metadata_func, num_workers=args.workers)

    unreachables = metadata_processor.n_unreachable_urls()
    # Create chunks/nodes
    nodes = settings.text_splitter.get_nodes_from_documents(documents)

    # Filter out invalid nodes
    good_nodes = filter_out_invalid_nodes(nodes)
    metadata_processor = OpenshiftRunbooksMetadata(RUNBOOKS_ROOT_DIR)

    # Load runbook documents
    runbook_documents = process_documents(
        args.runbooks, metadata_func=metadata_processor.file_metadata_func,
        num_workers=args.workers, required_exts=['.md',], file_extractor={".md": FlatReader()})
    unreachables += metadata_processor.n_unreachable_urls()
    # Create chunks/nodes
    runbook_nodes = settings.text_splitter.get_nodes_from_documents(runbook_documents)

    # Extend nodes with runbook_nodes
    good_nodes.extend(runbook_nodes)

    # Create & save Index
    save_index(good_nodes, storage_context, args.index, PERSIST_FOLDER)

    # Save metadata
    save_metadata(start_time, args, embedding_dimension, documents,
                  PERSIST_FOLDER)

    if unreachables > 0:
        print_unreachable_docs_warning(unreachables)
