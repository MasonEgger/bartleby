# ABOUTME: The typed shape of bartleby.yml: dataclasses, constants, ConfigError, path helpers.
# ABOUTME: A leaf that imports nothing from the package but errors and theme_loader.

"""The shapes ``bartleby.yml`` loads into, and the pieces every config module shares.

:mod:`bartleby.config` (the loader and validator), :mod:`bartleby.config_schema`
(every key as data), and :mod:`bartleby.config_edit` (the writer) all build on this
module without importing each other: the schema reads the dataclass defaults and the
closed sets here, and the loader re-exports every public name so
``from bartleby.config import BartlebyConfig`` stays the import path callers use.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml

from bartleby.errors import format_error
from bartleby.theme_loader import DEFAULT_THEME_NAME

if TYPE_CHECKING:
    from pathlib import Path


METADATA_FIELD_TYPES: tuple[str, ...] = ("string", "integer", "boolean", "date", "list")
"""The ``type`` values a content type's ``metadata`` schema accepts."""

FEED_FORMATS: tuple[str, ...] = ("rss", "atom")
"""The feed formats ``site.feed.formats`` and a content type's ``feeds`` accept."""

COLOR_MODES: tuple[str, ...] = ("light", "dark")
"""The values ``theme.color_mode.default`` accepts."""

DOTTED_KEY_SECTIONS: tuple[str, ...] = ("theme.tokens",)
"""Mappings whose keys contain dots (``color.primary``), so a path under one is not split."""

MARKWRIGHT_KEY = "markwright"
"""The top-level key that carries markwright's own config table."""

BUILD_INPUT_DIRS: tuple[str, ...] = (
    "content",
    "static",
    "templates",
    "overrides",
    "hooks",
    "data",
    "shortcodes",
    "partials",
)
"""The project directories a build reads, which ``output_dir`` may not overlap."""


