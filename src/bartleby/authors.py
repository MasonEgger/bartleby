# ABOUTME: Author definition loading, validation, and resolution.
# Parses .authors.yml into typed Author objects and resolves front matter keys.

"""Author loading and resolution.

Error-message contract: an :class:`AuthorError` renders as
``<authors file>: authors.<id>: <message> (fix: <hint>)`` (see
:func:`bartleby.errors.format_error`). It names the authors file whenever the error comes
from reading it, names the author id when one entry is at fault, and always ends with a
hint. A reference to an unknown id lists the ids the file does define.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import yaml

from bartleby.errors import format_error

if TYPE_CHECKING:
    from pathlib import Path


class AuthorError(Exception):
    """Raised when ``.authors.yml`` is malformed or a referenced key is missing.

    :ivar message: What is wrong.
    :ivar author_id: The author id at fault, or ``None`` when the whole file is.
    :ivar hint: A concrete fix.
    :ivar source: The authors file, or ``None`` when the caller did not supply it.
    """

    def __init__(
        self,
        message: str,
        *,
        author_id: str | None = None,
        hint: str | None = None,
        source: Path | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.author_id = author_id
        self.hint = hint
        self.source = source

    def __str__(self) -> str:
        key_path = f"authors.{self.author_id}" if self.author_id is not None else None
        return format_error(self.message, source=self.source, key_path=key_path, hint=self.hint)


class _UniqueKeyLoader(yaml.SafeLoader):
    """A safe YAML loader that rejects a mapping key written twice.

    Plain YAML keeps the last duplicate silently, which would drop an author.
    """

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
        seen: set[str] = set()
        for key_node, _ in node.value:
            if not isinstance(key_node, yaml.ScalarNode):
                continue
            if key_node.value in seen:
                raise yaml.constructor.ConstructorError(
                    None, None, f"duplicate key {key_node.value!r}", key_node.start_mark
                )
            seen.add(key_node.value)
        return super().construct_mapping(node, deep=deep)


@dataclass(slots=True)
class Author:
    """A single author definition loaded from ``.authors.yml``.

    :ivar key: The mapping key from the authors file (e.g. ``"mason"``).
    :ivar name: The author's display name.
    :ivar description: Optional short biography or tagline.
    :ivar avatar: Optional URL to an avatar image.
    :ivar url: Optional URL to the author's website or profile.
    """

    key: str
    name: str
    description: str | None
    avatar: str | None
    url: str | None


def load_authors(authors_path: Path) -> dict[str, Author]:
    """Load author definitions from a YAML file.

    :param authors_path: Path to ``.authors.yml`` (or equivalent).
    :returns: Mapping of author key to :class:`Author` object. Returns an empty
        mapping if the file does not exist.
    :raises AuthorError: If the file is malformed or any entry is missing ``name``.
    """
    if not authors_path.exists():
        return {}

    raw_text = authors_path.read_text(encoding="utf-8")
    try:
        parsed: Any = yaml.load(raw_text, Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise AuthorError(
            _yaml_problem(exc),
            hint="remove the repeated id or fix the syntax at that line",
            source=authors_path,
        ) from exc

    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise AuthorError(
            "root must be a YAML mapping",
            hint="start the file with `authors:` and one indented entry per author",
            source=authors_path,
        )

    entries = parsed.get("authors")
    if entries is None:
        return {}
    if not isinstance(entries, dict):
        raise AuthorError(
            "'authors' must be a mapping",
            hint="write one `<id>:` entry per author, indented under `authors:`",
            source=authors_path,
        )

    result: dict[str, Author] = {}
    for raw_key, definition in entries.items():
        key = str(raw_key)
        if not isinstance(definition, dict):
            raise AuthorError(
                "author must be a mapping",
                author_id=key,
                hint=f"write `name:` indented under `{key}:`",
                source=authors_path,
            )
        if "name" not in definition:
            raise AuthorError(
                "missing required field 'name'",
                author_id=key,
                hint=f"add a `name:` line under `{key}:`",
                source=authors_path,
            )
        result[key] = Author(
            key=key,
            name=str(definition["name"]),
            description=_optional_str(definition.get("description")),
            avatar=_optional_str(definition.get("avatar")),
            url=_optional_str(definition.get("url")),
        )
    return result


def _yaml_problem(exc: yaml.YAMLError) -> str:
    """Describe a YAML failure as ``problem at line N``."""
    problem = getattr(exc, "problem", None) or "invalid YAML"
    mark = getattr(exc, "problem_mark", None)
    return f"{problem} at line {mark.line + 1}" if mark is not None else str(problem)


def resolve_authors(
    keys: list[str], authors: dict[str, Author], *, source: Path | None = None
) -> list[Author]:
    """Resolve a list of author keys to :class:`Author` objects in order.

    :param keys: Author keys referenced in page front matter.
    :param authors: The authors mapping returned by :func:`load_authors`.
    :param source: The authors file, named in the error when a key is unknown.
    :returns: Ordered list of :class:`Author` objects matching ``keys``.
    :raises AuthorError: If any key is not present in ``authors``.
    """
    resolved: list[Author] = []
    for key in keys:
        if key not in authors:
            raise AuthorError(
                f"unknown author key {key!r}",
                hint=unknown_author_hint(authors),
                source=source,
            )
        resolved.append(authors[key])
    return resolved


def unknown_author_hint(authors: dict[str, Author]) -> str:
    """Return the fix for a reference to an author id the authors file does not define."""
    known = ", ".join(authors) or "none defined"
    return f"use one of the known author ids ({known}), or add the id to the authors file"


def _optional_str(value: Any) -> str | None:
    """Return ``str(value)`` when ``value`` is not ``None``, else ``None``."""
    return None if value is None else str(value)
