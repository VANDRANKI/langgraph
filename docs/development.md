# LangGraph Development Guide

This guide covers setting up a local development environment and contributing to the LangGraph monorepo.

## Repository Structure

The monorepo contains several independent Python and JavaScript libraries under `libs/`:

| Library | Description |
|---------|-------------|
| `checkpoint` | Base interfaces for checkpointers |
| `checkpoint-postgres` | PostgreSQL checkpoint saver |
| `checkpoint-sqlite` | SQLite checkpoint saver |
| `langgraph` | Core stateful agent framework |
| `prebuilt` | High-level agent APIs |
| `cli` | LangGraph CLI |
| `sdk-py` | Python SDK for LangGraph Server |
| `sdk-js` | JavaScript/TypeScript SDK |

## Setting Up

```bash
# From any library directory
cd libs/langgraph

# Format code
make format

# Lint
make lint

# Run tests
make test

# Run a specific test file
TEST=tests/test_graph.py make test
```

## Dependency Graph

Be aware of downstream impact when modifying a library:

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
```

## Adding New Features

1. Choose the appropriate library (most graph changes belong in `libs/langgraph`)
2. Add tests in `tests/` within that library directory
3. Run `make format && make lint && make test` before opening a PR
4. Update documentation in `docs/` for user-facing changes

## Code Style

- Use single backticks for inline code in docstrings (`` `code` ``), not double backticks
- All public functions must have type hints and docstrings
- Follow the existing patterns in each library for error handling and logging

## Checkpointer Development

When implementing a new checkpointer:
1. Inherit from `BaseCheckpointSaver` in `libs/checkpoint`
2. Implement `get`, `put`, `list`, and async variants
3. Add integration tests that verify round-trip checkpoint fidelity
4. Ensure thread-safety for concurrent graph executions
