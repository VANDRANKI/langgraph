# Contributing to LangGraph

Thank you for your interest in contributing! This guide covers the conventions
and workflow for working on the LangGraph monorepo.

## Repository Overview

This is a Python monorepo. Each library lives in a subdirectory under `libs/`.
See [DEVELOPMENT.md](DEVELOPMENT.md) for the full library map and dependency
graph.

## Before You Start

1. **Check the dependency map.** Changes to `checkpoint` affect `langgraph`,
   `prebuilt`, `checkpoint-postgres`, and `checkpoint-sqlite`. Understand the
   blast radius before modifying shared libraries.
2. **Work inside the library directory.** All `make` commands must be run from
   within the relevant `libs/<library>` directory.

## Development Workflow

### 1. Install dependencies

```bash
cd libs/<library-name>
make install
```

### 2. Make your changes

### 3. Format and lint

Always run both before committing:

```bash
make format   # Black formatting
make lint     # Ruff + mypy
```

### 4. Run tests

```bash
make test

# Run a specific file
TEST=tests/test_graph.py make test

# Run a specific test with extra options
TEST="tests/test_graph.py::test_compile -v" make test
```

### 5. Open a pull request

Include a clear description of what changed and why.

## Code Style

### Docstring formatting

Use **single backticks** for all inline code references in docstrings and
comments. Do **not** use Sphinx-style double backticks:

```python
# Correct
"""Compiles the graph into a `CompiledStateGraph`."""

# Incorrect — do not use double backticks
"""Compiles the graph into a ``CompiledStateGraph``."""
```

### Type hints

All public functions and methods must have complete type annotations, including
return types.

### Imports

Place all imports at the top of the file (module-level). Avoid inline imports
inside functions or methods. The only acceptable exception is breaking circular
imports where no other option exists.

## Running Tests Across Libraries

If your change touches a library that others depend on, you must verify
downstream tests still pass. For example, changing `checkpoint` requires:

```bash
cd libs/checkpoint && make test
cd libs/checkpoint-postgres && make test
cd libs/checkpoint-sqlite && make test
cd libs/prebuilt && make test
cd libs/langgraph && make test
```

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
feat(langgraph): add interrupt_before parameter to StateGraph
fix(checkpoint): handle None values in checkpoint metadata
docs(sdk-py): add streaming example to README
chore: expand .gitignore for ruff cache
```

## Questions

Open an issue with a clear description of what you are trying to do.
