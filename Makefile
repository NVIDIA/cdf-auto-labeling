# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
.PHONY: help sync lint lint-check mypy test test-e2e check run build pull clean

SCRIPT ?=
ARGS ?=
IMAGE ?=
PYTHON ?= python3
CONTAINER_RUNTIME ?= docker
NGC_REGISTRY ?= nvcr.io/nvidia
NGC_TAG ?= 1.1.0
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
	@echo "  test-e2e       Run end-to-end service tests (needs GPU runner + external model endpoints)"
	@echo "  check          Run lint, mypy, and test checks. Make sure this passes before submitting a PR."
	@echo "  run            Select and run a workspace script (optional ARGS=... for script argv)"
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

# End-to-end tests run each service through its real CLI entrypoint. Tests self-skip
# when their prerequisites (external model endpoints, ffmpeg) are unavailable.
# --basetemp writes each test's scene outputs to e2e_artifacts/ so they can be
# inspected locally and uploaded as browsable CI artifacts.
test-e2e: sync
	uv run pytest -m e2e tests/e2e --basetemp=e2e_artifacts --junitxml=e2e_report.xml

check: sync lint mypy test

run: sync
	uv run --group dev python scripts/run.py $(SCRIPT) -- $(ARGS)

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
