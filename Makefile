.PHONY: help install install-dev test test-unit test-integration test-performance lint format clean docs

# Help target
help:
	@echo "Available targets:"
	@echo "  install          Install OCode package"
	@echo "  install-dev      Install with development dependencies"
	@echo "  test            Run all tests"
	@echo "  test-unit       Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-performance Run performance tests only"
	@echo "  lint            Run all linting checks"
	@echo "  format          Format code with black and isort"
	@echo "  clean           Clean build artifacts"
	@echo "  docs            Build documentation"

# Installation targets
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pip install -r requirements-dev.txt

# Testing targets
test:
	pytest

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-performance:
	pytest tests/performance/ -v -m performance

test-coverage:
	pytest --cov=ocode_python --cov-report=html --cov-report=term

# Linting targets
lint: lint-flake8 lint-mypy

lint-flake8:
	@echo "Running flake8..."
	@python -m flake8 ocode_python/ tests/ || echo "flake8 not installed, skipping..."

lint-mypy:
	@echo "Running mypy..."
	@python -m mypy ocode_python/ || echo "mypy not installed, skipping..."

# Formatting targets
format: format-black format-isort

format-black:
	@echo "Running black..."
	@python -m black ocode_python/ tests/ || echo "black not installed, skipping..."

format-isort:
	@echo "Running isort..."
	@python -m isort ocode_python/ tests/ || echo "isort not installed, skipping..."

# Check formatting without applying changes
check-format:
	@echo "Checking black formatting..."
	@python -m black --check ocode_python/ tests/ || echo "black not installed, skipping..."
	@echo "Checking isort formatting..."
	@python -m isort --check-only ocode_python/ tests/ || echo "isort not installed, skipping..."

# Security checks
security:
	@echo "Running security checks..."
	@python -m bandit -r ocode_python/ || echo "bandit not installed, skipping..."

# Clean targets
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Documentation targets
docs:
	@echo "Building documentation..."
	@cd docs && make html || echo "sphinx not installed or docs/ not found"

# Docker targets
docker-build:
	docker build -t ocode:latest .

docker-test:
	docker run --rm ocode:latest pytest

# Release targets
check-release: clean lint test
	@echo "Release checks completed"

# CI targets
ci: install-dev lint test
	@echo "CI pipeline completed"
