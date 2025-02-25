#!/usr/bin/env python3
"""Utility script to generate embeddings."""

import os
import sys
import time

from llama_index.readers.file.flat.base import FlatReader

# Add the common_embedding.py to the Python path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(scripts_dir)

from common_embeddings import (
    filter_out_invalid_nodes,
    get_common_arg_parser,
    get_settings,
    process_documents,
    save_index,
    save_metadata,
)


if __name__ == "__main__":

    start_time = time.time()
    parser = get_common_arg_parser()
    args = parser.parse_args()
    print(f"Arguments used: {args}")

    # OLS-823: sanitize directory
    PERSIST_FOLDER = os.path.normpath("/" + args.output).lstrip("/")
    if PERSIST_FOLDER == "":
        PERSIST_FOLDER = "."

    EMBEDDINGS_ROOT_DIR = os.path.abspath(args.folder)
    if EMBEDDINGS_ROOT_DIR.endswith("/"):
        EMBEDDINGS_ROOT_DIR = EMBEDDINGS_ROOT_DIR[:-1]

    os.environ["HF_HOME"] = args.model_dir
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    settings, embedding_dimension, storage_context = get_settings(
        args.chunk, args.overlap, args.model_dir, args.vector_store_type, args.index,
    )

    def get_meta(file_path):
        return {"foo": "bar", "file_path": file_path}

    # Load documents
    documents = process_documents(
        args.folder,
        metadata_func=get_meta,
        num_workers=args.workers,
    )

    # Create chunks/nodes
    nodes = settings.text_splitter.get_nodes_from_documents(documents)

    # Filter out invalid nodes
    good_nodes = filter_out_invalid_nodes(nodes)

    # Create & save Index
    save_index(good_nodes, storage_context, args.index, PERSIST_FOLDER)

    # Save metadata
    save_metadata(start_time, args, embedding_dimension, documents, PERSIST_FOLDER)
