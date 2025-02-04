#!/usr/bin/env python3

"""Utility script to generate embeddings."""

import multiprocessing
import os
import sys
import time
from typing import Dict

# Add the common_embedding.py to the Python path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(scripts_dir)

from common_embeddings import (
    file_metadata_func,
    get_common_arg_parser,
    filter_out_invalid_nodes,
    save_index,
    save_metadata,
    process_documents,
    get_settings,
    print_unreachable_docs_warning
)

# The OpenStack documentation base URL
OS_DOCS_ROOT_URL = "https://docs.openstack.org"


class OSMetadata(object):

    def __init__(self, docs_dir, base_url):
        super(OSMetadata, self).__init__()
        self._base_path = os.path.abspath(docs_dir)
        if self._base_path.endswith('/'):
            self._base_path = self._base_path[:-1]

        self.base_url = base_url

    def set_metadata(self, file_path: str) -> Dict:
        """Populate metadata for an OpenStack documentation page.

        Args:
            file_path: str: file path in str
        """
        docs_url = lambda file_path: (  # noqa: E731
            self.base_url
            + file_path.removeprefix(self._base_path).removesuffix("txt")
            + "html"
        )
        return file_metadata_func(file_path, docs_url)


if __name__ == "__main__":

    start_time = time.time()

    parser = get_common_arg_parser()
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=multiprocessing.cpu_count(),
        help=("Number of workers (defaults to number of CPUs) to parallelize "
              "the data loading. Set to a negative value to disable."))
    args = parser.parse_args()
    print(f"Arguments used: {args}")

    # OLS-823: sanitize directory
    PERSIST_FOLDER = os.path.normpath("/" + args.output).lstrip("/")
    if PERSIST_FOLDER == "":
        PERSIST_FOLDER = "."

    os.environ["HF_HOME"] = args.model_dir
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    settings, embedding_dimension, storage_context = get_settings(
        args.chunk, args.overlap, args.model_dir)

    # Load documents
    os_metadata = OSMetadata(args.folder, OS_DOCS_ROOT_URL)
    documents = process_documents(
        args.folder, metadata_func=os_metadata.set_metadata,
        required_exts=['.txt',], num_workers=args.workers)

    # Create chunks/nodes
    nodes = settings.text_splitter.get_nodes_from_documents(documents)

    # Filter out invalid nodes
    good_nodes = filter_out_invalid_nodes(nodes)

    # Create & save Index
    save_index(good_nodes, storage_context, args.index, PERSIST_FOLDER)

    # Save metadata
    save_metadata(start_time, args, embedding_dimension, documents,
                  PERSIST_FOLDER)

    print_unreachable_docs_warning()
