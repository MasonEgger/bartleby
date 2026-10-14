# ABOUTME: Shared formatter for structured error messages.
# One helper builds "source: key path: message (fix: hint)" for every error type.

"""The message contract behind Bartleby's structured errors.

Every user-facing error from a YAML-backed module (``ConfigError``, ``AuthorError``,
``ThemeError``, ``ShortcodeError``, ``AgentSurfaceError``, and the page errors collected
by a build) renders through :func:`format_error`, so a newcomer sees the same shape
everywhere::

    <source>: <key path>: <message> (fix: <hint>)

* ``source`` names the file (or directory) the problem lives in.
* ``key path`` names the field or id inside it, such as ``site.url`` or
  ``content_types.blog.metadata.rating.type``.
* ``message`` says what is wrong.
* ``hint`` says what to change, in terms the reader can act on.

Any part may be absent; only ``message`` is required.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def format_error(
    message: str,
    *,
    source: Path | str | None = None,
    key_path: str | None = None,
    hint: str | None = None,
) -> str:
    """Join the parts of an error into one message line.

    Args:
        message: What is wrong.
        source: The file or directory the problem lives in.
        key_path: The dotted key path or id inside ``source``.
        hint: A concrete fix.

    Returns:
        ``"<source>: <key path>: <message> (fix: <hint>)"`` with absent parts dropped.
    """
    location = ": ".join(str(part) for part in (source, key_path) if part)
    text = f"{location}: {message}" if location else message
    return f"{text} (fix: {hint})" if hint else text
