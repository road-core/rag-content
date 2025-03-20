# Copyright 2025 Red Hat, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""Metadata handling for document nodes in vector database."""

import abc
import logging
from typing import Dict

import requests

LOG = logging.getLogger(__name__)


class MetadataProcessor:
    """Metadata processing callback.

    Projects should make their own metadata processors.
    Specifically, the `url_function` which is meant to derive URL
    from name of a document, is not implemented.
    """

    def get_file_title(self, file_path: str) -> str:
        """Extract title from the plaintext doc file."""
        title = ""
        try:
            with open(file_path, "r") as file:
                title = file.readline().rstrip("\n").lstrip("# ")
        except Exception:  # noqa: S110
            pass
        return title

    def ping_url(self, url: str) -> bool:
        """Check if the URL parameter is live."""
        try:
            response = requests.get(url, timeout=30)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def populate(self, file_path: str) -> Dict:
        """Populate title and metadata with docs URL.

        Populate the docs_url and title metadata elements with docs URL
        and the page's title.

        Args:
            file_path: str: file path in str
        """
        docs_url = self.url_function(file_path)
        title = self.get_file_title(file_path)

        document = {
            "file_path": file_path,
            "title": title,
            "url": docs_url,
        }

        if not self.ping_url(docs_url):
            LOG.warning(
                'URL not reachable: %(url)s (Title: "%(title)s", '
                "File path: %(file_path)s)",
                document,
            )

        LOG.debug(
            'Metadata populated for: "%(title)s" (URL: %(url)s, File '
            "path: %(file_path)s)",
            document,
        )

        return {"docs_url": docs_url, "title": title}

    @abc.abstractmethod
    def url_function(self, file_path: str) -> str:
        """Derive URL to document source from given file path."""
        raise NotImplementedError
