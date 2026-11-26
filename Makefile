# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
.PHONY: help sync lint lint-check mypy test test-integration test-e2e check run build pull clean

SCRIPT ?=
ARGS ?=
IMAGE ?=
PYTHON ?= python3
CONTAINER_RUNTIME ?= docker
NGC_REGISTRY ?= nvcr.io/nvidia
NGC_TAG ?= 1.1.0
RUNNER_IMAGE ?= cdf-workflow-runner
RUNNER_DOCKER_ARGS ?=
NGC_IMAGES ?= \
	cdf-workflow-runner \
	cdf-super-resolution-service \
	cdf-detection-and-tracking-rfdetr-service \
	cdf-detection-and-tracking-sam3-service \
	cdf-referring-expressions-service \
	cdf-captioning-service \
	cdf-grounding-2d-service \
	cdf-grounding-2d-sam3-service \
	cdf-visual-qa-service \
	cdf-reasoning-service \
	cdf-training-export-service \
	cdf-event-and-person-attribute-search-service
GIT ?= git
UV_CACHE_DIR ?= $(CURDIR)/.uv-cache
PYTEST_DISABLE_PLUGIN_AUTOLOAD ?= 1
PY_FILE_DIRS ?= packages services scripts tests
PY_FILES ?= $(shell \
	if command -v $(GIT) >/dev/null 2>&1; then \
		$(GIT) ls-files --cached --others --exclude-standard '*.py'; \
	else \
		find $(PY_FILE_DIRS) -type f -name '*.py'; \
	fi)

export UV_CACHE_DIR
export PYTEST_DISABLE_PLUGIN_AUTOLOAD

# Avoid leaking ambient PYTHONPATH, such as ROS site-packages, into uv commands.
# These paths can break pytest plugin discovery; CI usually has PYTHONPATH unset.
export PYTHONPATH :=

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  sync           Install all workspace packages"
	@echo "  lint           Fix lint issues and format code"
	@echo "  lint-check     Check lint and formatting without changes"
	@echo "  mypy           Run mypy type checks"
	@echo "  test           Run tests with coverage report"
	@echo "  test-integration Run source-mode service tests (optional external endpoints)"
	@echo "  test-e2e       Run real-container workflows (requires GPU, images, checkpoints, endpoints)"
	@echo "  check          Run lint, mypy, and test checks. Make sure this passes before submitting a PR."
	@echo "  run            Run a workflow or service container (no host Python required)"
	@echo "                 ARGS='--cookbook-file path/to/cookbook.yaml' or SCRIPT=<service>:main"
	@echo "  build          Select and build a registered Docker image"
	@echo "  pull           Pull prebuilt stage images from NGC and tag them with local names"
	@echo "                 (optional NGC_IMAGES=\"cdf-captioning-service ...\" NGC_TAG=... CONTAINER_RUNTIME=podman)"
	@echo "  clean          Remove build artifacts and .venv"

sync:
	uv sync --all-packages --all-extras

lint: sync
	uv run ruff format $(PY_FILES)
	uv run ruff check --fix $(PY_FILES)

lint-check: sync
	uv run ruff format --check $(PY_FILES)
	uv run ruff check $(PY_FILES)

mypy: sync
	uv run mypy $(PY_FILES)

test: sync
	uv run pytest -p pytest_cov --cov --cov-report=term --cov-report=xml:coverage_report.xml --junitxml=test_report.xml

# Deterministic source CLI checks; no model endpoints or GPU required.
# Preserve service outputs for local inspection.
test-integration: sync
	uv run pytest -m integration tests/integration/services --basetemp=integration_artifacts --junitxml=integration_report.xml

test-e2e:
	uv run --package workflow-runner python tests/e2e/run_e2e.py $(ARGS)

check: sync lint mypy test

# The host daemon must see the manifest at the same path as the runner container.
run:
	@set -eu; \
	run_image="$(RUNNER_IMAGE)"; \
	socket_mount=--mount=type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock; \
	if [ -n "$(SCRIPT)" ] && [ "$(SCRIPT)" != workflow-runner:main ]; then \
		socket_mount=; \
		run_image=$$(docker run --rm --entrypoint python3 \
			--user "$$(id -u):$$(id -g)" \
			--mount "type=bind,src=$(CURDIR),dst=$(CURDIR),readonly" \
			--workdir "$(CURDIR)" "$(RUNNER_IMAGE)" \
			scripts/run.py --container-image "$(SCRIPT)"); \
	fi; \
	runner_tmp=$$(mktemp -d "$(CURDIR)/.workflow-runner.XXXXXX"); \
	trap 'rmdir "$$runner_tmp"' EXIT; \
	docker run --rm --network host \
		--user "$$(id -u):$$(id -g)" \
		--group-add "$$(stat -c %g /var/run/docker.sock)" \
		$$socket_mount \
		--mount "type=bind,src=$(CURDIR),dst=$(CURDIR)" \
		--workdir "$(CURDIR)" --env "TMPDIR=$$runner_tmp" \
		--env NVIDIA_API_KEY --env GEMINI_API_KEY \
		--env MULTISTORAGECLIENT_CONFIGURATION \
		$(RUNNER_DOCKER_ARGS) "$$run_image" $(if $(strip $(ARGS)),$(ARGS),--help)

build:
	$(PYTHON) scripts/build.py $(IMAGE)

# The workflow runner launches stages by bare image name (e.g. cdf-captioning-service)
# and never pulls, so each pulled image is also tagged with that local name.
pull:
	@for image in $(NGC_IMAGES); do \
		ref="$(NGC_REGISTRY)/$$image:$(NGC_TAG)"; \
		echo "Pulling $$ref"; \
		$(CONTAINER_RUNTIME) pull "$$ref" || exit 1; \
		$(CONTAINER_RUNTIME) tag "$$ref" "$$image" || exit 1; \
	done

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + || true
	rm -rf .venv .uv-cache dist build
