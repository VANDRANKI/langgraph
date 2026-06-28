# Graph Testing Patterns

This guide covers strategies for unit-testing and integration-testing LangGraph
graphs without running expensive LLM calls on every test invocation.

## 1. Testing nodes in isolation

Each node is a plain Python function. Test it directly without involving the
graph runner.

```python
from myapp.graph import classify_intent

def test_classify_intent_routes_billing():
    state = {"message": "I need help with my invoice"}
    result = classify_intent(state)
    assert result["intent"] == "billing"
```

## 2. Stubbing LLM calls with a fake model

Replace your LLM with a deterministic stub so tests run offline and
instantaneously.

```python
from langchain_core.language_models.fake import FakeListChatModel
from myapp.graph import build_graph

def test_happy_path(monkeypatch):
    fake_llm = FakeListChatModel(responses=["Paris"])
    graph = build_graph(llm=fake_llm)
    result = graph.invoke({"question": "Capital of France?"})
    assert result["answer"] == "Paris"
```

## 3. Verifying state transitions

Inspect intermediate states by streaming events rather than reading only the
final output.

```python
def test_state_transitions():
    graph = build_graph(llm=fake_llm)
    states = list(graph.stream({"question": "Capital of France?"}))
    node_names = [list(s.keys())[0] for s in states]
    assert node_names == ["retrieve", "generate"]
```

## 4. Checkpoint round-trip test

Verify that a graph can pause, serialise its state, and resume correctly.

```python
from langgraph.checkpoint.memory import MemorySaver

def test_checkpoint_resume():
    checkpointer = MemorySaver()
    graph = build_graph(llm=fake_llm, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-thread"}}

    # First invocation — interrupted by human-in-the-loop node.
    graph.invoke({"question": "Approve spend?"}, config=config)

    # Resume after human approval.
    result = graph.invoke(None, config=config)
    assert result["approved"] is True
```

## 5. Testing conditional edges

Invoke the graph with inputs that exercise each branch of a conditional edge.

```python
@pytest.mark.parametrize("score,expected_node", [
    (0.9, "high_confidence_path"),
    (0.3, "low_confidence_path"),
])
def test_conditional_routing(score, expected_node):
    graph = build_graph(llm=FakeListChatModel(responses=[str(score)]))
    events = list(graph.stream({"query": "test"}))
    visited = {list(e.keys())[0] for e in events}
    assert expected_node in visited
```

## Anti-patterns to avoid

| Anti-pattern | Problem | Fix |
|---|---|---|
| Real LLM in unit tests | Slow, costly, non-deterministic | `FakeListChatModel` or monkeypatch |
| Asserting on raw LLM text | Fragile | Assert on parsed fields |
| No thread ID in config | Checkpoint not stored | Always pass `thread_id` |
| Inspecting only final state | Misses routing bugs | Stream and collect all events |
