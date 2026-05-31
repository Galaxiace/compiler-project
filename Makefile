# MiniCompiler Makefile (Sprint 8)
# Build, test, and install the compiler

.PHONY: all build install clean distclean test test-all coverage help

# Variables
PYTHON = python3
PIP = pip3
PROJECT = mycc
VENV = .venv

# Default target
all: build

# Build the project
build:
	$(PYTHON) setup.py build

# Install the compiler
install: build
	$(PYTHON) setup.py install --user

# Create virtual environment and install
venv:
	$(PYTHON) -m venv $(VENV)
	. $(VENV)/bin/activate && $(PIP) install -e .

# Install in development mode
install-dev:
	$(PIP) install -e .

# Run tests
test:
	pytest tests/ -v

# Run all tests
test-all:
	pytest tests/ -v
	python tests/test_runner.py -v
	bash tests/codegen/run_tests.sh

# Generate test coverage
coverage:
	pytest --cov=. --cov-report=html tests/
	@echo "Coverage report generated in htmlcov/index.html"

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Deep clean
distclean: clean
	rm -rf $(VENV)

# Build package for distribution
dist:
	$(PYTHON) setup.py sdist bdist_wheel

# Install development dependencies
dev-install:
	$(PIP) install -e ".[dev]"

# Show help
help:
	@echo "MiniCompiler Build System"
	@echo "========================="
	@echo "make build        - Build the compiler"
	@echo "make install      - Install the compiler"
	@echo "make install-dev  - Install in development mode"
	@echo "make venv         - Create virtual environment"
	@echo "make test         - Run pytest tests"
	@echo "make test-all     - Run all tests"
	@echo "make coverage     - Generate test coverage report"
	@echo "make clean        - Clean build artifacts"
	@echo "make distclean    - Deep clean (including venv)"
	@echo "make dist         - Create distribution package"
	@echo "make dev-install  - Install with development dependencies"
	@echo "make help         - Show this help"