"""Type guard utilities for LangGraph checkpoint and state types.

These narrow union types at runtime so downstream code avoids
repeated isinstance checks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeGuard

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver


def is_checkpoint_saver(obj: object) -> "TypeGuard[BaseCheckpointSaver]":
    """Return True if *obj* is a concrete checkpoint saver instance.

    Args:
        obj: Any object to test.

    Returns:
        True when ``obj`` is a ``BaseCheckpointSaver`` subclass instance.
    """
    try:
        from langgraph.checkpoint.base import BaseCheckpointSaver as _Base
        return isinstance(obj, _Base)
    except ImportError:
        return False


def is_non_empty_dict(obj: object) -> "TypeGuard[dict[str, object]]":
    """Return True if *obj* is a non-empty dict.

    Args:
        obj: Any object to test.

    Returns:
        True when ``obj`` is a dict with at least one key.
    """
    return isinstance(obj, dict) and len(obj) > 0