class ConfigError(Exception):
    """Raised when ``bartleby.yml`` is malformed or fails validation.

    ``str(error)`` is ``<source>: <key_path>: <message> (fix: <hint>)`` with absent
    parts dropped; :func:`load_config` fills in ``source`` as the error leaves it.

    :ivar message: The validation message describing the problem.
    :ivar key_path: The dotted key path identifying the offending field,
        or ``None`` when the problem is not tied to a specific field.
    :ivar hint: A concrete fix, or ``None`` when there is nothing more to say.
    :ivar source: The config file, or ``--set`` for a command-line override, the error
        came from, once known.
    """

    def __init__(
        self,
        message: str,
        key_path: str | None = None,
        *,
        hint: str | None = None,
        source: Path | str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.key_path = key_path
        self.hint = hint
        self.source = source

    def __str__(self) -> str:
        return format_error(
            self.message, source=self.source, key_path=self.key_path, hint=self.hint
        )


@dataclass(slots=True)
class FeedConfig:
    """Site-wide aggregate feed settings loaded from ``site.feed``.

    The aggregate is the homepage firehose: one feed merging items across
    content types. See spec.md "Feed Generation > Site-wide aggregate feed".

    :ivar enabled: Whether the aggregate feed is generated at all.
    :ivar formats: Which feed formats to emit at the site root (``rss``, ``atom``).
    :ivar include: Content types to aggregate. Empty means every content type
        that has its own ``feeds`` enabled; a non-empty list restricts to exactly
        those types.
    :ivar limit: Maximum number of items in the merged feed.
    :ivar title: Channel title override; ``None`` falls back to ``site.title``.
    """

    enabled: bool = True
    formats: list[str] = field(default_factory=lambda: ["rss", "atom"])
    include: list[str] = field(default_factory=list)
    limit: int = 50
    title: str | None = None


@dataclass(slots=True)
class SiteConfig:
    """Global site metadata loaded from the ``site`` section."""

    title: str
    url: str
    description: str = ""
    author: str = ""
    default_image: str | None = None
    twitter: str | None = None
    language: str = "en"
    feed: FeedConfig = field(default_factory=FeedConfig)


@dataclass(slots=True)
class PaginationConfig:
    """Pagination configuration for a content type's listing pages."""

    enabled: bool = False
    per_page: int = 10
    url_format: str = "page/{page}"


@dataclass(slots=True)
class MetadataFieldSchema:
    """Schema describing a single metadata field declared on a content type."""

    field_type: str
    required: bool = False
    choices: list[str] | None = None


@dataclass(slots=True)
class ContentTypeConfig:
    """Definition of one content type (e.g. ``blog``, ``tutorials``).

    :ivar enabled: Whether the build produces this type's outputs. A disabled type
        stays parsed and validated, but its content files, listing pages, and feeds
        are skipped, and it drops out of the aggregate feed. ``bartleby disable``
        sets this to ``False`` instead of deleting the block.
    """

    name: str
    path: str
    enabled: bool = True
    url_base: str | None = None
    url_format: str | None = None
    pagination: PaginationConfig = field(default_factory=PaginationConfig)
    taxonomies: list[str] = field(default_factory=list)
    feeds: list[str] = field(default_factory=list)
    readtime: bool = False
    excerpt_separator: str | None = None
    metadata: dict[str, MetadataFieldSchema] = field(default_factory=dict)


@dataclass(slots=True)
class TaxonomyConfig:
    """Definition of one site-wide taxonomy (e.g. ``tags``, ``categories``)."""

    name: str
    slug_format: str


@dataclass(slots=True)
class ThemeConfig:
    """Theme selection, features, design tokens, and asset paths.

    At most one of ``name``, ``path``, and ``package`` is set in
    ``bartleby.yml``; when none is, ``name`` is the bundled default theme.

    :ivar name: A bundled theme name.
    :ivar path: A theme directory, relative to the project or absolute.
    :ivar package: A ``bartleby.themes`` entry-point name.
    :ivar features: Enabled feature names, each a member of
        :data:`bartleby.theme_loader.THEME_FEATURES`.
    :ivar tokens: Design-token overrides, a flat map of dotted token names
        (``color.primary``, ``font.text``, ``radius``) to CSS values.
    :ivar color_mode: Light/dark settings; only ``default`` (``light`` or ``dark``) is read.
    :ivar icon_packs: Icon pack name to enabled flag.
    :ivar logo: The site logo as a URL: a path relative to ``static/`` becomes
        root-relative (``img/logo.svg`` is ``/img/logo.svg``); an ``http(s)`` URL or a
        rooted path is kept as written.
    :ivar favicon: The site favicon, normalized the same way as ``logo``.
    """

    name: str = DEFAULT_THEME_NAME
    path: str | None = None
    package: str | None = None
    features: list[str] = field(default_factory=list)
    tokens: dict[str, str] = field(default_factory=dict)
    color_mode: dict[str, str] = field(default_factory=dict)
    icon_packs: dict[str, bool] = field(default_factory=dict)
    logo: str | None = None
    favicon: str | None = None


@dataclass(slots=True)
class SkillsConfig:
    """Settings for deterministic agent-skill generation (``ai.skills``)."""

    output_dir: str = ".claude/skills"
    style_guide: str | None = None
    regenerate_on_build: bool = False


@dataclass(slots=True)
class AgentContext:
    """Explicit voice/audience/constraint declarations for generated skills.

    These are included verbatim in the write/review skills when set; they are
    the only source of voice/style information in v1 (content analysis is
    deferred).
    """

    voice: str | None = None
    audience: str | None = None
    constraints: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AIConfig:
    """AI and agent integration settings (LLM output, robots directives)."""

    llms_txt: bool = True
    llms_full_txt: bool = True
    markdown_variants: bool = True
    agent_surface: bool = True
    robots: dict[str, list[str]] = field(default_factory=dict)
    skills: SkillsConfig = field(default_factory=SkillsConfig)
    agent_context: AgentContext = field(default_factory=AgentContext)


@dataclass(slots=True)
class DevServerConfig:
    """Development server bind host and port."""

    host: str = "127.0.0.1"
    port: int = 8000


DEFAULT_EXCLUDE_PATTERNS: list[str] = ["_drafts/**", "_*.md", ".git/**"]


@dataclass(slots=True)
class BartlebyConfig:
    """Root configuration object representing a fully-parsed ``bartleby.yml``.

    :ivar markwright: The ``markwright:`` section exactly as written. It has the shape of a
        ``markwright.toml``; :func:`markwright_config` has already validated it through
        markwright's own config API, and the renderer resolves it again from here.
    """

    site: SiteConfig
    nav: list[dict[str, object]] | None
    theme: ThemeConfig
    authors_file: str
    content_types: dict[str, ContentTypeConfig]
    taxonomies: dict[str, TaxonomyConfig]
    exclude_patterns: list[str]
    markdown_extensions: list[dict[str, object] | str]
    plugins: list[str]
    extra_css: list[str]
    extra_js: list[str]
    ai: AIConfig
    dev_server: DevServerConfig
    config_dir: Path
    output_dir: str = "site"
    disabled_plugins: set[str] = field(default_factory=set)
    markwright: dict[str, object] = field(default_factory=dict)

    def enabled_content_types(self) -> dict[str, ContentTypeConfig]:
        """The content types the build produces output for, in config order."""
        return {name: kind for name, kind in self.content_types.items() if kind.enabled}


OVERRIDE_SOURCE = "--set"
"""The error source label for a value that came from a ``--set`` override."""


SOURCE_DEFAULT = "default"
"""The provenance label for a value no file key or override supplied; set by
:func:`bartleby.config.resolve_with_sources`."""

SOURCE_FILE = "file"
"""The provenance label for a value read from ``bartleby.yml``."""


def split_path(dotted_path: str) -> list[str]:
    """Split a dotted key path into its segments.

    A path under a :data:`DOTTED_KEY_SECTIONS` mapping keeps its tail as one segment:
    ``theme.tokens.color.primary`` is ``["theme", "tokens", "color.primary"]``.

    :param dotted_path: A path such as ``site.feed.limit``.
    :returns: The segments, in order.
    :raises ConfigError: If the path is empty or has an empty segment.
    """
    segments = dotted_path.split(".")
    for section in DOTTED_KEY_SECTIONS:
        prefix = section.split(".")
        if segments[: len(prefix)] == prefix and len(segments) > len(prefix):
            segments = [*prefix, ".".join(segments[len(prefix) :])]
    if not all(segments):
        raise ConfigError(
            f"invalid key path {dotted_path!r}",
            key_path=dotted_path,
            hint="use dotted names such as site.title",
        )
    return segments


def existing_prefix[Mapping: dict[str, Any]](
    root: Mapping, segments: list[str]
) -> tuple[Mapping, int]:
    """Walk the parent segments of a dotted path that already hold mappings.

    Shared by ``--set`` overrides (plain dicts) and the comment-preserving writer
    (ruamel maps): the children are expected to be the same mapping type as ``root``.

    :param root: The top-level mapping.
    :param segments: A path from :func:`split_path`.
    :returns: The deepest existing mapping and how many parent segments lead to it.
    :raises ConfigError: If a parent key holds something other than a mapping or null.
    """
    node = root
    for depth, segment in enumerate(segments[:-1], start=1):
        child = node.get(segment)
        if child is None:
            return node, depth - 1
        if not isinstance(child, type(root)):
            walked = ".".join(segments[:depth])
            raise ConfigError(
                f"{walked} is not a mapping, so it cannot hold {segments[depth]!r}",
                key_path=walked,
                hint=f"replace the value of {walked} with a mapping first",
            )
        node = child
    return node, len(segments) - 1


def same_branch(key_path: str | None, override_path: str) -> bool:
    """Whether ``key_path`` equals ``override_path`` or sits under it."""
    if not key_path:
        return False
    return key_path == override_path or key_path.startswith(f"{override_path}.")


def yaml_location(exc: Exception) -> str:
    """Return `` at line N`` for a PyYAML or ruamel error that carries a position.

    :param exc: The YAML error; one without a ``problem_mark`` yields an empty string.
    """
    mark = getattr(exc, "problem_mark", None)
    return f" at line {mark.line + 1}" if mark is not None else ""


class _StrictLoader(yaml.SafeLoader):
    """A SafeLoader that rejects a mapping with two equal keys instead of keeping the last."""

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
        seen: set[str] = set()
        for key_node, _value_node in node.value:
            if not isinstance(key_node, yaml.ScalarNode):
                continue
            key = self.construct_scalar(key_node)
            if key in seen:
                raise ConfigError(
                    f"duplicate key {key!r} at line {key_node.start_mark.line + 1}",
                    hint=f"keep one `{key}:` line; the later one replaces the earlier",
                )
            seen.add(key)
        return super().construct_mapping(node, deep)


def parse_override_value(dotted_path: str, text: str) -> Any:
    """Parse the text of a ``--set`` or ``config set`` value as YAML.

    ``42`` is an int, ``true`` a bool, ``[a, b]`` a list, and empty text null. A date
    or timestamp is carried as its ISO text, since no config key holds a date.

    :param dotted_path: The key the value is for; named in the error.
    :param text: The value as the user typed it.
    :returns: The parsed value.
    :raises ConfigError: If ``text`` is not valid YAML.
    """
    try:
        value = yaml.load(text, Loader=_StrictLoader)
    except yaml.YAMLError as exc:
        raise ConfigError(
            f"value {text!r} is not valid YAML{yaml_location(exc)}",
            key_path=dotted_path,
            hint="wrap the value in quotes, such as '\"Hello: World\"'",
        ) from exc
    return value.isoformat() if isinstance(value, datetime.date) else value
