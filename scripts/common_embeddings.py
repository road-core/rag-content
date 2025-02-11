#!/usr/bin/env python3

"""Common code for generating embeddings."""

import argparse
import json
import os
import time
from typing import Callable, Dict, List, Sequence, Tuple
from pathlib import Path

import faiss
from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.llms.utils import resolve_llm
from llama_index.core.schema import TextNode, BaseNode

from llama_index.core.storage.storage_context import StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore
import requests


def ping_url(url: str) -> bool:
    """Check if the URL parameter is live."""
    try:
        response = requests.get(url, timeout=30)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def get_file_title(file_path: str) -> str:
    """Extract title from the plaintext doc file."""
    title = ""
    try:
        with open(file_path, "r") as file:
            title = file.readline().rstrip("\n").lstrip("# ")
    except Exception:  # noqa: S110
        pass
    return title

class FileMetadataProcessor:
    """Metadata processing callback with memory of unreachable URLS.
    FileMetadataProcessor keeps a list of processed files,
    their titles, URLs and if their URLs were reachable.

    Projects should make their own metadata processors.
    Specifically, the `url_function` which is meant to derive URL
    from name of a document, is not implemented.
    """

    def __init__(self):
        self.processed_urls = []

    def url_function(self, file_path: str) -> str:
        """This function must be implemeted in the derived class
        """
        raise NotImplementedError

    def n_unreachable_urls(self) -> int:
        """Return number of unreachable documents.
        """
        return len([e for e in self.processed_urls if e["unreachable"]])

    def file_metadata_func(self, file_path: str) -> Dict:
        """Populate title and metadata with docs URL.

        Populate the docs_url and title metadata elements with docs URL
        and the page's title.

        Args:
            file_path: str: file path in str
        """
        docs_url = self.url_function(file_path)
        title = get_file_title(file_path)

        document = {
            "file_path": file_path,
            "title": title,
            "docs_url": docs_url,
            "unreachable": False}

        if not ping_url(docs_url):
            document["unreachable"] = True
        self.processed_urls.append(document)

        print(f"{document}")

        return {"docs_url": docs_url, "title": title}


def get_common_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Embedding CLI for task execution")
    parser.add_argument(
        "-f",
        "--folder",
        help="Directory containing the plain text documentation")
    parser.add_argument(
        "-md",
        "--model-dir",
        default="embeddings_model",
        help="Directory containing the embedding model")
    parser.add_argument(
        "-mn",
        "--model-name",
        help="HF repo id of the embedding model")
    parser.add_argument(
        "-c",
        "--chunk",
        type=int,
        default=380,
        help="Chunk size for embedding")
    parser.add_argument(
        "-l",
        "--overlap",
        type=int,
        default=0,
        help="Chunk overlap for embedding")
    parser.add_argument(
        "-em",
        "--exclude-metadata",
        nargs="+",
        default=None,
        help="Metadata to be excluded during embedding")
    parser.add_argument(
        "-o",
        "--output",
        help="Vector DB output folder")
    parser.add_argument(
        "-i",
        "--index",
        help="Product index")
    parser.add_argument(
        "-w",
        "--workers",
        default=-1,
        type=int,
        help=("Number of workers to parallelize the data loading. Set to a "
              "negative value by default, turning parallelism off")
    )
    return parser


def got_whitespace(text: str) -> bool:
    """Indicate if the parameter string contains whitespace."""
    for c in text:
        if c.isspace():
            return True
    return False


def filter_out_invalid_nodes(nodes) -> List:
    """Filter out invalid nodes."""
    good_nodes = []
    for node in nodes:
        if isinstance(node, TextNode) and got_whitespace(node.text):
            # Exclude given metadata during embedding
            # if args.exclude_metadata is not None:
            #     node.excluded_embed_metadata_keys.extend(args.exclude_metadata)
            good_nodes.append(node)
        else:
            print("Skipping node without whitespace: " + repr(node))
    return good_nodes


def save_index(
        nodes: Sequence[BaseNode], storage_context: StorageContext, index: str, persist_folder: str) -> None:
    """Create and save the Vector Store Index"""

    idx = VectorStoreIndex(
        nodes,
        storage_context=storage_context,
    )
    idx.set_index_id(index)
    idx.storage_context.persist(persist_dir=persist_folder)


def save_metadata(start_time: float, args: argparse.Namespace, embedding_dimension: int,
                  documents: SimpleDirectoryReader, persist_folder: str) -> None:
    """Create and save the metadata"""
    metadata: dict = {}
    metadata["execution-time"] = time.time() - start_time
    metadata["llm"] = "None"
    metadata["embedding-model"] = args.model_name
    metadata["index-id"] = args.index
    metadata["vector-db"] = "faiss.IndexFlatIP"
    metadata["embedding-dimension"] = embedding_dimension
    metadata["chunk"] = args.chunk
    metadata["overlap"] = args.overlap
    metadata["total-embedded-files"] = len(documents)

    with open(os.path.join(persist_folder, "metadata.json"), "w") as file:
        file.write(json.dumps(metadata))


def process_documents(docs_dir: Path, metadata_func: Callable,
                      required_exts : List[str] | None = None,
                      file_extractor: Dict | None = None,
                      num_workers: int = 0) -> SimpleDirectoryReader:

    if num_workers <= 0:
        num_workers = None

    return SimpleDirectoryReader(
        docs_dir,
        recursive=True,
        file_metadata=metadata_func,
        required_exts=required_exts,
        file_extractor=file_extractor).load_data(num_workers=num_workers)


def get_settings(chunk_size: int, chunk_overlap: int, model_dir: str) -> Tuple:
    Settings.chunk_size = chunk_size
    Settings.chunk_overlap = chunk_overlap
    Settings.embed_model = HuggingFaceEmbedding(model_name=model_dir)
    Settings.llm = resolve_llm(None)

    embedding_dimension = len(Settings.embed_model.get_text_embedding(
        "random text"))
    faiss_index = faiss.IndexFlatIP(embedding_dimension)
    vector_store = FaissVectorStore(faiss_index=faiss_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    return Settings, embedding_dimension, storage_context


def print_unreachable_docs_warning(n_unreachable_urls: int = 0):

    print("WARNING:\n"
        f"There were documents with {n_unreachable_urls} unreachable URLs, "
        "grep the log for UNREACHABLE.\n"
        "Please update the plain text."
    )
