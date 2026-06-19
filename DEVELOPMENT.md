# Development Guide

This document covers day-to-day development workflows for the LangGraph monorepo.

## Repository Structure

Each library lives in a subdirectory under `libs/`:

| Library | Description |
|---------|-------------|
| `libs/langgraph/` | Core framework for building stateful, multi-actor agents |
| `libs/checkpoint/` | Base interfaces for LangGraph checkpointers |
| `libs/checkpoint-postgres/` | Postgres implementation of the checkpoint saver |
| `libs/checkpoint-sqlite/` | SQLite implementation of the checkpoint saver |
| `libs/prebuilt/` | High-level APIs for creating and running agents and tools |
| `libs/sdk-py/` | Python SDK for the LangGraph Server API |
| `libs/sdk-js/` | JS/TS SDK for interacting with the LangGraph REST API |
| `libs/cli/` | Official command-line interface for LangGraph |

## Library Dependency Map

Before modifying a library, understand which downstream libraries it affects:

```
checkpoint
├── checkpoint-postgres
├── checkpoint-sqlite
├── prebuilt
└── langgraph

prebuilt
└── langgraph

sdk-py
├── langgraph
└── cli

sdk-js (standalone)
```

When you change `checkpoint`, you must also verify that `checkpoint-postgres`,
`checkpoint-sqlite`, `prebuilt`, and `langgraph` still pass their tests.

## Setting Up

Each library manages its own dependencies. Navigate to the library you want to
work on and install dependencies:

```bash
cd libs/langgraph
make install
```

Or use `uv` directly:

```bash
cd libs/langgraph
uv sync
```

## Running Tests

All test commands are run from within the relevant library directory.

### Run the full test suite for a library

```bash
cd libs/langgraph
make test
```

### Run a specific test file

```bash
cd libs/langgraph
TEST=tests/test_graph.py make test
```

### Pass additional pytest options

```bash
cd libs/langgraph
TEST="tests/test_graph.py -k test_compile -v" make test
```

### Run pytest directly

```bash
cd libs/langgraph
uv run pytest tests/test_graph.py -v
```

## Code Formatting and Linting

Always run these before opening a pull request:

```bash
cd libs/<library-name>
make format   # Apply Black code formatting
make lint     # Run Ruff linter and mypy type checker
```

To run specific linters:

```bash
make lint-ruff    # Ruff linting only
make lint-mypy    # mypy type checking only
```

## Docstring Style Convention

Use **single backticks** for inline code references in docstrings and comments:

```python
# Correct
"""Compiles the graph into a `CompiledGraph` object."""

# Incorrect — do not use Sphinx-style double backticks
"""Compiles the graph into a ``CompiledGraph`` object."""
```

## Pull Requests

1. Make changes in the relevant `libs/<library>` directory.
2. Run `make format` and `make lint` in that directory.
3. Run `make test` and verify tests pass.
4. If your change affects a library that others depend on (see dependency map above),
   run tests in those downstream libraries too.
5. Open a PR with a clear description of what changed and why.
