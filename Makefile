.PHONY: help install install-dev test test-unit test-integration coverage lint format type-check clean docs

help:
	@echo "AI Content Generator - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install package and dependencies"
	@echo "  make install-dev      Install package with dev dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make coverage         Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run linting (ruff)"
	@echo "  make format           Format code (black + ruff)"
	@echo "  make type-check       Run type checking (mypy)"
	@echo "  make quality          Run all quality checks"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove build artifacts and cache"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs             Generate documentation"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v -m integration

coverage:
	pytest --cov=ai_content_generator --cov-report=html --cov-report=term

lint:
	ruff check src/ tests/

format:
	black src/ tests/
	ruff check --fix src/ tests/

type-check:
	mypy src/

quality: format lint type-check
	@echo "All quality checks passed!"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docs:
	@echo "Documentation generation not yet implemented"

