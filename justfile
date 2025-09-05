# justfile for GigaChat development commands

# Load environment variables from .env
set dotenv-load

# Default recipe to display help
default:
    @just --list

# Install dependencies
setup:
    python -m pip install --upgrade pip
    pip install -r requirements/dev.txt
    pre-commit install

# Run development server
dev:
    uvicorn app.main:app --reload

# Run all tests
test:
    pytest --cov=app --cov-report=term-missing

# Run specific test file
test-file file:
    pytest {{file}} -v

# Run linting
lint:
    ruff check .
    black . --check
    mypy app tests

# Format code
format:
    black .
    ruff check . --fix

# Run security checks
security:
    bandit -r app
    safety check

# Start development services with Docker
services:
    docker-compose up -d redis minio

# Stop development services
services-stop:
    docker-compose down

# Build Docker image
build:
    docker build -t gigachat:local .

# Clean Python cache files
clean:
    find . -type d -name "__pycache__" -exec rm -r {} +
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    find . -type f -name "*.pyd" -delete
    find . -type f -name ".coverage" -delete
    find . -type d -name "*.egg-info" -exec rm -r {} +
    find . -type d -name "*.egg" -exec rm -r {} +
    find . -type d -name ".pytest_cache" -exec rm -r {} +
    find . -type d -name ".mypy_cache" -exec rm -r {} +
    find . -type d -name ".ruff_cache" -exec rm -r {} +
    find . -type d -name "htmlcov" -exec rm -r {} +

# Run database migrations
db-migrate:
    alembic upgrade head

# Create new database migration
db-revision message:
    alembic revision --autogenerate -m "{{message}}"

# Build documentation
docs-build:
    mkdocs build

# Serve documentation locally
docs-serve:
    mkdocs serve

# Create a new release
release version:
    #!/bin/bash
    set -e
    # Update version in pyproject.toml
    sed -i "s/version = .*/version = \"{{version}}\"/" pyproject.toml
    # Create git tag
    git tag -a v{{version}} -m "Release v{{version}}"
    git push origin v{{version}}

# Export requirements
requirements-export:
    pip-compile pyproject.toml -o requirements/base.txt
    pip-compile pyproject.toml --extra dev -o requirements/dev.txt
    pip-compile pyproject.toml --extra prod -o requirements/prod.txt
    pip-compile pyproject.toml --extra test -o requirements/test.txt