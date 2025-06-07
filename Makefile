# Project Configuration
PACKAGE_NAME := v-agents
PYTHON := python3
PIP := pip3

# Colors for output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# Default target
.PHONY: help
help:
	@echo "$(CYAN)Available targets:$(RESET)"
	@echo "  $(GREEN)install$(RESET)          - Install the package in development mode"
	@echo "  $(GREEN)install-dev$(RESET)      - Install development dependencies"
	@echo "  $(GREEN)clean$(RESET)            - Clean build artifacts"
	@echo "  $(GREEN)build$(RESET)            - Build the package"
	@echo "  $(GREEN)test$(RESET)             - Run tests"
	@echo "  $(GREEN)lint$(RESET)             - Run linting checks"
	@echo "  $(GREEN)format$(RESET)           - Format code"
	@echo "  $(GREEN)check$(RESET)            - Run all quality checks"
	@echo "  $(GREEN)version$(RESET)          - Show current version"
	@echo "  $(GREEN)bump-patch$(RESET)       - Bump patch version"
	@echo "  $(GREEN)bump-minor$(RESET)       - Bump minor version"
	@echo "  $(GREEN)bump-major$(RESET)       - Bump major version"
	@echo "  $(GREEN)build-upload$(RESET)     - Build and upload to PyPI"
	@echo "  $(GREEN)upload-test$(RESET)      - Upload to TestPyPI"
	@echo "  $(GREEN)upload$(RESET)           - Upload to PyPI"
	@echo "  $(GREEN)release$(RESET)          - Full release process (test, build, upload)"

# Installation targets
.PHONY: install
install:
	@echo "$(CYAN)Installing package in development mode...$(RESET)"
	$(PIP) install -e .

.PHONY: install-dev
install-dev:
	@echo "$(CYAN)Installing development dependencies...$(RESET)"
	$(PIP) install -e ".[dev]"
	$(PIP) install build twine

# Clean targets
.PHONY: clean
clean:
	@echo "$(CYAN)Cleaning build artifacts...$(RESET)"
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Build targets
.PHONY: build
build: clean
	@echo "$(CYAN)Building package...$(RESET)"
	$(PYTHON) -m build

# Test targets
.PHONY: test
test:
	@echo "$(CYAN)Running tests...$(RESET)"
	$(PYTHON) -m pytest

# Quality checks
.PHONY: lint
lint:
	@echo "$(CYAN)Running linting checks...$(RESET)"
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 vagents/; \
	else \
		echo "$(YELLOW)flake8 not installed, skipping...$(RESET)"; \
	fi
	@if command -v pylint >/dev/null 2>&1; then \
		pylint vagents/; \
	else \
		echo "$(YELLOW)pylint not installed, skipping...$(RESET)"; \
	fi

.PHONY: format
format:
	@echo "$(CYAN)Formatting code...$(RESET)"
	@if command -v black >/dev/null 2>&1; then \
		black vagents/; \
	else \
		echo "$(YELLOW)black not installed, skipping...$(RESET)"; \
	fi
	@if command -v isort >/dev/null 2>&1; then \
		isort vagents/; \
	else \
		echo "$(YELLOW)isort not installed, skipping...$(RESET)"; \
	fi

.PHONY: check
check: lint test
	@echo "$(GREEN)All quality checks passed!$(RESET)"

# Version management
.PHONY: version
version:
	@$(PYTHON) -c "import vagents; print(f'Current version: {vagents.__version__}')"

.PHONY: bump-patch
bump-patch:
	@echo "$(CYAN)Bumping patch version...$(RESET)"
	@$(PYTHON) -c "import vagents; parts = vagents.__version__.split('.'); parts[2] = str(int(parts[2]) + 1); new_version = '.'.join(parts); open('vagents/__init__.py', 'w').write(f'__version__ = \"{new_version}\"\n'); print(f'Version bumped to {new_version}')"

