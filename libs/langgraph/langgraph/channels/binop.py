"""Binary-operator aggregate channel for LangGraph state accumulation.

This module defines `BinaryOperatorAggregate`, the channel type that
backs `Annotated[T, operator]` state fields.  Every update received
during a super-step is folded into the running aggregate using the
caller-supplied binary operator (e.g. `operator.add` for lists,
`operator.or_` for dicts).

A special `Overwrite` sentinel allows a single writer per super-step to
replace the accumulated value entirely instead of folding into it.  At
most one `Overwrite` is accepted per super-step; receiving more than one
raises `InvalidUpdateError`.
"""

import collections.abc
from collections.abc import Callable, Sequence
from typing import Any, Generic

from typing_extensions import NotRequired, Required, Self

from langgraph._internal._constants import OVERWRITE
from langgraph._internal._typing import MISSING
from langgraph.channels.base import BaseChannel, Value
from langgraph.errors import (
    EmptyChannelError,
    ErrorCode,
    InvalidUpdateError,
    create_error_message,
)
from langgraph.types import Overwrite

__all__ = ("BinaryOperatorAggregate",)


# Adapted from typing_extensions
def _strip_extras(t):  # type: ignore[no-untyped-def]
    """Recursively strip `Annotated`, `Required`, and `NotRequired` wrappers.

    Python’s `typing` module stores the *origin* of parameterised generics
    (e.g. ``list[int].__origin__ is list``), but `Required` / `NotRequired`
    from `typing_extensions` use ``__origin__`` to hold themselves.  This
    helper peels those wrappers off until a concrete, instantiable type is
    reached.

    Args:
        t: Any type annotation, including generic aliases, `Annotated`,
            `Required`, or `NotRequired` forms.

    Returns:
        The innermost concrete type that can be called to produce an empty
        default value (e.g. ``list``, ``dict``, ``int``).
    """
    if hasattr(t, "__origin__"):
        if t.__origin__ in (Required, NotRequired):
            return _strip_extras(t.__args__[0])
        return _strip_extras(t.__origin__)
    return t


def _get_overwrite(value: Any) -> tuple[bool, Any]:
    """Detect and unwrap an overwrite sentinel from `value`.

    Accepts two representations of an overwrite:

    1. An `Overwrite` instance (the canonical form).
    2. A single-key dict ``{OVERWRITE: v}`` (the serialised/dict form).

    Args:
        value: The update value delivered to `BinaryOperatorAggregate.update`.

    Returns:
        A 2-tuple ``(is_overwrite, overwrite_value)``:

        - If `value` is an overwrite sentinel, returns ``(True, unwrapped_value)``.
        - Otherwise, returns ``(False, None)``.
    """
    if isinstance(value, Overwrite):
        return True, value.value
    if isinstance(value, dict) and len(value) == 1 and OVERWRITE in value:
        return True, value[OVERWRITE]
    return False, None


def _operators_equal(a: Callable, b: Callable) -> bool:
    """Return ``True`` if two reducer operators should be considered equal.

    Lambda functions all share the name ``'<lambda>'``, making identity
    comparison (``a is b``) unreliable for lambdas stored in different
    scopes.  This function treats *any* pairing that includes a lambda as
    equal so that channel equality checks (`__eq__`) work correctly when
    users inline small lambdas as reducers.

    For named functions, identity comparison (``a is b``) is used which
    correctly distinguishes e.g. `operator.add` from `operator.mul`.

    Args:
        a: First callable to compare.
        b: Second callable to compare.

    Returns:
        ``True`` if the two operators should be treated as the same
        reducer, ``False`` otherwise.
    """
    if a.__name__ == "<lambda>" or b.__name__ == "<lambda>":
        return True
    return a is b


