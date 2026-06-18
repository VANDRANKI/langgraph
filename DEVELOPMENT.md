# LangGraph Development Guide

This document supplements `CLAUDE.md` with step-by-step instructions
for common contributor workflows.

## Repository Layout

```
libs/
  checkpoint/           # Base checkpointer interface
  checkpoint-postgres/  # PostgreSQL checkpointer
  checkpoint-sqlite/    # SQLite checkpointer
  cli/                  # LangGraph CLI
  langgraph/            # Core framework
  prebuilt/             # High-level agent APIs
  sdk-py/               # Python SDK for LangGraph Server
  sdk-js/               # JS/TS SDK
```

## Setup

```bash
# From the root of any library, e.g. libs/langgraph
cd libs/langgraph
pip install -e ".[dev]"
```

Or use the root-level convenience targets:

```bash
make -C libs/langgraph install
```

## Running Tests

Always `cd` into the specific library before running tests:

```bash
cd libs/langgraph
make test                    # full suite
TEST=tests/test_graph.py make test   # single file
```

The `TEST` variable is forwarded directly to pytest, so standard
options work:

```bash
TEST="tests/test_graph.py -k test_cycles -v" make test
```

## Linting & Formatting

```bash
make format   # ruff format + isort
make lint     # ruff check + mypy
```

Both must pass before opening a PR.

## Dependency Map

If you change `checkpoint`, tests in these libraries may break too:

- `checkpoint-postgres`
- `checkpoint-sqlite`
- `prebuilt`
- `langgraph`

If you change `prebuilt`, also check:

- `langgraph`

Always run the downstream test suites when touching shared code.

## Docstrings

Use single-backtick inline code (`` `symbol` ``), not Sphinx-style
double backticks (```` ``symbol`` ````). This applies everywhere:
docstrings, comments, and markdown files.

## Commit Messages

Follow Conventional Commits:

```
feat(langgraph): add cycle detection to state graph
fix(checkpoint): handle concurrent writes to same thread_id
docs(sdk-py): clarify streaming API usage
```
