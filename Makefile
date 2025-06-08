.PHONY: help install install-dev test lint format type-check clean dev migrate docker-build docker-up

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -e .

install-dev: ## Install development dependencies
	pip install -e ".[dev,test]"

test: ## Run tests
	pytest

test-cov: ## Run tests with coverage
	pytest --cov=src --cov-report=html --cov-report=term

lint: ## Run linting
	ruff check .

lint-fix: ## Run linting with auto-fix
	ruff check --fix .

format: ## Format code
	black .
	isort .

type-check: ## Run type checking
	mypy .

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

dev: ## Start development server
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

migrate: ## Run database migrations
	alembic upgrade head

migrate-auto: ## Create auto-migration
	alembic revision --autogenerate -m "Auto migration"

migrate-create: ## Create empty migration (use MESSAGE=description)
	alembic revision -m "$(MESSAGE)"

docker-build: ## Build Docker image
	docker build -t waitlist-management .

docker-up: ## Start with Docker Compose
	docker-compose up

docker-up-detached: ## Start with Docker Compose in background
	docker-compose up -d

docker-down: ## Stop Docker Compose
	docker-compose down

check: format lint type-check test ## Run all checks (format, lint, type-check, test)

build: clean ## Build package
	python -m build

release: build ## Build and upload to PyPI (requires proper setup)
	python -m twine upload dist/* 