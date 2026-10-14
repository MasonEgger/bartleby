# ABOUTME: Writes bartleby.yml: sets one dotted key in place and renders the full annotated config.
# The one writer shared by `config set`, `enable`, and `new site --full-config`.

"""Comment-preserving edits to ``bartleby.yml`` and the full annotated config.

Entry points:

* :func:`set_key` sets one dotted key in existing config text and returns the new text.
* :func:`append_to_list` adds one item to a list key, such as a ``nav`` entry.
* :func:`render_full_config` renders every option in a schema, each with its one-line
  description as a comment above it, on top of a base config.
* :func:`write_config_text` writes the result to disk atomically.

The edits go through one :class:`ruamel.yaml.YAML` round-trip instance, so comments,
key order, and indentation in a file a person wrote survive, as do a byte order mark
and CRLF line endings. This module is the one writer shared by ``config set``,
``enable``, and ``--full-config``; nothing else serializes ``bartleby.yml``. The
dotted-path walk (``split_path`` and ``existing_prefix``) lives in
:mod:`bartleby.config_model`, shared with the ``--set`` override layer.
"""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import YAMLError
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
from ruamel.yaml.tokens import CommentToken

from bartleby.config_model import ConfigError, existing_prefix, split_path, yaml_location

if TYPE_CHECKING:
    from collections.abc import Iterable

    from bartleby.config_schema import ConfigField

BOM = "\ufeff"

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


def ensure_parent_mapping(root: CommentedMap, segments: list[str]) -> CommentedMap:
    """Walk to the mapping that holds the last segment, building missing ones.

    :param root: The top-level mapping.
    :param segments: A path from :func:`split_path`.
    :returns: The mapping that holds ``segments[-1]``.
    :raises ConfigError: If an intermediate key holds something other than a mapping.
    """
    node, depth = existing_prefix(root, segments)
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


def _load_document(text: str, source: Path | str | None) -> CommentedMap | None:
    """Parse config text as a round-trip mapping; ``None`` when it holds no keys.

    :param text: The file contents.
    :param source: The file, named in the error.
    :raises ConfigError: If the text is not valid YAML (a repeated key, a tab indent)
        or its root is not a mapping.
    """
    try:
        loaded: Any = _YAML.load(text)
    except YAMLError as exc:
        problem = getattr(exc, "problem", None) or "syntax error"
        raise ConfigError(
            f"invalid YAML{yaml_location(exc)}: {problem}",
            hint="fix the syntax at that line (check indentation, quotes, brackets, "
            "and repeated keys)",
            source=source,
        ) from exc
    if loaded is None:
        return None
    if not isinstance(loaded, CommentedMap):
        raise ConfigError(
            "config root must be a YAML mapping",
            hint="start with top-level keys such as `site:`, one per line",
            source=source,
        )
    return loaded


def _dump_like(original: str, root: CommentedMap, preamble: str = "") -> str:
    """Serialize ``root`` in the style of ``original``: its byte order mark and line endings.

    :param original: The text the document was loaded from.
    :param root: The edited document.
    :param preamble: Text (a leading comment block) to keep ahead of the first key.
    """
    text = preamble + _dump(root)
    if "\r\n" in original:
        text = text.replace("\n", "\r\n")
    return BOM + text if original.startswith(BOM) else text


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


_STR_TAG = "tag:yaml.org,2002:str"
_PLAIN_RESOLVER = yaml.resolver.Resolver()


def _round_trip(value: object) -> object:
    """Convert plain dicts and lists, recursively, to ruamel containers, quoting lookalikes.

    ``_trailing_slot`` walks only ``CommentedMap`` and ``CommentedSeq``, so a plain
    container appended as a value hides the comment slot of its own last leaf. A string
    that PyYAML's YAML 1.1 reader would type as something else (``Yes``, ``on``, ``1e3``)
    is written double-quoted, so the loader reads back the string ruamel wrote.
    """
    if isinstance(value, dict):
        return CommentedMap((key, _round_trip(item)) for key, item in value.items())
    if isinstance(value, list):
        return CommentedSeq(_round_trip(item) for item in value)
    if isinstance(value, str) and _plain_tag(value) != _STR_TAG:
        return DoubleQuotedScalarString(value)
    return value


