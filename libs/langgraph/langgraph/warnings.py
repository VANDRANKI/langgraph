"""LangGraph specific warnings."""

from __future__ import annotations

__all__ = (
    "LangGraphDeprecationWarning",
    "LangGraphDeprecatedSinceV05",
    "LangGraphDeprecatedSinceV10",
    "LangGraphDeprecatedSinceV11",
)


class LangGraphDeprecationWarning(DeprecationWarning):
    """A LangGraph specific deprecation warning.

    Subclasses this from the built-in `DeprecationWarning` so that it can be
    selectively silenced or enabled independently of other deprecation notices
    in user code (e.g. ``warnings.filterwarnings("error",
    category=LangGraphDeprecationWarning)``).

    Attributes:
        message: Human-readable description of what is deprecated and what to
            use instead.
        since: ``(major, minor)`` tuple indicating the LangGraph release in
            which the deprecation was introduced.
        expected_removal: ``(major, minor)`` tuple indicating the first
            LangGraph release in which the deprecated functionality is
            expected to be **removed**.  Defaults to ``(since[0] + 1, 0)``
            when not specified explicitly.

    Inspired by the Pydantic ``PydanticDeprecationWarning`` class, which sets
    a great standard for deprecation warnings with clear versioning
    information.
    """

    message: str
    since: tuple[int, int]
    expected_removal: tuple[int, int]

    def __init__(
        self,
        message: str,
        *args: object,
        since: tuple[int, int],
        expected_removal: tuple[int, int] | None = None,
    ) -> None:
        """Initialise a :class:`LangGraphDeprecationWarning`.

        Args:
            message: Human-readable deprecation description.  A trailing
                period is stripped automatically so that the formatted
                ``__str__`` output is grammatically consistent.
            *args: Additional positional arguments forwarded to
                :class:`DeprecationWarning` (and ultimately to
                :class:`Warning`).
            since: ``(major, minor)`` version tuple for when the deprecation
                was introduced, e.g. ``(1, 0)`` for v1.0.
            expected_removal: ``(major, minor)`` version tuple for the
                planned removal release.  When omitted, defaults to
                ``(since[0] + 1, 0)`` (i.e. the next major version).
        """
        super().__init__(message, *args)
        self.message = message.rstrip(".")
        self.since = since
        self.expected_removal = (
            expected_removal if expected_removal is not None else (since[0] + 1, 0)
        )

    def __str__(self) -> str:
        """Return a human-readable deprecation notice including version info.

        The returned string follows the pattern::

            <message>. Deprecated in LangGraph V<since_major>.<since_minor>
            to be removed in V<removal_major>.<removal_minor>.

        Returns:
            Formatted deprecation message with ``since`` and
            ``expected_removal`` version numbers appended.
        """
        return (
            f"{self.message}. Deprecated in LangGraph "
            f"V{self.since[0]}.{self.since[1]}"
            f" to be removed in "
            f"V{self.expected_removal[0]}.{self.expected_removal[1]}."
        )


class LangGraphDeprecatedSinceV05(LangGraphDeprecationWarning):
    """Deprecation warning for functionality removed since LangGraph v0.5.0.

    Expected removal: v2.0.
    """

    def __init__(self, message: str, *args: object) -> None:
        """Initialise with ``since=(0, 5)`` and ``expected_removal=(2, 0)``.

        Args:
            message: Human-readable deprecation description.
            *args: Additional positional arguments forwarded to the base class.
        """
        super().__init__(message, *args, since=(0, 5), expected_removal=(2, 0))


class LangGraphDeprecatedSinceV10(LangGraphDeprecationWarning):
    """Deprecation warning for functionality deprecated since LangGraph v1.0.0.

    Expected removal: v2.0.
    """

    def __init__(self, message: str, *args: object) -> None:
        """Initialise with ``since=(1, 0)`` and ``expected_removal=(2, 0)``.

        Args:
            message: Human-readable deprecation description.
            *args: Additional positional arguments forwarded to the base class.
        """
        super().__init__(message, *args, since=(1, 0), expected_removal=(2, 0))


class LangGraphDeprecatedSinceV11(LangGraphDeprecationWarning):
    """Deprecation warning for functionality deprecated since LangGraph v1.1.0.

    Expected removal: v3.0.
    """

    def __init__(self, message: str, *args: object) -> None:
        """Initialise with ``since=(1, 1)`` and ``expected_removal=(3, 0)``.

        Args:
            message: Human-readable deprecation description.
            *args: Additional positional arguments forwarded to the base class.
        """
        super().__init__(message, *args, since=(1, 1), expected_removal=(3, 0))
