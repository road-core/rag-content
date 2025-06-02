#!/usr/bin/env python3
"""Utility script to generate RHDH embeddings."""

import logging
import os
import yaml

from lightspeed_rag_content import utils
from lightspeed_rag_content.metadata_processor import MetadataProcessor
from lightspeed_rag_content.document_processor import DocumentProcessor

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


RHDH_DOCS_ROOT_URL = "https://docs.redhat.com/en/documentation/red_hat_developer_hub/"
RHDH_DOCS_VERSION = "1.6"


def process_node(node: dict, dir: str = "", file_url_list: dict = {}) -> dict:
    """Process YAML node from the topic map."""
    currentdir = dir
    if "Topics" in node:
        currentdir = os.path.join(currentdir, node["Dir"])
        for subnode in node["Topics"]:
            file_url_list = process_node(
                subnode, dir=currentdir, file_url_list=file_url_list
            )
    else:
        dir_basename = os.path.basename(currentdir)
        file_url_list[dir_basename] = node["WebpageID"]
    return file_url_list

class RHDHDocsMetadata(MetadataProcessor):
    """Generates metadata from plaintext documentation."""

    def __init__(self, root_dir: str, rhdh_docs_version: str, topic_map: str):
        super().__init__()
        self.root_dir = root_dir
        self.rhdh_docs_version = rhdh_docs_version
        self.topic_map = topic_map
        self.file_url_list: dict = {}

        with open(topic_map, "r") as fin:
            topic_map = yaml.safe_load_all(fin)
            for map in topic_map:
                self.file_url_list = process_node(map, file_url_list=self.file_url_list)

    def url_function(self, file_path: str):

        dir_basename = os.path.basename(os.path.dirname(file_path))

        return (
            RHDH_DOCS_ROOT_URL
            + self.rhdh_docs_version
            + "/html-single/"
            + self.file_url_list[dir_basename]
            + "/index"
        )


if __name__ == "__main__":
    parser = utils.get_common_arg_parser()
    parser.add_argument(
        "-v", "--rhdh-version", help="RHDH version", default=RHDH_DOCS_VERSION
    )
    parser.add_argument("--topic-map", "-t", required=True, help="The topic map file")
    args = parser.parse_args()
    print(f"Arguments used: {args}")

    topic_map = os.path.normpath(os.path.join(os.getcwd(), args.topic_map))

    # OLS-823: sanitize directory
    PERSIST_FOLDER = os.path.normpath("/" + args.output).lstrip("/")
    if PERSIST_FOLDER == "":
        PERSIST_FOLDER = "."

    EMBEDDINGS_ROOT_DIR = os.path.abspath(args.folder)
    if EMBEDDINGS_ROOT_DIR.endswith("/"):
        EMBEDDINGS_ROOT_DIR = EMBEDDINGS_ROOT_DIR[:-1]

    # Instantiate Metadata Processor
    print("Instantiate Metadata Processor")
    metadata_processor = RHDHDocsMetadata(EMBEDDINGS_ROOT_DIR, args.rhdh_version, topic_map)
    
    # Instantiate Document Processor
    print("Instantiate Document Processor")
    document_processor = DocumentProcessor(
        args.chunk, args.overlap, args.model_name, args.model_dir, args.workers,
        args.vector_store_type, args.index.replace("-", "_"),
    )
    
    # Process RHDH documents
    print("Process RHDH documents")
    document_processor.process(args.folder, metadata=metadata_processor)
    
    # Save to the output directory
    document_processor.save(args.index, PERSIST_FOLDER)
    