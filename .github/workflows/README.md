# GitHub Actions Workflows

This directory contains the CI/CD workflows for the ocode project.

## Workflows

### ci.yml
Main CI workflow that runs on pushes to main/develop and pull requests:
- **Code Quality**: Runs Black, isort, Flake8, mypy, and Bandit across Python 3.8-3.12
- **Tests**: Runs unit and integration tests with coverage reporting
- **Build**: Creates and validates distribution packages

### pre-commit.yml
Runs pre-commit hooks on pull requests and pushes to main.

### test-pr.yml
Quick validation for pull requests with minimal checks.

## Local Development

To run the same checks locally:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run formatting
make format

# Check formatting without changes
make check-format

# Run linting
make lint

# Run security checks
make security

# Run all tests
make test

# Install and run pre-commit hooks
pre-commit install
pre-commit run --all-files
```

## Pre-commit Hooks

The project uses pre-commit to ensure code quality. Hooks include:
- Basic file checks (trailing whitespace, file endings, etc.)
- Black (code formatting)
- isort (import sorting)
- Flake8 (linting)
- mypy (type checking)
- Bandit (security scanning)

Install hooks locally with:
```bash
pre-commit install
```