.PHONY: bump-minor
bump-minor:
	@echo "$(CYAN)Bumping minor version...$(RESET)"
	@$(PYTHON) -c "import vagents; parts = vagents.__version__.split('.'); parts[1] = str(int(parts[1]) + 1); parts[2] = '0'; new_version = '.'.join(parts); open('vagents/__init__.py', 'w').write(f'__version__ = \"{new_version}\"\n'); print(f'Version bumped to {new_version}')"

.PHONY: bump-major
bump-major:
	@echo "$(CYAN)Bumping major version...$(RESET)"
	@$(PYTHON) -c "import vagents; parts = vagents.__version__.split('.'); parts[0] = str(int(parts[0]) + 1); parts[1] = '0'; parts[2] = '0'; new_version = '.'.join(parts); open('vagents/__init__.py', 'w').write(f'__version__ = \"{new_version}\"\n'); print(f'Version bumped to {new_version}')"

# PyPI upload targets
.PHONY: upload-test
upload-test: build
	@echo "$(CYAN)Uploading to TestPyPI...$(RESET)"
	@if [ ! -f ~/.pypirc ]; then \
		echo "$(RED)Error: ~/.pypirc not found. Please configure your PyPI credentials.$(RESET)"; \
		echo "$(YELLOW)You can create it with:$(RESET)"; \
		echo "  twine configure"; \
		exit 1; \
	fi
	twine upload --repository testpypi dist/*
	@echo "$(GREEN)Package uploaded to TestPyPI!$(RESET)"
	@echo "$(YELLOW)Test installation with:$(RESET)"
	@echo "  pip install --index-url https://test.pypi.org/simple/ $(PACKAGE_NAME)"

.PHONY: upload
upload: build
	@echo "$(CYAN)Uploading to PyPI...$(RESET)"
	@if [ ! -f ~/.pypirc ]; then \
		echo "$(RED)Error: ~/.pypirc not found. Please configure your PyPI credentials.$(RESET)"; \
		echo "$(YELLOW)You can create it with:$(RESET)"; \
		echo "  twine configure"; \
		exit 1; \
	fi
	@echo "$(YELLOW)WARNING: This will upload to the official PyPI!$(RESET)"
	@echo "$(YELLOW)Make sure you have tested on TestPyPI first.$(RESET)"
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]
	twine upload dist/*
	@echo "$(GREEN)Package uploaded to PyPI!$(RESET)"
	@echo "$(YELLOW)Install with:$(RESET)"
	@echo "  pip install $(PACKAGE_NAME)"

.PHONY: build-upload
build-upload: build upload

# Full release process
.PHONY: release
release: check build upload-test
	@echo "$(GREEN)Release process completed!$(RESET)"
	@echo "$(YELLOW)To complete the release:$(RESET)"
	@echo "  1. Test the package from TestPyPI"
	@echo "  2. If everything works, run 'make upload' to publish to PyPI"
	@echo "  3. Create a git tag: git tag v$$($(PYTHON) -c 'import vagents; print(vagents.__version__)')"
	@echo "  4. Push the tag: git push origin v$$($(PYTHON) -c 'import vagents; print(vagents.__version__)')"

# Check PyPI credentials
.PHONY: check-credentials
check-credentials:
	@echo "$(CYAN)Checking PyPI credentials...$(RESET)"
	@if [ ! -f ~/.pypirc ]; then \
		echo "$(RED)Error: ~/.pypirc not found.$(RESET)"; \
		echo "$(YELLOW)To configure your credentials, run:$(RESET)"; \
		echo "  twine configure"; \
		echo ""; \
		echo "$(YELLOW)Or create ~/.pypirc manually with:$(RESET)"; \
		echo "[distutils]"; \
		echo "index-servers = pypi testpypi"; \
		echo ""; \
		echo "[pypi]"; \
		echo "username = __token__"; \
		echo "password = <your-pypi-token>"; \
		echo ""; \
		echo "[testpypi]"; \
		echo "repository = https://test.pypi.org/legacy/"; \
		echo "username = __token__"; \
		echo "password = <your-testpypi-token>"; \
		exit 1; \
	else \
		echo "$(GREEN)PyPI credentials found!$(RESET)"; \
	fi