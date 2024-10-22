ARG EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
ARG HERMETIC=false

FROM registry.access.redhat.com/ubi9/python-311 as lightspeed-rag-builder
ARG EMBEDDING_MODEL
ARG HERMETIC

USER 0
WORKDIR /workdir

COPY requirements.txt .
RUN pip3.11 install --no-cache-dir -r requirements.txt

COPY ocp-product-docs-plaintext ./ocp-product-docs-plaintext
COPY runbooks ./runbooks

COPY embeddings_model ./embeddings_model
RUN cat embeddings_model/model.safetensors.part* > embeddings_model/model.safetensors && rm embeddings_model/model.safetensors.part*

COPY scripts/generate_embeddings.py .
RUN set -e && for OCP_VERSION in $(ls -1 ocp-product-docs-plaintext); do \
        python3.11 generate_embeddings.py -f ocp-product-docs-plaintext/${OCP_VERSION} -r runbooks/alerts -md embeddings_model \
            -mn ${EMBEDDING_MODEL} -o vector_db/ocp_product_docs/${OCP_VERSION} \
            -i ocp-product-docs-$(echo $OCP_VERSION | sed 's/\./_/g') -v ${OCP_VERSION} -hb $HERMETIC; \
    done

FROM registry.access.redhat.com/ubi9/ubi-minimal@sha256:c0e70387664f30cd9cf2795b547e4a9a51002c44a4a86aa9335ab030134bf392
COPY --from=lightspeed-rag-builder /workdir/vector_db/ocp_product_docs /rag/vector_db/ocp_product_docs
COPY --from=lightspeed-rag-builder /workdir/embeddings_model /rag/embeddings_model

# this directory is checked by ecosystem-cert-preflight-checks task in Konflux
RUN mkdir /licenses
COPY LICENSE /licenses/

# Labels for enterprise contract
LABEL com.redhat.component=openshift-lightspeed-rag-content
LABEL description="Red Hat OpenShift Lightspeed RAG content"
LABEL distribution-scope=private
LABEL io.k8s.description="Red Hat OpenShift Lightspeed RAG content"
LABEL io.k8s.display-name="Openshift Lightspeed RAG content"
LABEL io.openshift.tags="openshift,lightspeed,ai,assistant,rag"
LABEL name=openshift-lightspeed-rag-content
LABEL release=0.0.1
LABEL url="https://github.com/openshift/lightspeed-rag-content"
LABEL vendor="Red Hat, Inc."
LABEL version=0.0.1
LABEL summary="Red Hat OpenShift Lightspeed RAG content"

USER 65532:65532
