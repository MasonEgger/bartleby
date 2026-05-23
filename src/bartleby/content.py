# ABOUTME: Content discovery, front matter parsing, and page data objects.
# Walks content/ and produces Page and ColocatedAsset objects for the build pipeline.

from __future__ import annotations

import datetime
import fnmatch
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path

    from bartleby.config import BartlebyConfig


FRONT_MATTER_DELIMITER = "---"

PageMetadataValue = str | int | bool | list[str] | datetime.date


@dataclass(slots=True)
class Page:
    """A single content page discovered under ``content/``.

    Fields set during discovery describe the source; fields set later in the
    pipeline (``output_url``, ``rendered_content``, ``excerpt``, ``readtime``)
    default to empty values and are populated by subsequent build steps.
    """

    source_path: Path
    abs_source_path: Path
    title: str
    description: str | None = None
    date: datetime.date | None = None
    draft: bool = False
    template_override: str | None = None
    url_override: str | None = None
    url_base_override: str | None = None
    author_keys: list[str] = field(default_factory=list)
    taxonomy_values: dict[str, list[str]] = field(default_factory=dict)
    custom_metadata: dict[str, PageMetadataValue] = field(default_factory=dict)
    raw_content: str = ""
    content_type_name: str | None = None
    output_url: str = ""
    rendered_content: str = ""
    excerpt: str = ""
    readtime: int | None = None


@dataclass(slots=True)
class ColocatedAsset:
    """A non-markdown file living next to content; copied as-is at build time."""

    source_path: Path
    abs_source_path: Path
    associated_page_source: Path | None = None


# Front matter fields handled by their own dataclass attributes — anything else
# in the YAML block is treated as a taxonomy value (if it matches a configured
# taxonomy name) or custom metadata.
_STANDARD_FRONT_MATTER_FIELDS = frozenset(
    {
        "title",
        "description",
        "date",
        "draft",
        "template",
        "url",
        "url_base",
        "authors",
        "slug",
    }
)


def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """Split a markdown document into (front matter dict, body).

    :param text: Full text of a markdown file.
    :returns: A ``(metadata, body)`` tuple. When no front matter is present the
        metadata dict is empty and the body is the input text unchanged.
    """
    if not text.startswith(FRONT_MATTER_DELIMITER):
        return {}, text

    after_opening = text[len(FRONT_MATTER_DELIMITER) :]
    closing_marker = f"\n{FRONT_MATTER_DELIMITER}"
    closing = after_opening.find(closing_marker)
    if closing == -1:
        # First line was `---` but no closing delimiter — treat as no front matter.
        return {}, text

    front_matter_block = after_opening[:closing]
    body = after_opening[closing + len(closing_marker) :]
    if body.startswith("\n"):
        body = body[1:]

    if not front_matter_block.strip():
        return {}, body

    parsed: Any = yaml.safe_load(front_matter_block)
    if parsed is None:
        return {}, body
    if not isinstance(parsed, dict):
        return {}, body
    return parsed, body


def should_exclude(path_str: str, patterns: list[str]) -> bool:
    """Return ``True`` when ``path_str`` matches any gitignore-style pattern.

    :param path_str: Path relative to ``content/``, using forward slashes.
    :param patterns: Patterns from ``BartlebyConfig.exclude_patterns``.
    """
    normalised = path_str.replace("\\", "/")
    parts = normalised.split("/")
    return any(_pattern_matches(normalised, parts, pattern) for pattern in patterns)


def _pattern_matches(path: str, parts: list[str], pattern: str) -> bool:
    """Match ``path`` against one gitignore-style ``pattern``."""
    if pattern.endswith("/**"):
        prefix = pattern[: -len("/**")]
        return path == prefix or path.startswith(prefix + "/")
    if "/" not in pattern:
        return any(fnmatch.fnmatchcase(part, pattern) for part in parts)
    return fnmatch.fnmatchcase(path, pattern)


