# Troubleshooting LangGraph

A reference for common issues encountered when building and running LangGraph
applications.

---

## Graph Execution Issues

### `RecursionError: maximum recursion depth exceeded`

**Cause:** The graph entered an infinite loop — a node keeps routing back to
itself (or through a cycle) without a terminal condition.

**Fix:** Ensure every cycle has a conditional edge that eventually routes to
`END`.

```python
from langgraph.graph import StateGraph, END

def should_continue(state: dict) -> str:
    if state["iteration"] >= state["max_iterations"]:
        return "end"
    return "continue"

graph.add_conditional_edges("agent", should_continue, {"continue": "agent", "end": END})
```

Alternatively, pass `recursion_limit` to `graph.invoke()`:

```python
result = graph.invoke(input_state, config={"recursion_limit": 50})
```

---

### `KeyError` when accessing state

**Cause:** A node references a state key that was not present in the initial
state and has no default value.

**Fix:** Define all keys in the `TypedDict` and provide defaults:

```python
from typing import TypedDict, Annotated
from operator import add

class AgentState(TypedDict):
    messages: Annotated[list, add]
    error_count: int  # always initialise to 0 in the input
```

---

## Checkpointer Issues

### Checkpoint saves fail silently

**Cause:** An async checkpointer is used in a synchronous context (or vice
versa).

**Fix:** Match the checkpointer type to the graph's invocation style:

```python
# Synchronous
from langgraph.checkpoint.sqlite import SqliteSaver
with SqliteSaver.from_conn_string("./checkpoints.db") as memory:
    result = graph.invoke(state, config={"configurable": {"thread_id": "1"}},
                          checkpointer=memory)

# Asynchronous
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
async with AsyncSqliteSaver.from_conn_string("./checkpoints.db") as memory:
    result = await graph.ainvoke(state, config={"configurable": {"thread_id": "1"}},
                                 checkpointer=memory)
```

---

### Migrating from `MemorySaver` to `PostgresSaver`

`MemorySaver` is intended only for prototyping. For production, use
`PostgresSaver` from `langgraph-checkpoint-postgres`.

```bash
pip install langgraph-checkpoint-postgres
```

```python
from langgraph.checkpoint.postgres import PostgresSaver

DB_URI = "postgresql://user:password@localhost:5432/langgraph"

with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup()  # creates the required tables on first run
    result = graph.invoke(state, config={"configurable": {"thread_id": "thread-1"}},
                          checkpointer=checkpointer)
```

---

## Streaming Issues

### Only the final state is returned, not intermediate steps

**Cause:** `graph.invoke()` returns only the final state. Use `stream()` to
observe intermediate updates.

```python
for chunk in graph.stream(state, stream_mode="updates"):
    print(chunk)
```

Use `stream_mode="values"` to receive the full state after each step instead
of just the delta.

---

## Getting Help

- [LangGraph documentation](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangChain Forum](https://forum.langchain.com)
- [GitHub Issues](https://github.com/langchain-ai/langgraph/issues)
