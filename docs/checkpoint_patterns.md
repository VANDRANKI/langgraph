# LangGraph Checkpoint Patterns

This guide covers common patterns and pitfalls when using LangGraph checkpointers.
It applies to all three backends: in-memory, SQLite (`checkpoint-sqlite`), and
Postgres (`checkpoint-postgres`).

## Thread IDs and Checkpoint Keys

Every checkpoint is keyed by `(thread_id, checkpoint_id)`. A single thread can
have multiple checkpoints — one per node invocation or per explicit save call.

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

checkpointer = MemorySaver()
graph = build_graph().compile(checkpointer=checkpointer)

# thread_id identifies the conversation or session.
# Use a stable ID (e.g., user_id or session UUID) — not a random ID per call.
config = {"configurable": {"thread_id": "user-42-session-1"}}
result = graph.invoke({"messages": [...]}, config)
```

**Common mistake**: generating a new `thread_id` per call loses all history.
The checkpoint is stored under the previous ID and never read again.

## Reading Checkpoints

```python
# Get the latest checkpoint for a thread
checkpoint_tuple = checkpointer.get_tuple(
    {"configurable": {"thread_id": "user-42-session-1"}}
)
if checkpoint_tuple is None:
    # No checkpoint exists yet for this thread_id
    print("Fresh session")
else:
    state = checkpoint_tuple.checkpoint["channel_values"]
    print(f"Last state: {state}")
```

Use `aget_tuple` for async code:

```python
checkpoint_tuple = await checkpointer.aget_tuple(
    {"configurable": {"thread_id": "user-42-session-1"}}
)
```

## Listing Checkpoints

To iterate over all checkpoints for a thread (newest first):

```python
for cp in checkpointer.list(
    {"configurable": {"thread_id": "user-42-session-1"}},
    limit=10,
):
    print(cp.checkpoint_id, cp.metadata)
```

This is useful for implementing undo/redo or audit logging.

## Serialization Requirements

Checkpointers serialize state via `JsonPlusSerializer` (the default). This handles:
- Python primitives (`str`, `int`, `float`, `bool`, `None`)
- `list` and `dict` (nested, recursive)
- Pydantic v2 models (serialized to dict)
- `datetime`, `UUID`, `Enum`

**What it does NOT handle automatically**:
- Custom classes without `__dict__` (use Pydantic instead)
- Generators or callables stored in state
- Database connection objects

If your state contains a custom class, annotate it as a Pydantic model:

```python
from pydantic import BaseModel
from typing import Annotated
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages

class MyState(BaseModel):
    messages: Annotated[list, add_messages]
    metadata: dict = {}
    step: int = 0
```

## Postgres Checkpointer

For production, use `AsyncPostgresSaver` from `langgraph-checkpoint-postgres`:

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import asyncpg

async def main():
    conn = await asyncpg.connect("postgresql://user:pass@host/db")
    checkpointer = AsyncPostgresSaver(conn)
    # Run migrations once on startup:
    await checkpointer.setup()
    graph = build_graph().compile(checkpointer=checkpointer)
    ...
```

**Important**: call `await checkpointer.setup()` exactly once to create the
tables. Calling it on every request is safe (it's idempotent) but adds latency.

## SQLite Checkpointer (Dev Only)

SQLite is convenient for local development but not suitable for production
because it uses file-level locking:

```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

async with AsyncSqliteSaver.from_conn_string(":memory:") as checkpointer:
    graph = build_graph().compile(checkpointer=checkpointer)
    result = await graph.ainvoke(...)
```

Use `:memory:` for tests; use a file path (`/tmp/dev.db`) for local dev.

## Clearing Checkpoints

To delete all checkpoints for a thread (e.g., user logout or session reset):

```python
# There is no built-in delete method in the base interface.
# For SQLite/Postgres, query the DB directly:
await conn.execute(
    "DELETE FROM checkpoints WHERE thread_id = $1",
    "user-42-session-1",
)
```

## Testing with Checkpoints

For unit tests, use `MemorySaver` — it requires no setup:

```python
from langgraph.checkpoint.memory import MemorySaver

def test_graph_resumes_from_checkpoint():
    checkpointer = MemorySaver()
    graph = build_graph().compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-thread"}}

    # First invocation
    graph.invoke({"messages": ["hello"]}, config)

    # Second invocation should resume from saved state
    result = graph.invoke({"messages": ["follow-up"]}, config)
    assert len(result["messages"]) > 1  # both messages in history
```
