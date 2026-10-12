# ABOUTME: Writes bartleby.yml: sets one dotted key in place and renders the full annotated config.
# The one writer shared by `config set`, `enable`, and `new site --full-config`.

"""Comment-preserving edits to ``bartleby.yml`` and the full annotated config.

Two entry points:

* :func:`set_key` sets one dotted key in existing config text and returns the new text.
* :func:`render_full_config` renders every option in a schema at its default, each
  with its one-line description as a comment above it.

Both go through one :class:`ruamel.yaml.YAML` round-trip instance, so comments, key
order, and indentation in a file a person wrote survive an edit. This module is the
one writer shared by ``config set``, ``enable``, and ``--full-config``; nothing else
serializes ``bartleby.yml``. :func:`split_path` and :func:`ensure_parent_mapping` are the
shared dotted-path walk that ``config get`` and the override layer reuse.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.tokens import CommentToken

from bartleby.config import ConfigError

if TYPE_CHECKING:
    from collections.abc import Iterable

    from bartleby.config_schema import ConfigField

# The name that stands in for each user-chosen `<name>` path segment in the full config.
EXAMPLE_NAME = "example"

# Values for required fields, which have no default but must be present for the file to load.
_REQUIRED_PLACEHOLDERS: dict[str, object] = {
    "site.title": "My Site",
    "site.url": "https://example.com",
    "content_types.<name>.path": "posts",
    "content_types.<name>.metadata.<field>.type": "string",
}

# Appended to a placeholder's comment so a reader knows to change the value.
PLACEHOLDER_MARKER = "(Example value; replace it.)"


def example_path(schema_path: str) -> list[str]:
    """Split a schema path, naming each ``<placeholder>`` segment ``example``.

    :param schema_path: A path from :data:`bartleby.config_schema.CONFIG_SCHEMA`.
    :returns: The segments :func:`render_full_config` writes for that field.
    """
    return [EXAMPLE_NAME if part.startswith("<") else part for part in schema_path.split(".")]


_YAML = YAML(typ="rt")
_YAML.preserve_quotes = True
_YAML.indent(mapping=2, sequence=4, offset=2)
_YAML.width = 4096


def split_path(dotted_path: str) -> list[str]:
    """Split a dotted key path into its segments.

    :param dotted_path: A path such as ``site.feed.limit``.
    :returns: The segments, in order.
    :raises ConfigError: If the path is empty or has an empty segment.
    """
    segments = dotted_path.split(".")
    if not all(segments):
        raise ConfigError(
            f"invalid key path {dotted_path!r}",
            key_path=dotted_path,
            hint="use dotted names such as site.title",
        )
    return segments


def _existing_prefix(root: CommentedMap, segments: list[str]) -> tuple[CommentedMap, int]:
    """Walk the parent segments that already hold mappings.

    :returns: The deepest existing mapping and how many parent segments lead to it.
    :raises ConfigError: If a parent key holds something other than a mapping or null.
    """
    node = root
    for depth, segment in enumerate(segments[:-1], start=1):
        child = node.get(segment)
        if child is None:
            return node, depth - 1
        if not isinstance(child, CommentedMap):
            walked = ".".join(segments[:depth])
            raise ConfigError(
                f"{walked} is not a mapping, so it cannot hold {segments[depth]!r}",
                key_path=walked,
                hint=f"replace the value of {walked} with a mapping first",
            )
        node = child
    return node, len(segments) - 1


def ensure_parent_mapping(root: CommentedMap, segments: list[str]) -> CommentedMap:
    """Walk to the mapping that holds the last segment, building missing ones.

    :param root: The top-level mapping.
    :param segments: A path from :func:`split_path`.
    :returns: The mapping that holds ``segments[-1]``.
    :raises ConfigError: If an intermediate key holds something other than a mapping.
    """
    node, depth = _existing_prefix(root, segments)
    for segment in segments[depth:-1]:
        child = CommentedMap()
        node[segment] = child
        node = child
    return node


def _dump(root: object) -> str:
    """Serialize a round-trip document to text."""
    buffer = io.StringIO()
    _YAML.dump(root, buffer)
    return buffer.getvalue()


def _trailing_slot(
    node: CommentedMap | CommentedSeq,
) -> tuple[CommentedMap | CommentedSeq, int | str, int]:
    """Find where ruamel stores the comment that follows ``node``'s last leaf.

    :returns: The container, its last key or index, and the slot in ``ca.items``
        (2 for a mapping key, 0 for a sequence item).
    """
    while True:
        if isinstance(node, CommentedMap):
            key = list(node)[-1]
            child = node[key]
            if isinstance(child, (CommentedMap, CommentedSeq)) and child:
                node = child
                continue
            return node, key, 2
        index = len(node) - 1
        child = node[index]
        if isinstance(child, (CommentedMap, CommentedSeq)) and child:
            node = child
            continue
        return node, index, 0


def _append_key(holder: CommentedMap, key: str, value: object) -> None:
    """Add a new key at the end of ``holder``, leaving the next key's comment below it.

    ruamel stores the blank line and comment above the next top-level key on the
    last leaf of the mapping before it. A plain assignment would append under that
    comment, so the part after the last leaf's own line comment moves to the new key.
    """
    token: CommentToken | None = None
    if holder:
        container, last, slot = _trailing_slot(holder)
        entry = container.ca.items.get(last)
        existing = entry[slot] if entry else None
        if isinstance(existing, CommentToken):
            text: str = existing.value
            if text.startswith("\n"):
                moved = text
                entry[slot] = None
            else:
                line_end = text.index("\n") + 1
                moved = "\n" + text[line_end:] if text[line_end:] else ""
                existing.value = text[:line_end]
            if moved:
                token = CommentToken(moved, existing.start_mark, None)

    holder[key] = value
    if token is not None:
        container, last, slot = _trailing_slot(holder)
        entry = container.ca.items.setdefault(last, [None, None, None, None])
        entry[slot] = token


def set_key(text: str, dotted_path: str, value: object) -> str:
    """Set one dotted key in ``bartleby.yml`` text, keeping comments and key order.

    Missing intermediate mappings are created. Python ``str``, ``int``, ``bool``,
    ``list``, and ``dict`` values are written as the matching YAML types.

    :param text: The current file contents; empty text starts a new document.
    :param dotted_path: The key to set, such as ``site.title``.
    :param value: The new value.
    :returns: The updated file contents.
    :raises ConfigError: If the path is malformed or passes through a non-mapping value.
    """
    segments = split_path(dotted_path)
    loaded: Any = _YAML.load(text) if text.strip() else None
    root = loaded if loaded is not None else CommentedMap()
    if not isinstance(root, CommentedMap):
        raise ConfigError(
            "config root must be a YAML mapping",
            hint="start with top-level keys such as `site:`, one per line",
        )

    # Missing parents become one nested value so the new branch is added in a single step.
    holder, depth = _existing_prefix(root, segments)
    key = segments[depth]
    for segment in reversed(segments[depth + 1 :]):
        value = CommentedMap({segment: value})
    if key in holder:
        holder[key] = value
    else:
        _append_key(holder, key, value)

    return _dump(root)


def render_full_config(schema: Iterable[ConfigField]) -> str:
    """Render every schema field at its default, each with its description above it.

    A ``<name>`` path segment renders as one example instance named ``example``.
    Required fields get a placeholder, marked in its comment, so the file loads as written.

    :param schema: The fields to render, usually :data:`bartleby.config_schema.CONFIG_SCHEMA`.
    :returns: A complete ``bartleby.yml``.
    """
    root = CommentedMap()
    for entry in schema:
        segments = example_path(entry.path)
        holder = ensure_parent_mapping(root, segments)
        key = segments[-1]
        description = entry.description
        value: object = entry.default
        if entry.path in _REQUIRED_PLACEHOLDERS:
            value = _REQUIRED_PLACEHOLDERS[entry.path]
            description = f"{description} {PLACEHOLDER_MARKER}"
        elif isinstance(entry.default, tuple):
            value = list(entry.default)
        holder[key] = value

        # Describe the key from the line above it, indented to its depth.
        holder.yaml_set_comment_before_after_key(
            key, before=description, indent=2 * (len(segments) - 1)
        )

    return _dump(root)
