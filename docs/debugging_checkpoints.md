# Debugging Checkpoints in LangGraph

This guide explains how to inspect, debug, and troubleshoot LangGraph checkpointers.

## What Are Checkpoints?

Checkpoints save the full state of a graph run at each step (node execution).
This enables:
- **Human-in-the-loop**: pause and resume after user input
- **Fault tolerance**: resume after crashes or timeouts
- **Time-travel debugging**: replay or fork from any past state
- **Audit trails**: full history of every state transition

## Choosing a Checkpointer

| Checkpointer | Use Case | Setup |
|---|---|---|
| `MemorySaver` | Development / testing | No setup |
| `SqliteSaver` | Single-process, lightweight | SQLite DB file |
| `AsyncSqliteSaver` | Async single-process | SQLite DB file |
| `PostgresSaver` | Production, multi-process | PostgreSQL connection |
| `AsyncPostgresSaver` | Async production | PostgreSQL connection |

## Inspecting Checkpoint State

```python
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph

# Set up a checkpointer
checkpointer = SqliteSaver.from_conn_string(":memory:")

# Compile graph with checkpointing
graph = workflow.compile(checkpointer=checkpointer)

# Run with a thread ID to enable checkpointing
config = {"configurable": {"thread_id": "my-session-1"}}
result = graph.invoke({"messages": []}, config)

# Inspect the current state
state = graph.get_state(config)
print("Current values:", state.values)
print("Next nodes:", state.next)
print("Config:", state.config)
```

## Viewing State History (Time Travel)

```python
# List all checkpoints for a thread
history = list(graph.get_state_history(config))
for checkpoint in history:
    print(f"Step: {checkpoint.metadata.get('step', 'N/A')}")
    print(f"Node: {checkpoint.metadata.get('source', 'N/A')}")
    print(f"Values: {checkpoint.values}")
    print("---")

# Fork from a past checkpoint (time travel)
past_config = history[-2].config  # Two steps back
branched_result = graph.invoke(None, past_config)
```

## Resuming Interrupted Runs

```python
from langgraph.errors import GraphInterrupt

try:
    result = graph.invoke(inputs, config)
except GraphInterrupt:
    # Graph paused for human input
    print("Waiting for human input...")
    
    # After getting human input:
    human_input = "approved"
    result = graph.invoke(
        {"human_review": human_input},  # Update state
        config  # Same thread ID resumes from checkpoint
    )
```

## Debugging State Transitions

```python
# Stream events to see each node's output
for event in graph.stream(inputs, config, stream_mode="updates"):
    for node_name, node_output in event.items():
        print(f"Node '{node_name}' produced: {node_output}")

# Stream with full state at each step
for state in graph.stream(inputs, config, stream_mode="values"):
    print("Full state after step:", state)
```

## Common Issues

### Checkpoint Not Found

If `get_state()` returns `None`, the thread has no checkpoint yet — the graph
has not been run with that `thread_id`, or the checkpointer was reset.

### State Schema Mismatch

If the graph schema changes after checkpoints are saved, deserialization can
fail. Use versioned thread IDs (e.g. `v2-session-abc`) when making breaking
schema changes, or clear old checkpoints.

### Performance with Postgres

For high-throughput applications, ensure your Postgres connection pool is sized
correctly. Use `AsyncPostgresSaver` with `asyncpg` for best performance.