def _plain_tag(text: str) -> str:
    """The tag PyYAML gives ``text`` when it stands unquoted in a YAML document."""
    # types-PyYAML leaves Resolver.resolve untyped; it returns the tag string.
    tag: str = _PLAIN_RESOLVER.resolve(yaml.ScalarNode, text, (True, False))  # type: ignore[no-untyped-call]
    return tag


def _detach_trailing_comment(holder: CommentedMap | CommentedSeq) -> CommentToken | None:
    """Take the blank line and comment that follow ``holder``'s last leaf off that leaf.

    ruamel stores the blank line and comment above the next key on the last leaf of the
    container before it. A plain append would land under that comment, so the part
    after the last leaf's own line comment is split off for :func:`_attach_trailing_comment`.
    """
    if not holder:
        return None
    container, last, slot = _trailing_slot(holder)
    entry = container.ca.items.get(last)
    existing = entry[slot] if entry else None
    if not isinstance(existing, CommentToken):
        return None
    text: str = existing.value
    if text.startswith("\n"):
        moved = text
        entry[slot] = None
    else:
        line_end = text.index("\n") + 1
        moved = "\n" + text[line_end:] if text[line_end:] else ""
        existing.value = text[:line_end]
    return CommentToken(moved, existing.start_mark, None) if moved else None


def _attach_trailing_comment(
    holder: CommentedMap | CommentedSeq, token: CommentToken | None
) -> None:
    """Put a comment from :func:`_detach_trailing_comment` on ``holder``'s new last leaf."""
    if token is None:
        return
    container, last, slot = _trailing_slot(holder)
    entry = container.ca.items.setdefault(last, [None, None, None, None])
    entry[slot] = token


def _append_key(holder: CommentedMap, key: str, value: object) -> None:
    """Add a new key at the end of ``holder``, leaving the next key's comment below it."""
    token = _detach_trailing_comment(holder)
    holder[key] = value
    _attach_trailing_comment(holder, token)


def set_key(
    text: str, dotted_path: str, value: object, *, source: Path | str | None = None
) -> str:
    """Set one dotted key in ``bartleby.yml`` text, keeping comments and key order.

    Missing intermediate mappings are created. Python ``str``, ``int``, ``bool``,
    ``list``, and ``dict`` values are written as the matching YAML types. A file that
    holds only comments keeps them above the new key.

    :param text: The current file contents; empty text starts a new document.
    :param dotted_path: The key to set, such as ``site.title``.
    :param value: The new value.
    :param source: The file the text came from, named in a YAML error.
    :returns: The updated file contents.
    :raises ConfigError: If the text is not valid YAML, the path is malformed, or it
        passes through a non-mapping value.
    """
    segments = split_path(dotted_path)
    value = _round_trip(value)
    loaded = _load_document(text, source)
    root = loaded if loaded is not None else CommentedMap()

    # Missing parents become one nested value so the new branch is added in a single step.
    holder, depth = existing_prefix(root, segments)
    key = segments[depth]
    for segment in reversed(segments[depth + 1 :]):
        value = CommentedMap({segment: value})
    if key in holder:
        holder[key] = value
    else:
        _append_key(holder, key, value)

    return _dump_like(text, root, _comment_preamble(text) if loaded is None else "")


def _comment_preamble(text: str) -> str:
    """The comment lines of a document with no keys, ready to sit above the first key."""
    stripped = text.removeprefix(BOM).replace("\r\n", "\n").strip()
    return f"{stripped}\n" if stripped else ""


