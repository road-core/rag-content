# Default to CPU if not specified
FLAVOR ?= cpu
NUM_WORKERS ?= $$(( $(shell nproc --all) / 2))

# Define behavior based on the flavor
ifeq ($(FLAVOR),cpu)
TORCH_GROUP := cpu
else ifeq ($(FLAVOR),gpu)
TORCH_GROUP := gpu
else
$(error Unsupported FLAVOR $(FLAVOR), must be 'cpu' or 'gpu')
endif

install-tools: ## Install required utilities/tools
	@command -v pdm > /dev/null || { echo >&2 "pdm is not installed. Installing..."; pip3.11 install --upgrade pip pdm; }

pdm-lock-check: ## Check that the pdm.lock file is in a good shape
	pdm lock --check --group $(TORCH_GROUP) --lockfile pdm.lock.$(TORCH_GROUP)

install-hooks: install-deps-test ## Install commit hooks
	pdm run pre-commit install

install-deps: install-tools pdm-lock-check ## Install all required dependencies, according to pdm.lock
	pdm sync --group $(TORCH_GROUP) --lockfile pdm.lock.$(TORCH_GROUP)

install-deps-test: install-tools pdm-lock-check ## Install all required dev dependencies, according to pdm.lock
	pdm sync --dev --group $(TORCH_GROUP) --lockfile pdm.lock.$(TORCH_GROUP)

update-deps: ## Check pyproject.toml for changes, update the lock file if needed, then sync.
	pdm install --group $(TORCH_GROUP) --lockfile pdm.lock.$(TORCH_GROUP)
	pdm install --dev --group $(TORCH_GROUP) --lockfile pdm.lock.$(TORCH_GROUP)

check-types: ## Checks type hints in sources
	pdm run mypy --explicit-package-bases --disallow-untyped-calls --disallow-untyped-defs --disallow-incomplete-defs scripts

format: ## Format the code into unified format
	pdm run black scripts
	pdm run ruff check scripts --fix --per-file-ignores=scripts/*:S101
	pdm run pre-commit run

verify: check-types ## Verify the code using various linters
	pdm run black --check scripts
	pdm run ruff check scripts --per-file-ignores=scripts/*:S101

update-docs: ## Update the plaintext OCP docs in ocp-product-docs-plaintext/
	@set -e && for OCP_VERSION in $$(ls -1 ocp-product-docs-plaintext); do \
		scripts/get_ocp_plaintext_docs.sh $$OCP_VERSION; \
	done
	scripts/get_runbooks.sh

build-image-ocp-example: build-base-image ## Build a rag-content container image
	podman build -t rag-content -f examples/Containerfile.ocp_lightspeed --build-arg FLAVOR=$(TORCH_GROUP) --build-arg NUM_WORKERS=$(NUM_WORKERS) .

build-base-image: ## Build base container image
	podman build -t $(TORCH_GROUP)-road-core-base -f Containerfile.base --build-arg FLAVOR=$(TORCH_GROUP)

help: ## Show this help screen
	@echo 'Usage: make <OPTIONS> ... <TARGETS>'
	@echo ''
	@echo 'Available targets are:'
	@echo ''
	@grep -E '^[ a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ''
