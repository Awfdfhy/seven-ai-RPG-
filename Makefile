.PHONY: help test lint type coverage clean install pre-commit qa-fast qa-full

help:
	@echo "Seven RPG — QA Automation"
	@echo ""
	@echo "  make test          Run unit tests"
	@echo "  make lint          Run ruff linter"
	@echo "  make type          Run mypy type checks"
	@echo "  make coverage      Run tests with HTML coverage report"
	@echo "  make qa-fast       Fast QA (skip slow/integration)"
	@echo "  make qa-full       Full QA suite with coverage"
	@echo "  make clean         Remove cache/coverage artifacts"
	@echo "  make install       Install dev dependencies"
	@echo "  make pre-commit    Install pre-commit hooks"

test:
	python run_qa.py --unit --no-cov

lint:
	ruff check src/ tests/

type:
	mypy src/ --ignore-missing-imports

coverage:
	python -m pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

qa-fast:
	python run_qa.py --fast

qa-full:
	python run_qa.py

clean:
	rm -rf .pytest_cache htmlcov .coverage .mypy_cache .ruff_cache

install:
	pip install -e ".[dev]"
	pip install ruff mypy

pre-commit:
	pip install pre-commit
	pre-commit install
