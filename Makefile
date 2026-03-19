SHELL := /bin/bash
.DEFAULT_GOAL := help

UNIT_GLOB ?= tests/units/*_test.yaml
SMOKE_ARGS ?=
E2E_ARGS ?=
EXAMPLE_VALUES ?= tests/smokes/fixtures/example.values.yaml

.PHONY: help
help: ## Show available local targets
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_.-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: lint
lint: ## Run helm lint with the representative example values file
	helm dependency build .
	helm lint . -f $(EXAMPLE_VALUES)

.PHONY: test
test: test-unit test-smoke-fast ## Run local fast checks

.PHONY: test-unit
test-unit: ## Run helm-unittest suites from tests/units
	helm dependency build .
	helm unittest -f '$(UNIT_GLOB)' .

.PHONY: test-compat
test-compat: ## Run backward compatibility checks against previous tags
	helm dependency build .
	sh tests/units/backward_compatibility_test.sh

.PHONY: test-smoke
test-smoke: ## Run all smoke scenarios; append SMOKE_ARGS='--scenario example-render'
	python3 tests/smokes/run/smoke.py $(SMOKE_ARGS)

.PHONY: test-smoke-fast
test-smoke-fast: ## Run the fast smoke scenarios
	python3 tests/smokes/run/smoke.py \
		--scenario default-empty \
		--scenario rendering-contract \
		--scenario example-render \
		$(SMOKE_ARGS)

.PHONY: test-e2e
test-e2e: ## Run local kind-based end-to-end tests
	bash tests/e2e/test-e2e.sh $(E2E_ARGS)

.PHONY: test-e2e-debug
test-e2e-debug: ## Run e2e tests with Helm debug output
	bash tests/e2e/test-e2e.sh --debug $(E2E_ARGS)

.PHONY: test-e2e-help
test-e2e-help: ## Show e2e runner help and supported environment overrides
	bash tests/e2e/test-e2e.sh --help
