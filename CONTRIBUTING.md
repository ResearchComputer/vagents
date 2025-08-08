# Contributing & Testing

## Setup

- Ensure Python 3.10+ is available.
- Install the project in editable mode with dev extras:

```bash
pip install -e ".[dev]"
```

## Run tests

```bash
pytest -q
```

Coverage reports are written to `htmlcov/`.

## CI/CD

GitHub Actions runs tests on pushes and PRs against `main`. Tagged releases `vX.Y.Z` trigger a publish workflow to PyPI using `PYPI_API_TOKEN` secret.
