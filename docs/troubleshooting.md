# Troubleshooting LangGraph

## Checkpoint issues

### "Concurrent write detected" error

This error means two graph invocations tried to save a checkpoint for the
same thread ID at the same time.

**Fix:** Use a `thread_id` that is unique per concurrent execution:

```python
config = {"configurable": {"thread_id": f"user-{user_id}-{uuid4()}"}}
graph.invoke(input, config=config)
```

### Checkpoint state appears empty after restart

Ensure the checkpointer is passed to the compiled graph, not just to
individual nodes:

```python
# Correct
app = graph.compile(checkpointer=memory)

# Wrong — checkpointer not active
app = graph.compile()
```

## State graph issues

### Node receives unexpected state keys

Check that all state keys are declared in your `TypedDict` schema.
Undeclared keys are silently dropped by the state reducer.

### Streaming stops mid-run

If streaming stops before the `END` node, a node likely raised an
unhandled exception. Wrap your node functions with try/except and
return a partial state update rather than re-raising.

## Common import errors

If you see `ImportError: cannot import name 'StateGraph'`, ensure you are
importing from `langgraph.graph` and not `langgraph` directly:

```python
from langgraph.graph import StateGraph  # correct
```
