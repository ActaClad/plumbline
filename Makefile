# Plumbline dev tasks. `make dev` takes a fresh clone to green tests.
# Targets use a local .venv so they work without an activated environment.

VENV := .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip
BIN  := $(VENV)/bin

.DEFAULT_GOAL := help
.PHONY: help dev test lint fmt fmt-check typecheck check scan build clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

dev: ## Create .venv and install Plumbline with dev + ai extras (one-command setup)
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev,ai]"
	@echo "Done. Run 'make check' to verify, or activate with: source $(VENV)/bin/activate"

test: ## Run the test suite
	$(BIN)/pytest

lint: ## Lint with ruff
	$(BIN)/ruff check .

fmt: ## Auto-format with ruff
	$(BIN)/ruff format .

fmt-check: ## Check formatting without writing
	$(BIN)/ruff format --check .

typecheck: ## Type-check the source with mypy
	$(BIN)/mypy src

check: lint fmt-check typecheck test ## Run everything CI runs (lint, format, types, tests)

scan: ## Dogfood — scan Plumbline's own source
	$(BIN)/plumb scan src --strict-analyzer-errors

build: ## Build sdist + wheel
	$(PY) -m pip install --upgrade build
	$(PY) -m build

clean: ## Remove build/test caches and the venv
	rm -rf $(VENV) dist build *.egg-info .pytest_cache .ruff_cache .mypy_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