class BinaryOperatorAggregate(Generic[Value], BaseChannel[Value, Value, Value]):
    """A channel that accumulates values by folding each update into a running aggregate.

    This channel backs `Annotated[T, reducer]` state fields.  Each time the
    Pregel runner delivers updates to this channel at the end of a super-step,
    every update is applied via the binary operator::

        new_value = operator(current_value, update)

    The operator is applied left-to-right across all updates received in a
    single super-step.  Order among concurrent updates is not guaranteed.

    Special overwrite behaviour
    ---------------------------
    A single update per super-step may be wrapped in an `Overwrite` sentinel
    (or the equivalent dict form ``{OVERWRITE: v}``).  When an overwrite is
    detected, the current accumulated value is replaced outright rather than
    folded in.  Non-overwrite updates delivered in the same super-step that
    arrive *after* the overwrite are ignored; those arriving *before* it are
    folded in normally first, then discarded when the overwrite replaces the
    accumulator.  Receiving more than one `Overwrite` in a single super-step
    raises `InvalidUpdateError`.

    Initial value
    -------------
    On construction, an empty instance of the channel’s type is created by
    calling ``typ()``.  Abstract collection types from `collections.abc`
    (``Sequence``, ``MutableSequence``, ``Set``, ``MutableSet``, ``Mapping``,
    ``MutableMapping``) are mapped to their concrete counterparts (``list``,
    ``set``, ``dict``) before attempting instantiation.  If the type cannot be
    instantiated, the initial value is set to `MISSING`.

    Example:
        ```python
        import operator
        from langgraph.channels.binop import BinaryOperatorAggregate

        # Accumulate integers by addition
        total = BinaryOperatorAggregate(int, operator.add)
        total.update([1, 2, 3])
        assert total.get() == 6

        # Accumulate lists by concatenation
        log = BinaryOperatorAggregate(list, operator.add)
        log.update([["a", "b"], ["c"]])
        assert log.get() == ["a", "b", "c"]
        ```
    """

    __slots__ = ("value", "operator")

    def __init__(self, typ: type[Value], operator: Callable[[Value, Value], Value]):
        super().__init__(typ)
        self.operator = operator
        # special forms from typing or collections.abc are not instantiable
        # so we need to replace them with their concrete counterparts
        typ = _strip_extras(typ)
        if typ in (collections.abc.Sequence, collections.abc.MutableSequence):
            typ = list
        if typ in (collections.abc.Set, collections.abc.MutableSet):
            typ = set
        if typ in (collections.abc.Mapping, collections.abc.MutableMapping):
            typ = dict
        try:
            self.value = typ()
        except Exception:
            self.value = MISSING

    def __eq__(self, value: object) -> bool:
        return isinstance(value, BinaryOperatorAggregate) and _operators_equal(
            self.operator, value.operator
        )

    @property
    def ValueType(self) -> type[Value]:
        """The type of the value stored in the channel."""
        return self.typ

    @property
    def UpdateType(self) -> type[Value]:
        """The type of the update received by the channel."""
        return self.typ

    def copy(self) -> Self:
        """Return a shallow copy of the channel preserving the current accumulated value."""
        empty = self.__class__(self.typ, self.operator)
        empty.key = self.key
        empty.value = self.value
        return empty

    def from_checkpoint(self, checkpoint: Value) -> Self:
        """Return a new channel initialised from a checkpoint value.

        Args:
            checkpoint: A previously serialised channel value as returned by
                `checkpoint()`, or `MISSING` if the channel had no value.

        Returns:
            A new `BinaryOperatorAggregate` with the same type and operator,
            pre-seeded with `checkpoint` (or an empty default if `MISSING`).
        """
        empty = self.__class__(self.typ, self.operator)
        empty.key = self.key
        if checkpoint is not MISSING:
            empty.value = checkpoint
        return empty

    def update(self, values: Sequence[Value]) -> bool:
        """Apply a sequence of updates to the accumulated value.

        For each value in `values`:

        - If it is an `Overwrite` sentinel, replace the current accumulator
          with the sentinel’s inner value.  Only one `Overwrite` is allowed
          per call; a second one raises `InvalidUpdateError`.
        - Otherwise (and if no overwrite has been seen yet), fold it in via
          the channel’s operator: ``self.value = operator(self.value, value)``.

        Args:
            values: Sequence of update values delivered by the Pregel runner.
                May be empty (no-op).

        Returns:
            ``True`` if the channel’s value changed, ``False`` if `values`
            was empty.

        Raises:
            InvalidUpdateError: If more than one `Overwrite` is present in
                `values`.
        """
        if not values:
            return False
        if self.value is MISSING:
            self.value = values[0]
            values = values[1:]
        seen_overwrite: bool = False
        for value in values:
            is_overwrite, overwrite_value = _get_overwrite(value)
            if is_overwrite:
                if seen_overwrite:
                    msg = create_error_message(
                        message="Can receive only one Overwrite value per super-step.",
                        error_code=ErrorCode.INVALID_CONCURRENT_GRAPH_UPDATE,
                    )
                    raise InvalidUpdateError(msg)
                self.value = overwrite_value
                seen_overwrite = True
                continue
            if not seen_overwrite:
                self.value = self.operator(self.value, value)
        return True

    def get(self) -> Value:
        """Return the current accumulated value.

        Raises:
            EmptyChannelError: If the channel has never been updated and the
                channel type could not be default-initialised (i.e. the initial
                value is `MISSING`).
        """
        if self.value is MISSING:
            raise EmptyChannelError()
        return self.value

    def is_available(self) -> bool:
        """Return ``True`` if the channel has a value (not `MISSING`)."""
        return self.value is not MISSING

    def checkpoint(self) -> Value:
        """Return the current accumulated value for serialisation."""
        return self.value
