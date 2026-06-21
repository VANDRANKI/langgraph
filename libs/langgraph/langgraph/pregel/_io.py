from __future__ import annotations

from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from typing import Any, Literal

from langgraph._internal._constants import (
    ERROR,
    INTERRUPT,
    NULL_TASK_ID,
    RESUME,
    RETURN,
    TASKS,
)
from langgraph._internal._typing import EMPTY_SEQ, MISSING
from langgraph.channels.base import BaseChannel, EmptyChannelError
from langgraph.constants import START, TAG_HIDDEN
from langgraph.errors import InvalidUpdateError
from langgraph.pregel._log import logger
from langgraph.types import Command, PregelExecutableTask, Send


def read_channel(
    channels: Mapping[str, BaseChannel],
    chan: str,
    *,
    catch: bool = True,
) -> Any:
    """Read the current value of a single channel.

    Args:
        channels: Mapping of channel name to `BaseChannel` instance.
        chan: The name of the channel to read.
        catch: If ``True`` (the default), an `EmptyChannelError` is
            swallowed and ``None`` is returned in its place.  Set to
            ``False`` when the caller needs to distinguish between an
            empty channel and a channel whose value *is* ``None``.

    Returns:
        The current value stored in the channel, or ``None`` if the
        channel is empty and `catch` is ``True``.

    Raises:
        EmptyChannelError: If the channel is empty and `catch` is
            ``False``.
        KeyError: If `chan` is not present in `channels`.
    """
    try:
        return channels[chan].get()
    except EmptyChannelError:
        if catch:
            return None
        else:
            raise


def read_channels(
    channels: Mapping[str, BaseChannel],
    select: Sequence[str] | str,
    *,
    skip_empty: bool = True,
) -> dict[str, Any] | Any:
    """Read one or more channels and return their current values.

    When `select` is a single string, behaves identically to
    `read_channel(channels, select)` — the raw channel value is returned
    (not wrapped in a dict).

    When `select` is a sequence of strings, returns a dict mapping each
    channel name to its value.  Empty channels are omitted by default;
    set `skip_empty=False` to raise `EmptyChannelError` on the first
    empty channel encountered instead.

    Args:
        channels: Mapping of channel name to `BaseChannel` instance.
        select: A single channel name or a sequence of channel names to
            read.
        skip_empty: Only relevant when `select` is a sequence.  If
            ``True`` (the default), empty channels are silently excluded
            from the returned dict.  If ``False``, an `EmptyChannelError`
            is raised for the first empty channel found.

    Returns:
        - If `select` is a string: the raw value from that channel (or
          ``None`` if empty, matching `read_channel` default behaviour).
        - If `select` is a sequence: a ``dict[str, Any]`` containing only
          the non-empty channels (when `skip_empty=True`), or all channels
          (when `skip_empty=False`, raising on empty).

    Raises:
        EmptyChannelError: If `skip_empty` is ``False`` and any of the
            selected channels is empty.
        KeyError: If any channel name in `select` is absent from
            `channels`.
    """
    if isinstance(select, str):
        return read_channel(channels, select)
    else:
        values: dict[str, Any] = {}
        for k in select:
            try:
                values[k] = read_channel(channels, k, catch=not skip_empty)
            except EmptyChannelError:
                pass
        return values


def map_command(cmd: Command) -> Iterator[tuple[str, str, Any]]:
    """Map a `Command` object to a sequence of pending writes.

    Each pending write is a 3-tuple ``(task_id, channel, value)`` where
    `task_id` is `NULL_TASK_ID` (meaning the write originates from graph
    input rather than a running node).

    Args:
        cmd: The `Command` to translate.  Its `.goto`, `.resume`, and
            `.update` fields are each translated independently.

    Yields:
        3-tuples of ``(task_id, channel, value)``:
        - For each `Send` in `cmd.goto`: ``(NULL_TASK_ID, TASKS, send)``
        - For each str in `cmd.goto`: ``(NULL_TASK_ID, "branch:to:<name>", START)``
        - For `cmd.resume`: ``(NULL_TASK_ID, RESUME, cmd.resume)``
        - For each ``(k, v)`` in `cmd.update`: ``(NULL_TASK_ID, k, v)``

    Raises:
        InvalidUpdateError: If `cmd.graph` is `Command.PARENT` (no parent
            graph is available at this call site).
        TypeError: If an entry in `cmd.goto` is neither a `Send` nor a
            `str`.
    """
    if cmd.graph == Command.PARENT:
        raise InvalidUpdateError("There is no parent graph")
    if cmd.goto:
        if isinstance(cmd.goto, (tuple, list)):
            sends = cmd.goto
        else:
            sends = [cmd.goto]
        for send in sends:
            if isinstance(send, Send):
                yield (NULL_TASK_ID, TASKS, send)
            elif isinstance(send, str):
                yield (NULL_TASK_ID, f"branch:to:{send}", START)
            else:
                raise TypeError(
                    f"In Command.goto, expected Send/str, got {type(send).__name__}"
                )
    if cmd.resume is not None:
        yield (NULL_TASK_ID, RESUME, cmd.resume)
    if cmd.update:
        for k, v in cmd._update_as_tuples():
            yield (NULL_TASK_ID, k, v)


