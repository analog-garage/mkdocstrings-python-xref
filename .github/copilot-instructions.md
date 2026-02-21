# Copilot Instructions

## Project Overview

mkdocstrings-python-xref is an mkdocstrings handler that extends the standard
`mkdocstrings-python` handler to support relative cross-reference syntax in Python
docstrings. It also reports source locations for bad references.

## Build, Test, and Lint

All tasks use [pixi](https://pixi.sh/). Run `pixi task list` to see all available tasks.

```bash
# Run tests with verbose output
pixi run pytest

# Run a single test file
pixi run pytest -sv -ra tests/test_crossref.py

# Run a single test by name
pixi run pytest -sv -ra tests/test_crossref.py -k "test_name"

# Lint (ruff + mypy)
pixi run lint

# Type checking only
pixi run mypy

# Ruff linting only
pixi run ruff

# Build docs
pixi run doc

# Serve docs locally
pixi run show-doc
```

## Architecture

- **Namespace package**: `src/mkdocstrings_handlers/` is an implicit namespace package
  (no `__init__.py`). The handler lives under `python_xref/`.
- **Handler registration**: `get_handler()` factory in `__init__.py` returns a
  `PythonRelXRefHandler` instance. mkdocstrings discovers it via the `python_xref`
  handler name.
- **Core classes**:
  - `PythonRelXRefHandler` (handler.py) — extends `PythonHandler`, overrides `render()`
    to process relative cross-references before rendering.
  - `_RelativeCrossrefProcessor` (crossref.py) — visitor-style processor that walks
    Griffe docstring objects and substitutes relative refs using compiled regex patterns.
- **Version**: stored as plain text in `src/mkdocstrings_handlers/python_xref/VERSION`.
  Hatchling reads it at build time. Versioning tracks the upstream mkdocstrings-python
  version.

## Conventions

- **Build system**: Hatchling. The wheel includes `src/mkdocstrings_handlers`.
- **Docstring style**: Google style (enforced by ruff `D` rules and mypy).
- **Formatting**: Use `black` for code formatting.
- **Type annotations**: Required on all function definitions (`disallow_untyped_defs`
  and `disallow_incomplete_defs` in mypy config).
- **Test organization**: Tests are in `tests/`. `tests/project/` contains a sample
  Python package used by integration tests. There is no `conftest.py`; fixtures come
  from pytest builtins.