def discover_content(
    config: BartlebyConfig, content_dir: Path
) -> tuple[list[Page], list[ColocatedAsset]]:
    """Walk ``content_dir`` and produce Page and ColocatedAsset objects.

    :param config: Parsed Bartleby config (used for content type paths,
        taxonomies, and exclude patterns).
    :param content_dir: The site's ``content/`` directory.
    :returns: ``(pages, assets)`` — every discovered markdown file becomes a
        :class:`Page`; every other file becomes a :class:`ColocatedAsset`.
    """
    pages: list[Page] = []
    assets: list[ColocatedAsset] = []
    taxonomy_names = set(config.taxonomies.keys())

    for abs_path in sorted(content_dir.rglob("*")):
        if not abs_path.is_file():
            continue
        relative = abs_path.relative_to(content_dir)
        rel_posix = relative.as_posix()
        if should_exclude(rel_posix, config.exclude_patterns):
            continue

        if abs_path.suffix == ".md":
            pages.append(
                _build_page(
                    abs_path=abs_path,
                    relative=relative,
                    config=config,
                    taxonomy_names=taxonomy_names,
                )
            )
        else:
            assets.append(
                ColocatedAsset(
                    source_path=relative,
                    abs_source_path=abs_path,
                    associated_page_source=None,
                )
            )

    return pages, assets


def _build_page(
    *,
    abs_path: Path,
    relative: Path,
    config: BartlebyConfig,
    taxonomy_names: set[str],
) -> Page:
    """Parse one markdown file into a :class:`Page` with front matter applied."""
    raw_text = abs_path.read_text(encoding="utf-8")
    metadata, body = parse_front_matter(raw_text)

    content_type_name = _content_type_for(relative.as_posix(), config)
    title = str(metadata.get("title", abs_path.stem))
    taxonomy_values, custom_metadata = _split_metadata(metadata, taxonomy_names)

    return Page(
        source_path=relative,
        abs_source_path=abs_path,
        title=title,
        description=_optional_str(metadata.get("description")),
        date=_coerce_date(metadata.get("date")),
        draft=bool(metadata.get("draft", False)),
        template_override=_optional_str(metadata.get("template")),
        url_override=_optional_str(metadata.get("url")),
        url_base_override=_optional_str(metadata.get("url_base")),
        author_keys=_coerce_str_list(metadata.get("authors")),
        taxonomy_values=taxonomy_values,
        custom_metadata=custom_metadata,
        raw_content=body,
        content_type_name=content_type_name,
    )


def _content_type_for(rel_posix: str, config: BartlebyConfig) -> str | None:
    """Return the content type name whose ``path`` prefixes ``rel_posix``."""
    for type_name, content_type in config.content_types.items():
        prefix = content_type.path.rstrip("/") + "/"
        if rel_posix.startswith(prefix):
            return type_name
    return None


def _split_metadata(
    metadata: dict[str, Any], taxonomy_names: set[str]
) -> tuple[dict[str, list[str]], dict[str, PageMetadataValue]]:
    """Separate metadata into taxonomy values vs. custom field map."""
    taxonomy_values: dict[str, list[str]] = {}
    custom: dict[str, PageMetadataValue] = {}
    for key, value in metadata.items():
        if key in _STANDARD_FRONT_MATTER_FIELDS:
            continue
        if key in taxonomy_names:
            taxonomy_values[key] = _coerce_str_list(value)
        else:
            coerced = _coerce_custom_metadata(value)
            if coerced is not None:
                custom[key] = coerced
    return taxonomy_values, custom


def _coerce_str_list(value: Any) -> list[str]:
    """Coerce a YAML value into ``list[str]``; missing/non-list values yield ``[]``."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _coerce_date(value: Any) -> datetime.date | None:
    """Coerce a YAML scalar into a :class:`datetime.date` when possible."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        return datetime.date.fromisoformat(value)
    return None


def _coerce_custom_metadata(value: Any) -> PageMetadataValue | None:
    """Narrow an arbitrary YAML value into the :data:`PageMetadataValue` union."""
    if isinstance(value, bool | int | str):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, list):
        return [str(item) for item in value]
    return None


def _optional_str(value: Any) -> str | None:
    """Return ``str(value)`` when ``value`` is not ``None``, else ``None``."""
    return None if value is None else str(value)
