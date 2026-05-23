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


def process_shortcodes(
    markdown_source: str,
    context: Mapping[str, object],
    jinja_env: jinja2.Environment,
) -> str:
    """Render every ``[% ... %]`` block/inline shortcode in ``markdown_source``.

    :param markdown_source: Raw markdown content (pre-render).
    :param context: Template context shared with shortcode templates.
    :param jinja_env: Bartleby's Jinja2 environment (used to load
        ``shortcodes/{name}.html`` templates).
    :returns: The source with every shortcode replaced by its rendered output.
    :raises ShortcodeError: When a shortcode's template cannot be loaded.
    """
    result_chars: list[str] = []
    cursor = 0
    while cursor < len(markdown_source):
        match = _OPEN_TAG_RE.search(markdown_source, cursor)
        if match is None:
            result_chars.append(markdown_source[cursor:])
            break

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
