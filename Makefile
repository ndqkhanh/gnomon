.PHONY: help install test lint run tui tui-mock docker-up docker-down docker-logs clean

PY ?= python3
VENV ?= .venv
VENV_BIN := $(VENV)/bin
PIP := $(VENV_BIN)/pip
PYTEST := $(VENV_BIN)/pytest
UVICORN := $(VENV_BIN)/uvicorn
PORT ?= 8011

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

$(VENV):
	$(PY) -m venv $(VENV)
	$(PIP) install -U pip wheel

install: $(VENV) ## Install gnomon + vendored harness_core editable
	$(PIP) install -e ./harness_core
	$(PIP) install -e ../../packages/harness-tui
	$(PIP) install -e '.[dev]'

test: install ## Run unit tests
	$(PYTEST) -q tests

run: install ## Start FastAPI on $(PORT)
	$(UVICORN) gnomon.app:app --reload --port $(PORT)


tui: install ## Open the TUI against the running backend
	$(VENV_BIN)/gnomon --url http://localhost:$(PORT)

tui-mock: install ## Open the TUI with the scripted demo (no backend)
	$(VENV_BIN)/gnomon --mock

docker-up: ## Start container stack
	docker compose up -d --build

docker-down: ## Stop container stack
	docker compose down -v

docker-logs: ## Tail container logs
	docker compose logs -f

clean: ## Remove caches and venv
	rm -rf $(VENV) .pytest_cache .ruff_cache .mypy_cache
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true

.DEFAULT_GOAL := help
