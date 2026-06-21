"""Runtime configuration helpers for LangGraph graph nodes and functional API tasks.

This module exposes three public helpers — `get_config`, `get_store`, and
`get_stream_writer` — that can be called from inside any running LangGraph
node or `@entrypoint` task to retrieve the active `RunnableConfig`, the
configured `BaseStore`, or the active `StreamWriter` respectively.

All three functions rely on a `contextvars.ContextVar` populated by the
PregelRunner at the start of each task execution.  They therefore raise
`RuntimeError` when called outside of a running LangGraph context.

Async caveat
-----------
Context-variable propagation to tasks created with `asyncio.create_task` was
only added in Python 3.11.  When running LangGraph asynchronously on Python
< 3.11, the context variable may not be visible inside the spawned task and
the helpers will raise `RuntimeError`.  Use Python >= 3.11 for full async
support.
"""

import asyncio
import sys
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.config import var_child_runnable_config
from langgraph.store.base import BaseStore

from langgraph._internal._constants import CONF, CONFIG_KEY_RUNTIME
from langgraph.types import StreamWriter


def _no_op_stream_writer(c: Any) -> None:
    """A stream writer that silently discards all values.

    Used as the default `StreamWriter` when no custom stream is configured,
    so that node code calling `get_stream_writer()` never needs to guard
    against a ``None`` writer.

    Args:
        c: The value to discard.  Accepts any type.
    """


def get_config() -> RunnableConfig:
    """Return the active `RunnableConfig` for the currently executing LangGraph task.

    This function reads the config from a `contextvars.ContextVar` that the
    PregelRunner populates at the start of every node invocation.  It is
    therefore only valid when called from inside a running graph node or a
    `@task` / `@entrypoint` function.

    !!! warning "Async with Python < 3.11"
        On Python < 3.11 the context variable is **not** propagated to
        `asyncio.create_task` coroutines.  Calling this function from an
        async context on Python < 3.11 will raise `RuntimeError`.

    Returns:
        The `RunnableConfig` for the current execution context, including
        all LangGraph-specific keys under the `"configurable"` key.

    Raises:
        RuntimeError: If called outside of a running LangGraph context, or
            if called from an async context on Python < 3.11.

    Example:
        ```python
        from langgraph.config import get_config

        def my_node(state):
            config = get_config()
            thread_id = config["configurable"].get("thread_id")
            return state
        ```
    """
    if sys.version_info < (3, 11):
        try:
            if asyncio.current_task():
                raise RuntimeError(
                    "Python 3.11 or later required to use this in an async context"
                )
        except RuntimeError:
            pass
    if var_config := var_child_runnable_config.get():
        return var_config
    else:
        raise RuntimeError("Called get_config outside of a runnable context")


def get_store() -> BaseStore:
    """Access LangGraph store from inside a graph node or entrypoint task at runtime.

    Can be called from inside any [`StateGraph`][langgraph.graph.StateGraph] node or
    functional API [`task`][langgraph.func.task], as long as the `StateGraph` or the [`entrypoint`][langgraph.func.entrypoint]
    was initialized with a store, e.g.:

    ```python
    # with StateGraph
    graph = (
        StateGraph(...)
        ...
        .compile(store=store)
    )

    # or with entrypoint
    @entrypoint(store=store)
    def workflow(inputs):
        ...
    ```

    !!! warning "Async with Python < 3.11"

        If you are using Python < 3.11 and are running LangGraph asynchronously,
        `get_store()` won't work since it uses [`contextvar`](https://docs.python.org/3/library/contextvars.html) propagation (only available in [Python >= 3.11](https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task)).


    Example: Using with `StateGraph`
        ```python
        from typing_extensions import TypedDict
        from langgraph.graph import StateGraph, START
        from langgraph.store.memory import InMemoryStore
        from langgraph.config import get_store

        store = InMemoryStore()
        store.put(("values",), "foo", {"bar": 2})


        class State(TypedDict):
            foo: int


        def my_node(state: State):
            my_store = get_store()
            stored_value = my_store.get(("values",), "foo").value["bar"]
            return {"foo": stored_value + 1}


        graph = (
            StateGraph(State)
            .add_node(my_node)
            .add_edge(START, "my_node")
            .compile(store=store)
        )

        graph.invoke({"foo": 1})
        ```

        ```pycon
        {"foo": 3}
        ```

    Example: Using with functional API
        ```python
        from langgraph.func import entrypoint, task
        from langgraph.store.memory import InMemoryStore
        from langgraph.config import get_store

        store = InMemoryStore()
        store.put(("values",), "foo", {"bar": 2})


        @task
        def my_task(value: int):
            my_store = get_store()
            stored_value = my_store.get(("values",), "foo").value["bar"]
            return stored_value + 1


        @entrypoint(store=store)
        def workflow(value: int):
            return my_task(value).result()


        workflow.invoke(1)
        ```

        ```pycon
        3
        ```
    """
    return get_config()[CONF][CONFIG_KEY_RUNTIME].store


def get_stream_writer() -> StreamWriter:
    """Access LangGraph [`StreamWriter`][langgraph.types.StreamWriter] from inside a graph node or entrypoint task at runtime.

    Can be called from inside any [`StateGraph`][langgraph.graph.StateGraph] node or
    functional API [`task`][langgraph.func.task].

    !!! warning "Async with Python < 3.11"

        If you are using Python < 3.11 and are running LangGraph asynchronously,
        `get_stream_writer()` won't work since it uses [`contextvar`](https://docs.python.org/3/library/contextvars.html) propagation (only available in [Python >= 3.11](https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task)).

    Example: Using with `StateGraph`
        ```python
        from typing_extensions import TypedDict
        from langgraph.graph import StateGraph, START
        from langgraph.config import get_stream_writer


        class State(TypedDict):
            foo: int


        def my_node(state: State):
            my_stream_writer = get_stream_writer()
            my_stream_writer({"custom_data": "Hello!"})
            return {"foo": state["foo"] + 1}


        graph = (
            StateGraph(State)
            .add_node(my_node)
            .add_edge(START, "my_node")
            .compile(store=store)
        )

        for chunk in graph.stream({"foo": 1}, stream_mode="custom"):
            print(chunk)
        ```

        ```pycon
        {"custom_data": "Hello!"}
        ```

    Example: Using with functional API
        ```python
        from langgraph.func import entrypoint, task
        from langgraph.config import get_stream_writer


        @task
        def my_task(value: int):
            my_stream_writer = get_stream_writer()
            my_stream_writer({"custom_data": "Hello!"})
            return value + 1


        @entrypoint(store=store)
        def workflow(value: int):
            return my_task(value).result()


        for chunk in workflow.stream(1, stream_mode="custom"):
            print(chunk)
        ```

        ```pycon
        {"custom_data": "Hello!"}
        ```
    """
    runtime = get_config()[CONF][CONFIG_KEY_RUNTIME]
    return runtime.stream_writer
