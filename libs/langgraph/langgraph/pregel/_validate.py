"""Graph structure validation helpers for the Pregel execution engine.

This module is called once during `StateGraph.compile()` (via
`Pregel.__init__`) to assert that the graph is well-formed before any
execution begins.  Catching structural problems at compile time produces
clear `ValueError` / `TypeError` messages instead of cryptic `KeyError`
or `AttributeError` failures at runtime.

The two public functions are:

- `validate_graph` — full graph-level check: reserved names, channel
  existence, input/output reachability, interrupt node membership.
- `validate_keys` — lightweight check that a set of keys exist inside
  a channel mapping (used when reading partial state).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from langgraph._internal._constants import RESERVED
from langgraph.channels.base import BaseChannel
from langgraph.managed.base import ManagedValueMapping
from langgraph.pregel._read import PregelNode
from langgraph.types import All


def validate_graph(
    nodes: Mapping[str, PregelNode],
    channels: dict[str, BaseChannel],
    managed: ManagedValueMapping,
    input_channels: str | Sequence[str],
    output_channels: str | Sequence[str],
    stream_channels: str | Sequence[str] | None,
    interrupt_after_nodes: All | Sequence[str],
    interrupt_before_nodes: All | Sequence[str],
) -> None:
    """Validate the compiled graph for structural correctness.

    Performs the following checks in order:

    1. No channel, managed value, or node name collides with a reserved
       LangGraph identifier (e.g. ``__start__``, ``__end__``).
    2. Every channel read by each node exists in `channels` or `managed`.
    3. Every channel that a node subscribes to (its *triggers*) exists in
       `channels`.
    4. Every `input_channels` entry exists in `channels` **and** is
       subscribed to by at least one node.  If none of the input channels
       are subscribed to, graph execution would immediately stall.
    5. Every `output_channels` and `stream_channels` entry exists in
       `channels`.
    6. Every node listed in `interrupt_after_nodes` /
       `interrupt_before_nodes` exists in `nodes` (unless the value is
       the ``"*"`` wildcard).

    Args:
        nodes: Mapping of node name to `PregelNode` instance as produced
            by `StateGraph.compile()`.
        channels: Mapping of channel name to `BaseChannel` instance
            covering all state channels registered in the graph.
        managed: Mapping of managed-value name to managed-value spec
            (e.g. `SharedValue` channels that live outside normal state).
        input_channels: The channel name(s) that receive the initial graph
            input.  Either a single string or a sequence of strings.
        output_channels: The channel name(s) whose values form the final
            graph output.  Either a single string or a sequence of strings.
        stream_channels: Optional channel name(s) to stream during
            execution.  ``None`` disables explicit stream-channel streaming.
        interrupt_after_nodes: Node names (or ``"*"``) after which
            execution should pause for human-in-the-loop review.
        interrupt_before_nodes: Node names (or ``"*"``) before which
            execution should pause for human-in-the-loop review.

    Raises:
        ValueError: If any of the structural checks listed above fail.
        TypeError: If a value in `nodes` is not a `PregelNode` instance.
    """
    for chan in channels:
        if chan in RESERVED:
            raise ValueError(f"Channel name '{chan}' is reserved")
    for name in managed:
        if name in RESERVED:
            raise ValueError(f"Managed name '{name}' is reserved")

    subscribed_channels = set[str]()
    for name, node in nodes.items():
        if name in RESERVED:
            raise ValueError(f"Node name '{name}' is reserved")
        if isinstance(node, PregelNode):
            subscribed_channels.update(node.triggers)
            if isinstance(node.channels, str):
                if node.channels not in channels:
                    raise ValueError(
                        f"Node {name} reads channel '{node.channels}' "
                        f"not in known channels: '{repr(sorted(channels))[:100]}'"
                    )
            else:
                for chan in node.channels:
                    if chan not in channels and chan not in managed:
                        raise ValueError(
                            f"Node {name} reads channel '{chan}' "
                            f"not in known channels: '{repr(sorted(channels))[:100]}'"
                        )
        else:
            raise TypeError(
                f"Invalid node type {type(node)}, expected PregelNode or NodeBuilder"
            )

    for chan in subscribed_channels:
        if chan not in channels:
            raise ValueError(
                f"Subscribed channel '{chan}' not "
                f"in known channels: '{repr(sorted(channels))[:100]}'"
            )

    if isinstance(input_channels, str):
        if input_channels not in channels:
            raise ValueError(
                f"Input channel '{input_channels}' not "
                f"in known channels: '{repr(sorted(channels))[:100]}'"
            )
        if input_channels not in subscribed_channels:
            raise ValueError(
                f"Input channel {input_channels} is not subscribed to by any node"
            )
    else:
        for chan in input_channels:
            if chan not in channels:
                raise ValueError(
                    f"Input channel '{chan}' not in '{repr(sorted(channels))[:100]}'"
                )
        if all(chan not in subscribed_channels for chan in input_channels):
            raise ValueError(
                f"None of the input channels {input_channels} "
                f"are subscribed to by any node"
            )

    all_output_channels = set[str]()
    if isinstance(output_channels, str):
        all_output_channels.add(output_channels)
    else:
        all_output_channels.update(output_channels)
    if isinstance(stream_channels, str):
        all_output_channels.add(stream_channels)
    elif stream_channels is not None:
        all_output_channels.update(stream_channels)

    for chan in all_output_channels:
        if chan not in channels:
            raise ValueError(
                f"Output channel '{chan}' not "
                f"in known channels: '{repr(sorted(channels))[:100]}'"
            )

    if interrupt_after_nodes != "*":
        for n in interrupt_after_nodes:
            if n not in nodes:
                raise ValueError(f"Node {n} not in nodes")
    if interrupt_before_nodes != "*":
        for n in interrupt_before_nodes:
            if n not in nodes:
                raise ValueError(f"Node {n} not in nodes")


def validate_keys(
    keys: str | Sequence[str] | None,
    channels: Mapping[str, Any],
) -> None:
    """Validate that every key in `keys` exists in `channels`.

    Used before reading a partial state snapshot to give a clear error
    message when the caller requests a channel that does not exist, rather
    than letting a `KeyError` propagate from deep inside the runner.

    Args:
        keys: A single channel name, a sequence of channel names, or
            ``None``.  ``None`` is treated as "no keys to validate" and
            the function returns immediately.
        channels: The mapping of channel names to `BaseChannel` instances
            (or any value) that should contain every key in `keys`.

    Raises:
        ValueError: If any key in `keys` is absent from `channels`.

    Example:
        ```python
        validate_keys("messages", graph.channels)   # single key
        validate_keys(["messages", "context"], graph.channels)  # multiple keys
        validate_keys(None, graph.channels)         # no-op
        ```
    """
    if isinstance(keys, str):
        if keys not in channels:
            raise ValueError(f"Key {keys} not in channels")
    elif keys is not None:
        for chan in keys:
            if chan not in channels:
                raise ValueError(f"Key {chan} not in channels")
