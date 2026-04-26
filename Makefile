# colourmapper - Makefile
.DEFAULT_GOAL := help
SHELL := /bin/bash

# Colors
CYAN  := \033[36m
RESET := \033[0m

# Python
PYTHON   := python3
VENV     := .venv
PIP      := $(VENV)/bin/pip
PYTEST   := $(VENV)/bin/pytest
RUFF     := $(VENV)/bin/ruff
MYPY     := $(VENV)/bin/mypy --explicit-package-bases
AUTOPEP8 := $(VENV)/bin/autopep8 --recursive --in-place --aggressive --max-line-length 119
ISORT    := $(VENV)/bin/isort

.PHONY: help
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2}'

.PHONY: check-venv
check-venv: venv ## Verify the virtual environment is activated
	@if [ -z "$${VIRTUAL_ENV:-}" ]; then \
	  printf "\033[31mERROR:\033[0m virtual env not active.\n"; \
	  printf "Activate it first:\n\n"; \
	  printf "  \033[32msource $(VENV)/bin/activate\033[0m\n\n"; \
	  printf "Then re-run make.\n"; \
	  exit 1; \
	fi
	@echo "  venv active: $${VIRTUAL_ENV}"

.PHONY: venv
venv: ## Create Python virtual environment (if absent)
	@if [ ! -d "$(VENV)" ]; then \
	  echo "  creating venv in $(VENV)..."; \
	  $(PYTHON) -m venv $(VENV); \
	  $(VENV)/bin/pip install --upgrade pip; \
	  echo "  venv created - activate with: source $(VENV)/bin/activate"; \
	else \
	  echo "  venv already exists in $(VENV)"; \
	fi

.PHONY: install
install: check-venv ## Install dependencies (venv must be active)
	$(PIP) install -r requirements.txt -r requirements-dev.txt

.PHONY: format
format: check-venv ## Format Python code (autopep8 + isort)
	$(AUTOPEP8) src/ tests/
	$(ISORT) src/ tests/

.PHONY: lint
lint: check-venv ## Lint Python code (ruff + mypy)
	$(RUFF) check src/ tests/
	$(MYPY) src/

.PHONY: typecheck
typecheck: check-venv ## Run mypy type checks
	$(MYPY) src/

.PHONY: test
test: check-venv ## Run Python tests with coverage
	$(PYTEST) tests/ -v --tb=short --cov=src --cov-report=term-missing

.PHONY: clean
clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache  -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist         -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name build        -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf coverage/ .coverage htmlcov/ 2>/dev/null || true

.PHONY: ci
ci: lint test ## Run lint + test (for CI pipelines)
	@echo "CI passed"

# GitHub
.PHONY: github-check
github-check: ## Test GitHub SSH connectivity
	ssh -T git@github.com || true

# Examples
CM                  := src/colourmapper/cm.py
MAPPING_FILE_CREATE := src/colourmapper/mapping_file_create.py

.PHONY: examples
examples: ## Run usage examples (colour lookup + mapping file preview)
	@echo "  example: cm 'burnt orange'"
	$(PYTHON) $(CM) 'burnt orange' | jq '.'
	@echo ""
	@echo "  example: mapping-file-create --print | jq '.map | to_entries | .[0:5]'"
	$(PYTHON) $(MAPPING_FILE_CREATE) --print | jq '.map | to_entries | .[0:5]'

.PHONY: aliases
aliases: ## Print shell alias commands for cm and mapping-file-create
	@REPOROOT=$$(git rev-parse --show-toplevel) && \
	case "$$SHELL" in \
	  */zsh)  RC="~/.zshrc" ;; \
	  */bash) RC="~/.bashrc" ;; \
	  */fish) RC="~/.config/fish/config.fish" ;; \
	  *)       RC="~/.profile" ;; \
	esac && \
	printf "\nAdd the following aliases to your shell RC file ($$RC):\n\n"; \
	printf "  alias cm='$$REPOROOT/$(CM)'\n"; \
	printf "  alias mapping-file-create='$$REPOROOT/$(MAPPING_FILE_CREATE)'\n"; \
	printf "\nOr append them automatically:\n\n"; \
	printf "  echo \"alias cm='$$REPOROOT/$(CM)'\" >> $$RC\n"; \
	printf "  echo \"alias mapping-file-create='$$REPOROOT/$(MAPPING_FILE_CREATE)'\" >> $$RC\n\n"

