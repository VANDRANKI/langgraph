"""Public constants for the LangGraph core library.

This module exposes the stable, public-facing constants used throughout
LangGraph graphs and the Pregel runtime.

Public constants
----------------

- :data:`START` -- sentinel name for the implicit entry node of every graph.
- :data:`END` -- sentinel name for the implicit exit node of every graph.
- :data:`TAG_NOSTREAM` -- attach to a chat model call to suppress its tokens
  from streaming output.
- :data:`TAG_HIDDEN` -- attach to a node or edge to hide it from LangSmith
  tracing and certain streaming environments.

Deprecated re-exports
---------------------

For backwards compatibility, accessing ``Send`` or ``Interrupt`` through
this module is still allowed but emits a :class:`~langgraph.warnings.LangGraphDeprecatedSinceV10`
warning.  Import them from :mod:`langgraph.types` instead.

Private constants (e.g. ``CONF``, ``TASKS``, ``CONFIG_KEY_CHECKPOINTER``)
are also temporarily re-exported for downstream consumers that relied on
them before they were made private, but those usages should be migrated.
"""

import sys
from typing import Any
from warnings import warn

from langgraph._internal._constants import (
    CONF,
    CONFIG_KEY_CHECKPOINTER,
    TASKS,
)
from langgraph.warnings import LangGraphDeprecatedSinceV10

__all__ = (
    "TAG_NOSTREAM",
    "TAG_HIDDEN",
    "START",
    "END",
    # retained for backwards compatibility (mostly langgraph-api), should be removed in v2 (or earlier)
    "CONF",
    "TASKS",
    "CONFIG_KEY_CHECKPOINTER",
)

# --- Public constants ---
TAG_NOSTREAM = sys.intern("nostream")
"""Tag to disable streaming for a chat model.

Attach this tag to a :class:`~langchain_core.language_models.BaseChatModel`
call (via ``model.with_config(tags=[TAG_NOSTREAM])``) to prevent its token
stream from being surfaced through the graph's stream output.  Useful when
you want a model call to happen silently (e.g., an internal classification
step whose output should not reach the user).
"""

TAG_HIDDEN = sys.intern("langsmith:hidden")
"""Tag to hide a node/edge from certain tracing/streaming environments.

Attach this tag to suppress a call from appearing in LangSmith traces or
certain streaming views.  Unlike :data:`TAG_NOSTREAM`, which suppresses
token-level output, ``TAG_HIDDEN`` suppresses the run/span entirely from
the observability layer.
"""

END = sys.intern("__end__")
"""The last (maybe virtual) node in graph-style Pregel.

Adding an edge to ``END`` signals that control flow should exit the graph
after the current step.  Every graph must have at least one path that
reaches ``END``.
"""

START = sys.intern("__start__")
"""The first (maybe virtual) node in graph-style Pregel.

Edges from ``START`` define which nodes receive the initial input when the
graph is invoked.  Use ``graph.add_edge(START, "my_node")`` or the
``set_entry_point`` convenience method.
"""


def __getattr__(name: str) -> Any:
    if name in ["Send", "Interrupt"]:
        warn(
            f"Importing {name} from langgraph.constants is deprecated. "
            f"Please use 'from langgraph.types import {name}' instead.",
            LangGraphDeprecatedSinceV10,
            stacklevel=2,
        )

        from importlib import import_module

        module = import_module("langgraph.types")
        return getattr(module, name)

    try:
        from importlib import import_module

        private_constants = import_module("langgraph._internal._constants")
        attr = getattr(private_constants, name)
        warn(
            f"Importing {name} from langgraph.constants is deprecated. "
            f"This constant is now private and should not be used directly. "
            "Please let the LangGraph team know if you need this value.",
            LangGraphDeprecatedSinceV10,
            stacklevel=2,
        )
        return attr
    except AttributeError:
        pass

    raise AttributeError(f"module has no attribute '{name}'")
