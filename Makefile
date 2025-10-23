.PHONY: help install dev test clean run docker-up docker-down migrate

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	uv sync

dev: ## Install development dependencies
	uv sync --extra dev
	pre-commit install
	@echo "✅ Development environment ready!"
	@echo "✅ Pre-commit hooks installed!"

test: ## Run tests
	pytest

test-cov: ## Run tests with coverage
	pytest --cov=app --cov-report=html --cov-report=term

lint: ## Run linting
	ruff check app/
	mypy app/

format: ## Format code
	ruff format app/

pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

pre-commit-update: ## Update pre-commit hooks to latest versions
	pre-commit autoupdate

clean: ## Clean up build artifacts and cache
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf htmlcov/

docker-up: ## Start Docker services (PostgreSQL + Redis)
	docker-compose up -d
	@echo "✅ Services started!"
	@echo "PostgreSQL: localhost:5432"
	@echo "Redis: localhost:6379"

docker-down: ## Stop Docker services
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f

run: ## Run FastAPI development server
	python -m app.main

run-prod: ## Run FastAPI production server
	uvicorn app.main:app --host 0.0.0.0 --port 8000

migrate-init: ## Initialize Alembic migrations
	alembic init migrations

migrate-create: ## Create a new migration
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

migrate-up: ## Run migrations
	alembic upgrade head

migrate-down: ## Rollback last migration
	alembic downgrade -1

db-reset: ## Reset database (WARNING: destroys all data)
	docker-compose down -v
	docker-compose up -d postgres
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 5
	alembic upgrade head
	@echo "✅ Database reset complete!"

check: ## Run all checks (lint + test)
	make lint
	make test

setup: ## Complete setup (install + docker + migrate)
	make dev
	make docker-up
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo "✅ Setup complete! Run 'make run' to start the server."
