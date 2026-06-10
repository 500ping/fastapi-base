COMPOSE := docker compose -f docker-compose.local.yml
APP := src:app
SRC := src tests

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---- Setup ----------------------------------------------------------------
.PHONY: install
install: ## Sync dependencies (incl. dev) into the uv environment
	uv sync

.PHONY: hooks
hooks: ## Install pre-commit git hooks
	uv run pre-commit install

# ---- Run ------------------------------------------------------------------
.PHONY: run
run: ## Run the app with autoreload (http://127.0.0.1:8000)
	uv run uvicorn $(APP) --reload

# ---- Quality --------------------------------------------------------------
.PHONY: lint
lint: ## Lint with ruff
	uvx ruff check $(SRC)

.PHONY: format
format: ## Format with ruff (and apply lint autofixes)
	uvx ruff format $(SRC)
	uvx ruff check --fix $(SRC)

.PHONY: check
check: ## Run all pre-commit hooks on all files
	uv run pre-commit run --all-files

# ---- Tests ----------------------------------------------------------------
.PHONY: test
test: ## Run the test suite (requires Docker for testcontainers)
	uv run pytest

.PHONY: test-v
test-v: ## Run the test suite verbosely
	uv run pytest -v

.PHONY: coverage
coverage: ## Run tests with a coverage report (terminal)
	uv run pytest --cov

.PHONY: coverage-html
coverage-html: ## Run tests and write an HTML coverage report to htmlcov/
	uv run pytest --cov --cov-report=html
	@echo "Open htmlcov/index.html"

# ---- Compose stack --------------------------------------------------------
.PHONY: up
up: ## Start the local compose stack
	$(COMPOSE) up -d

.PHONY: down
down: ## Stop the local compose stack
	$(COMPOSE) down

.PHONY: reset
reset: ## Recreate the local stack (drops data volumes)
	$(COMPOSE) down -v
	$(COMPOSE) up -d

.PHONY: logs
logs: ## Tail the compose stack logs
	$(COMPOSE) logs -f

# ---- Migrations -----------------------------------------------------------
.PHONY: migrate
migrate: ## Apply all migrations (alembic upgrade head)
	uv run alembic upgrade head

.PHONY: migration
migration: ## Autogenerate a migration: make migration m="message"
	uv run alembic revision --autogenerate -m "$(m)"

.PHONY: downgrade
downgrade: ## Roll back the last migration
	uv run alembic downgrade -1

# ---- Housekeeping ---------------------------------------------------------
.PHONY: clean
clean: ## Remove caches and build artifacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache
