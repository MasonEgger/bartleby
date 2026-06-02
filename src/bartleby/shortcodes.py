# ABOUTME: Shortcode preprocessing — parse [% %] syntax and render as Jinja2 fragments.
# Resolves shortcodes/{name}.html templates before markdown rendering runs.

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import jinja2

if TYPE_CHECKING:
    from collections.abc import Mapping


class ShortcodeError(Exception):
    """Raised when a shortcode references a missing template or invalid syntax."""


_OPEN_TAG_RE = re.compile(r"\[%\s*([a-zA-Z_][\w-]*)((?:\s+[^%]*?)?)\s*%\]")
_CLOSE_TAG_RE = re.compile(r"\[%\s*/([a-zA-Z_][\w-]*)\s*%\]")
_ARG_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
_FENCED_BLOCK_RE = re.compile(r"(^|\n)(```|~~~)[^\n]*\n.*?\n\2(?=\n|$)", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def process_shortcodes(
    markdown_source: str,
    context: Mapping[str, object],
    jinja_env: jinja2.Environment,
) -> str:
    """Render every ``[% ... %]`` block/inline shortcode in ``markdown_source``.

    Fenced code blocks (triple-backtick or triple-tilde) and inline ``code``
    spans are left untouched — shortcode syntax shown inside them is
    treated as literal text, not as an invocation.

    :param markdown_source: Raw markdown content (pre-render).
    :param context: Template context shared with shortcode templates.
    :param jinja_env: Bartleby's Jinja2 environment (used to load
        ``shortcodes/{name}.html`` templates).
    :returns: The source with every shortcode replaced by its rendered output.
    :raises ShortcodeError: When a shortcode's template cannot be loaded.
    """
    protected_spans = _collect_protected_spans(markdown_source)
    result_chars: list[str] = []
    cursor = 0
    while cursor < len(markdown_source):
        match = _OPEN_TAG_RE.search(markdown_source, cursor)
        if match is None:
            result_chars.append(markdown_source[cursor:])
            break

        if _span_is_protected(match.start(), match.end(), protected_spans):
            # Step over the protected region in one go so we don't keep
            # re-matching the same protected token.
            protected_end = _enclosing_protected_end(match.start(), protected_spans)
            result_chars.append(markdown_source[cursor:protected_end])
            cursor = protected_end
            continue

        result_chars.append(markdown_source[cursor : match.start()])
        name = match.group(1)
        args_text = match.group(2) or ""
        arguments = dict(_ARG_RE.findall(args_text))

        close_pattern = re.compile(rf"\[%\s*/{re.escape(name)}\s*%\]")
        close_match = close_pattern.search(markdown_source, match.end())
        if close_match is not None:
            content = markdown_source[match.end() : close_match.start()].strip()
            cursor = close_match.end()
        else:
            content = ""
            cursor = match.end()

        rendered = _render_shortcode(name, arguments, content, context, jinja_env)
        result_chars.append(rendered)

    return "".join(result_chars)


def _collect_protected_spans(source: str) -> list[tuple[int, int]]:
    """Return (start, end) spans of fenced code blocks and inline code spans."""
    spans: list[tuple[int, int]] = []
    for match in _FENCED_BLOCK_RE.finditer(source):
        spans.append((match.start(), match.end()))
    for match in _INLINE_CODE_RE.finditer(source):
        spans.append((match.start(), match.end()))
    spans.sort()
    return spans


def _span_is_protected(start: int, end: int, protected: list[tuple[int, int]]) -> bool:
    """True when ``[start, end)`` overlaps any protected span."""
    for protected_start, protected_end in protected:
        if protected_end <= start:
            continue
        if protected_start >= end:
            break
        return True
    return False


def _enclosing_protected_end(position: int, protected: list[tuple[int, int]]) -> int:
    """Return the end of the protected span containing ``position`` (or ``position + 1``)."""
    for protected_start, protected_end in protected:
        if protected_start <= position < protected_end:
            return protected_end
    return position + 1


def _render_shortcode(
    name: str,
    arguments: dict[str, str],
    content: str,
    context: Mapping[str, object],
    jinja_env: jinja2.Environment,
) -> str:
    """Load and render one shortcode template fragment."""
    try:
        template = jinja_env.get_template(f"shortcodes/{name}.html")
    except jinja2.TemplateNotFound as exc:
        raise ShortcodeError(f"unknown shortcode: {name!r}") from exc
    render_context: dict[str, object] = dict(context)
    render_context.update(arguments)
    render_context["content"] = content
    return template.render(**render_context)
