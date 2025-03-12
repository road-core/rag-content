# Road RAG content

# Generating the RAG for OpenShift

This guide outlines the steps for generating an example OpenShift Lightspeed
database for RAG.

The database can be generated manually, or in a container.

## Generate database in a container

Container base generation entails simply calling the appropriate make target:

```
make build-image-ocp-example
```

## Manual database generation

Install the dependencies and activate the virtualenv:

```
pdm install
source .venv/bin/activate
```

### Download the OCP documentation

The command below downloads the OCP documentation version 4.15 and
converts it to plain text:

```
./scripts/get_ocp_plaintext_docs.sh 4.15
```

Note, this step requires the command "asciidoctor" to be installed. See
https://docs.asciidoctor.org/asciidoctor/latest/install for installation
instructions.

### Download the runbooks

Download the runbooks by running the following script:

```
./scripts/get_runbooks.sh
```

### Download the embedding model

The embedding model used by OpenShift Lightspeed is the
**sentence-transformers/all-mpnet-base-v2**, in order to download it run
the following command:

```
./scripts/download_embeddings_model.py -l ./embeddings_model/ -r sentence-transformers/all-mpnet-base-v2
```

### Generating the RAG vector database

You can generate the RAG vector database either using

1. [Faiss Vector Store](#faiss-vector-store), or
2. [Postgres (PGVector) Vector Store](#postgres-pgvector-vector-store)

#### Faiss Vector Store

In order to generate the RAG vector database using 
Faiss Vector Store with
the
**sentend-transformers/all-mpnet-base-v2** embedding model and OpenShift
documentation version 4.15 run the following commands:

```
mkdir -p vector_db/ocp_product_docs/4.15

./scripts/generate_embeddings_openshift.py -o ./vector_db/ocp_product_docs/4.15 -f ocp-product-docs-plaintext/4.15/ -r runbooks/ -md embeddings_model/ -mn sentence-transformers/all-mpnet-base-v2 -v 4.15 -i ocp-product-docs-4_15
```

Once the command is done, you can find the vector database at
**vector_db/**, the embedding model at **embeddings_model/** and the
Index ID set to **ocp-product-docs-4_15**.

These dictories and index ID can now be used to configure OpenShift
Lightspeed.

#### Postgres (PGVector) Vector Store

In order to generate the RAG vector database using 
Postgres (PGVector) Vector Store run the following commands:

1. Start Postgres with the pgvector extension by running
    ```
    make start-postgres-debug
    ```
   The `data` folder of Postgres is created at
   `./postgresql/data`. This command also creates `./output` for the 
   output directory, in which the metadata is saved.
2. Run
    ```
    make generate-embeddings-postgres
    ```
   which generates embeddings on Postgres, which can be used for RAG, and `metadata.json`
   in `./output`. Generated embeddings are stored in the `data_ocp_product_docs_4_15` table
   on the Postgres DB.

   ```commandline
   $ podman exec -it pgvector bash
   root@42b7f8fcfe9b:/# psql -U postgres
   psql (16.4 (Debian 16.4-1.pgdg120+2))
   Type "help" for help.
   
   postgres=# \dt
                      List of relations
    Schema |            Name            | Type  |  Owner   
   --------+----------------------------+-------+----------
    public | data_ocp_product_docs_4_15 | table | postgres
   (1 row)
   
   postgres=#
   ```

## `requirements*` files generation for conflux

In order to generate all requirements files:

```
requirements-build.in
requirements-build.txt
requirements.txt
```

The following command must be executed:

```bash
scripts/generate_packages_to_prefetch.py
```