#!/bin/bash
set -eou pipefail

RHDH_VERSION=$1

trap "rm -rf red-hat-developers-documentation-rhdh" EXIT

rm -rf rhdh-product-docs-plaintext/${RHDH_VERSION}
rm -rf rhdh-docs-topic-map

git clone --single-branch --branch release-${RHDH_VERSION} https://github.com/redhat-developer/red-hat-developers-documentation-rhdh

git clone --single-branch --branch release-${RHDH_VERSION} https://github.com/redhat-ai-dev/rhdh-docs-topic-map

python examples/asciidoctor_text/convert_adoc_to_txt_rhdh.py \
    -i red-hat-developers-documentation-rhdh \
    -o rhdh-product-docs-plaintext/${RHDH_VERSION} \
    -t rhdh-docs-topic-map/rhdh_topic_map.yaml
