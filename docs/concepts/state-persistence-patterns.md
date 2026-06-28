# State Persistence Patterns in LangGraph

LangGraph's checkpointer system lets you pause, resume, and fork stateful
graph runs. This guide covers the three main persistence patterns and when
to use each.

## Overview

Every `StateGraph` can be compiled with a checkpointer:

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

graph = StateGraph(MyState)
# ... add nodes and edges ...

app = graph.compile(checkpointer=MemorySaver())
```

A **thread** is an isolated conversation or task identified by `thread_id`.
Checkpointers save state snapshots after every node execution, making threads
resumable after interrupts or crashes.

---

## Pattern 1: In-Memory (Development)

```python
from langgraph.checkpoint.memory import MemorySaver

app = graph.compile(checkpointer=MemorySaver())

config = {"configurable": {"thread_id": "user-123"}}

# First turn
result = app.invoke({"messages": [("human", "Hello")]}, config)

# Second turn — state is automatically continued from the checkpoint
result = app.invoke({"messages": [("human", "What did I just say?")]}, config)
```

**Use when**: local development, unit tests, ephemeral sessions.
**Limitation**: state is lost on process restart.

---

## Pattern 2: SQLite (Local Persistence)

```bash
pip install langgraph-checkpoint-sqlite
```

```python
from langgraph.checkpoint.sqlite import SqliteSaver

with SqliteSaver.from_conn_string("checkpoints.db") as saver:
    app = graph.compile(checkpointer=saver)
    result = app.invoke({"messages": [...]}, {"configurable": {"thread_id": "abc"}})
```

**Use when**: single-server deployments, CLI tools, notebooks.
**Limitation**: not suitable for horizontally scaled deployments.

---

## Pattern 3: PostgreSQL (Production)

```bash
pip install langgraph-checkpoint-postgres
```

```python
from langgraph.checkpoint.postgres import PostgresSaver

DB_URI = "postgresql://user:pass@host:5432/mydb"

with PostgresSaver.from_conn_string(DB_URI) as saver:
    saver.setup()  # Creates tables on first run — idempotent.
    app = graph.compile(checkpointer=saver)
```

**Use when**: production APIs, multi-server deployments, long-running agents.
**Advantage**: concurrent writes, horizontal scaling, queryable state history.

---

## Inspecting State History

```python
# List all checkpoints for a thread
history = list(app.get_state_history(config))

for snapshot in history:
    print(snapshot.config["configurable"]["checkpoint_id"])
    print(snapshot.values)  # the full state at that point
    print(snapshot.next)    # node(s) that would run next
```

### Time-Travel: Fork from a Past Checkpoint

```python
# Pick a specific past checkpoint
past_config = history[2].config  # 3rd most-recent snapshot

# Resume from that point — creates a new fork, not overwriting the original thread
result = app.invoke(
    {"messages": [("human", "Let's try a different path.")]},
    past_config,
)
```

---

## Human-in-the-Loop Interrupts

Compile with `interrupt_before` to pause before a sensitive node:

```python
app = graph.compile(
    checkpointer=saver,
    interrupt_before=["tool_executor"],  # pause before running tools
)

# Run until the interrupt
app.invoke({"messages": [...]}, config)

# Inspect the pending state
state = app.get_state(config)
print("Pending next step:", state.next)

# Approve and continue (pass None to resume without changing state)
app.invoke(None, config)
```

---

## Choosing a Checkpointer

| Requirement | Recommended Checkpointer |
|-------------|-------------------------|
| Unit tests | `MemorySaver` |
| Single-server, persisted | `SqliteSaver` |
| Multi-server production | `PostgresSaver` |
| Custom storage (S3, DynamoDB) | Subclass `BaseCheckpointSaver` |

---

## Common Pitfalls

- **Missing `thread_id`**: Without a `configurable.thread_id` the graph runs
  statelessly — no checkpoint is read or written.
- **Forgetting `saver.setup()`**: PostgresSaver requires one-time table creation;
  calling it again is safe (idempotent).
- **Large state blobs**: Checkpointers serialise the full state on every node
  execution. Keep binary data (images, embeddings) out of graph state and
  reference it by key from external storage.
