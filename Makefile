# Makefile for Holo Search SDK

.PHONY: help install install-dev test test-cov lint format clean build publish docs

help:
	@echo "Available commands:"
	@echo "  install      Install the package"
	@echo "  install-dev  Install development dependencies"
	@echo "  test         Run tests"
	@echo "  test-cov     Run tests with coverage"
	@echo "  lint         Run linting"
	@echo "  format       Format code"
	@echo "  clean        Clean build artifacts"
	@echo "  build        Build the package"
	@echo "  publish      Publish to PyPI"
	@echo "  docs         Build documentation"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest tests/

test-cov:
	pytest tests/ --cov=holo_search_sdk --cov-report=html --cov-report=term

lint:
	flake8 holo_search_sdk/ tests/
	mypy holo_search_sdk/
	black --check holo_search_sdk/ tests/
	isort --check-only holo_search_sdk/ tests/

format:
	black holo_search_sdk/ tests/
	isort holo_search_sdk/ tests/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

publish: build
	python -m twine upload dist/*

docs:
	cd docs && make html