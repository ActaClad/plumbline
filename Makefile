# Plumbline dev tasks. `make dev` takes a fresh clone to green tests.
# Targets use a local .venv so they work without an activated environment.
# Cross-platform: works on Linux/macOS and on Windows (GNU make, e.g. via
# Scoop/Chocolatey) — the venv layout and interpreter name differ per OS.

VENV := .venv

# Launch-asset helpers (macOS): what `make demo-report` scans, and where Chrome
# lives. For the canonical marketing image use simonw/llm @ 0d593ea (see
# docs/examples/README.md); override REPO to point elsewhere, or CHROME if it's
# installed at a non-default path.
REPO   ?= ./llm
CHROME ?= /Applications/Google Chrome.app/Contents/MacOS/Google Chrome

ifeq ($(OS),Windows_NT)
	BIN    := $(VENV)/Scripts
	PY     := $(BIN)/python.exe
	PIP    := $(BIN)/pip.exe
	PYTHON := python
else
	BIN    := $(VENV)/bin
	PY     := $(BIN)/python
	PIP    := $(BIN)/pip
	PYTHON := python3
endif

.DEFAULT_GOAL := help
.PHONY: help dev test lint fmt fmt-check typecheck check scan build clean demo-report

help: ## Show this help
	@$(PYTHON) -c "import re,sys; \
[print('  \033[36m%-12s\033[0m %s' % (m.group(1), m.group(2))) \
for line in open('Makefile', encoding='utf-8') \
for m in [re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)] if m]"

dev: ## Create .venv and install Plumbline with dev + ai extras (one-command setup)
	$(PYTHON) -m venv $(VENV)
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

demo-report: ## Regenerate docs/launch/report.png (writes report HTML; screenshots via Chrome if it cooperates)
	-$(BIN)/plumb scan $(REPO) --html $(VENV)/demo-report.html
	@rm -f "$(VENV)/report-shot.png"; \
	"$(CHROME)" --headless=new --hide-scrollbars --disable-gpu --force-device-scale-factor=2 \
	  --screenshot="$(CURDIR)/$(VENV)/report-shot.png" --window-size=1200,900 \
	  "file://$(CURDIR)/$(VENV)/demo-report.html" >/dev/null 2>&1 || true; \
	if [ -f "$(VENV)/report-shot.png" ]; then \
	  mv "$(VENV)/report-shot.png" docs/launch/report.png; \
	  echo "Wrote docs/launch/report.png (scanned: $(REPO))"; \
	else \
	  echo "Report HTML is at $(VENV)/demo-report.html. Headless Chrome didn't produce a PNG in this shell"; \
	  echo "(a known macOS quirk) — capture it directly:"; \
	  echo "  '$(CHROME)' --headless=new --hide-scrollbars \\"; \
	  echo "    --screenshot=\"$(CURDIR)/docs/launch/report.png\" --window-size=1200,900 \\"; \
	  echo "    \"file://$(CURDIR)/$(VENV)/demo-report.html\""; \
	fi

build: ## Build sdist + wheel
	$(PY) -m pip install --upgrade build
	$(PY) -m build

clean: ## Remove build/test caches and the venv
	@$(PYTHON) -c "import shutil,os; \
[shutil.rmtree(p, ignore_errors=True) for p in \
['$(VENV)','dist','build','.pytest_cache','.ruff_cache','.mypy_cache']]; \
[shutil.rmtree(os.path.join(r,d), ignore_errors=True) \
for r,ds,fs in os.walk('.') for d in ds if d in ('__pycache__',) or d.endswith('.egg-info')]"
