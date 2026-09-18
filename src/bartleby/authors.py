# ABOUTME: Author definition loading, validation, and resolution.
# Parses .authors.yml into typed Author objects and resolves front matter keys.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path


class AuthorError(Exception):
    """Raised when ``.authors.yml`` is malformed or a referenced key is missing."""


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
    parsed: Any = yaml.safe_load(raw_text)

    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise AuthorError(f"{authors_path}: root must be a YAML mapping")

    entries = parsed.get("authors")
    if entries is None:
        return {}
    if not isinstance(entries, dict):
        raise AuthorError(f"{authors_path}: 'authors' must be a mapping")

    result: dict[str, Author] = {}
    for raw_key, definition in entries.items():
        key = str(raw_key)
        if not isinstance(definition, dict):
            raise AuthorError(f"{authors_path}: author {key!r} must be a mapping")
        if "name" not in definition:
            raise AuthorError(f"{authors_path}: author {key!r} is missing required field 'name'")
        result[key] = Author(
            key=key,
            name=str(definition["name"]),
            description=_optional_str(definition.get("description")),
            avatar=_optional_str(definition.get("avatar")),
            url=_optional_str(definition.get("url")),
        )
    return result


def resolve_authors(keys: list[str], authors: dict[str, Author]) -> list[Author]:
    """Resolve a list of author keys to :class:`Author` objects in order.

    :param keys: Author keys referenced in page front matter.
    :param authors: The authors mapping returned by :func:`load_authors`.
    :returns: Ordered list of :class:`Author` objects matching ``keys``.
    :raises AuthorError: If any key is not present in ``authors``.
    """
    resolved: list[Author] = []
    for key in keys:
        if key not in authors:
            raise AuthorError(f"unknown author key: {key!r}")
        resolved.append(authors[key])
    return resolved


def _optional_str(value: Any) -> str | None:
    """Return ``str(value)`` when ``value`` is not ``None``, else ``None``."""
    return None if value is None else str(value)