def append_to_list(
    text: str, dotted_path: str, item: object, *, source: Path | str | None = None
) -> str:
    """Append one item to a list key, keeping the list's other items and their comments.

    :param text: The current file contents.
    :param dotted_path: The list key, such as ``nav``; a missing or null key becomes a list.
    :param item: The item to append.
    :param source: The file the text came from, named in a YAML error.
    :returns: The updated file contents.
    :raises ConfigError: If the text is not valid YAML or the key holds a non-list value.
    """
    segments = split_path(dotted_path)
    root = _load_document(text, source) or CommentedMap()
    holder = ensure_parent_mapping(root, segments)
    current = holder.get(segments[-1])
    if current is None:
        current = CommentedSeq()
        holder[segments[-1]] = current
    if not isinstance(current, CommentedSeq):
        raise ConfigError(
            f"{dotted_path} is not a list, so nothing can be appended to it",
            key_path=dotted_path,
            hint=f"replace the value of {dotted_path} with a list first",
            source=source,
        )
    token = _detach_trailing_comment(current)
    current.append(_round_trip(item))
    _attach_trailing_comment(current, token)
    return _dump_like(text, root)


def write_config_text(config_path: Path, text: str) -> None:
    """Write ``bartleby.yml`` atomically: a temp file beside it, then one rename.

    The one place the config file is written, so a file that cannot be written is one
    error. A read-only file is left alone rather than replaced through the directory.

    :param config_path: The file to write.
    :param text: The complete new contents.
    :raises ConfigError: If the file or its directory is not writable.
    """
    if config_path.exists() and not os.access(config_path, os.W_OK):
        raise ConfigError(
            "config file is read-only",
            hint=f"make it writable (chmod u+w {config_path.name}) or edit it by hand",
            source=config_path,
        )
    staged: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=config_path.parent,
            prefix=f".{config_path.name}.",
            delete=False,
        ) as handle:
            staged = handle.name
            handle.write(text)
        os.replace(staged, config_path)
    except OSError as exc:
        if staged is not None:
            Path(staged).unlink(missing_ok=True)
        raise ConfigError(
            f"cannot write config file ({exc.strerror or exc})",
            hint=f"check the permissions of {config_path.parent}",
            source=config_path,
        ) from exc


EXAMPLES_HEADING = "Uncomment to add a content type or taxonomy, and rename `example`."


def render_full_config(schema: Iterable[ConfigField], base: str = "") -> str:
    """Render every schema field, each with its description above it, over ``base``.

    A key ``base`` already sets keeps its value; every other key is written at its
    default. A required key ``base`` lacks gets a placeholder, marked in its comment, so
    the file loads as written. Repeatable fields (a ``<name>`` segment) render as one
    commented-out example named ``example`` above the key that follows them, so the file
    defines no content type or taxonomy of its own.

    :param schema: The fields to render, usually :data:`bartleby.config_schema.CONFIG_SCHEMA`.
    :param base: Config text to start from, such as the scaffold's ``bartleby.yml``.
    :returns: A complete ``bartleby.yml``.
    :raises ConfigError: If ``base`` is not a YAML mapping.
    """
    root = _load_document(base, None) or CommentedMap()
    examples = CommentedMap()
    follower: str | None = None
    for entry in schema:
        if entry.repeatable:
            _render_field(examples, entry, example_path(entry.path), keep=False)
            continue
        if examples and follower is None:
            follower = entry.path.split(".")[0]
        _render_field(root, entry, entry.path.split("."), keep=True)

    if follower is not None:
        block = f"{EXAMPLES_HEADING}\n{_dump(examples).rstrip()}\n"
        root.yaml_set_comment_before_after_key(follower, before=block)
    return _dump_like(base, root)


def _render_field(
    root: CommentedMap, entry: ConfigField, segments: list[str], *, keep: bool
) -> None:
    """Write one field into ``root`` at ``segments`` with its description above it.

    :param keep: Whether a value already at the key is left as it is.
    """
    holder = ensure_parent_mapping(root, segments)
    key = segments[-1]
    description = entry.description
    if not (keep and holder.get(key) is not None):
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
