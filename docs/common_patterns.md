# Common LangGraph Patterns

A concise reference for frequently used patterns when building graphs.

---

## State accumulation with `Annotated`

Use `Annotated` with a reducer to accumulate values across nodes:

```python
from typing import TypedDict, Annotated
from operator import add

class AgentState(TypedDict):
    messages: Annotated[list, add]   # each node appends, never overwrites
    error_count: int                  # last-write-wins
```

---

## Conditional routing

```python
from langgraph.graph import END

def route(state: AgentState) -> str:
    if state["error_count"] >= 3:
        return "escalate"
    if state["messages"][-1].content == "DONE":
        return END
    return "continue"

graph.add_conditional_edges(
    "agent",
    route,
    {"continue": "agent", "escalate": "escalate_node", END: END},
)
```

---

## Subgraphs

```python
from langgraph.graph import StateGraph

# Build the subgraph independently
subgraph_builder = StateGraph(SubState)
subgraph_builder.add_node("step", my_step)
subgraph_builder.set_entry_point("step")
subgraph_builder.set_finish_point("step")
subgraph = subgraph_builder.compile()

# Add subgraph as a node in the parent graph
parent_builder = StateGraph(ParentState)
parent_builder.add_node("sub", subgraph)
```

---

## Human-in-the-loop interrupts

```python
from langgraph.types import interrupt

def review_node(state: AgentState) -> dict:
    """Pause for human approval before taking action."""
    decision = interrupt({"action": state["pending_action"]})
    return {"approved": decision == "approve"}
```

Resume with:

```python
graph.invoke(None, config={"configurable": {"thread_id": "1"}},
             command=Command(resume="approve"))
```

---

## Streaming with `astream`

```python
async for chunk in graph.astream(state, stream_mode="updates"):
    for node_name, updates in chunk.items():
        print(f"{node_name}: {updates}")
```
