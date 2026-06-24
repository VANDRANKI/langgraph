# Contributing to langgraph

A quick reference for contributors. For the full guide see the repo root `CLAUDE.md`.

## Setup

```bash
# Python 3.11+ recommended
cd libs/langgraph

# Install with dev dependencies
pip install -e ".[dev]"

# Or using uv
uv pip install -e ".[dev]"
```

## Development Loop

All commands must be run from **inside the library directory** (`libs/langgraph/`):

```bash
# Format
make format

# Lint (ruff + mypy)
make lint

# Tests
make test

# Run a specific test file
TEST=tests/test_pregel.py make test

# Pass extra pytest flags
TEST="tests/test_pregel.py -x -k test_basic" make test
```

## Library Dependency Map

Understand the impact of your changes:

```
checkpoint
├── checkpoint-postgres
├── checkpoint-sqlite
├── prebuilt
└── langgraph        ← you are here

prebuilt
└── langgraph

sdk-py
├── langgraph
└── cli
```

Changes to `langgraph` may impact `prebuilt`, `sdk-py`, and `cli`.
Run their test suites if your change touches core graph or checkpoint APIs.

## Code Style

- Do NOT use Sphinx double-backtick (` ``code`` `). Use single backticks.
- Type hints required on all public functions.
- Google-style docstrings.

## PR Checklist

- [ ] `make format` applied
- [ ] `make lint` passes
- [ ] `make test` passes in the modified library
- [ ] Tests added for new behavior
- [ ] Downstream libraries tested if checkpoint or graph APIs changed