def map_input(
    input_channels: str | Sequence[str],
    chunk: dict[str, Any] | Any | None,
) -> Iterator[tuple[str, Any]]:
    """Map an input chunk to a sequence of pending channel writes.

    This is the entry point that converts raw user-supplied input (the
    argument passed to `graph.invoke()` / `graph.stream()`) into the
    internal ``(channel, value)`` write format consumed by the Pregel
    runner.

    Args:
        input_channels: The channel name(s) declared as graph inputs.  If
            a single string, the entire `chunk` is written to that channel.
            If a sequence of strings, `chunk` must be a ``dict`` and each
            key that matches an input channel is written individually;
            keys not in `input_channels` are silently ignored with a
            warning log.
        chunk: The raw input value.  ``None`` is treated as an empty
            input and causes the function to yield nothing.  When
            `input_channels` is a sequence, `chunk` must be a ``dict``.

    Yields:
        2-tuples of ``(channel_name, value)`` ready to be appended to the
        Pregel runner's pending-writes queue.

    Raises:
        TypeError: If `input_channels` is a sequence but `chunk` is not
            a ``dict``.
    """
    if chunk is None:
        return
    elif isinstance(input_channels, str):
        yield (input_channels, chunk)
    else:
        if not isinstance(chunk, dict):
            raise TypeError(f"Expected chunk to be a dict, got {type(chunk).__name__}")
        for k in chunk:
            if k in input_channels:
                yield (k, chunk[k])
            else:
                logger.warning(f"Input channel {k} not found in {input_channels}")


def map_output_values(
    output_channels: str | Sequence[str],
    pending_writes: Literal[True] | Sequence[tuple[str, Any]],
    channels: Mapping[str, BaseChannel],
) -> Iterator[dict[str, Any] | Any]:
    """Map pending writes (a sequence of tuples (channel, value)) to output chunk."""
    if isinstance(output_channels, str):
        if pending_writes is True or any(
            chan == output_channels for chan, _ in pending_writes
        ):
            yield read_channel(channels, output_channels)
    else:
        if pending_writes is True or {
            c for c, _ in pending_writes if c in output_channels
        }:
            yield read_channels(channels, output_channels)


def map_output_updates(
    output_channels: str | Sequence[str],
    tasks: list[tuple[PregelExecutableTask, Sequence[tuple[str, Any]]]],
    cached: bool = False,
) -> Iterator[dict[str, Any | dict[str, Any]]]:
    """Map pending writes (a sequence of tuples (channel, value)) to output chunk."""
    output_tasks = [
        (t, ww)
        for t, ww in tasks
        if (not t.config or TAG_HIDDEN not in t.config.get("tags", EMPTY_SEQ))
        and ww[0][0] != ERROR
        and ww[0][0] != INTERRUPT
    ]
    if not output_tasks:
        return
    updated: list[tuple[str, Any]] = []
    for task, writes in output_tasks:
        rtn = next((value for chan, value in writes if chan == RETURN), MISSING)
        if rtn is not MISSING:
            updated.append((task.name, rtn))
        elif isinstance(output_channels, str):
            updated.extend(
                (task.name, value) for chan, value in writes if chan == output_channels
            )
        elif any(chan in output_channels for chan, _ in writes):
            counts = Counter(chan for chan, _ in writes)
            if any(counts[chan] > 1 for chan in output_channels):
                updated.extend(
                    (
                        task.name,
                        {chan: value},
                    )
                    for chan, value in writes
                    if chan in output_channels
                )
            else:
                updated.append(
                    (
                        task.name,
                        {
                            chan: value
                            for chan, value in writes
                            if chan in output_channels
                        },
                    )
                )
    grouped: dict[str, Any] = {t.name: [] for t, _ in output_tasks}
    for node, value in updated:
        grouped[node].append(value)
    for node, value in grouped.items():
        if len(value) == 0:
            grouped[node] = None
        if len(value) == 1:
            grouped[node] = value[0]
    if cached:
        grouped["__metadata__"] = {"cached": cached}
    yield grouped
