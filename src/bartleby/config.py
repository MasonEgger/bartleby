# ABOUTME: Configuration loading and validation for bartleby.yml.
# Provides typed dataclass representation and structured validation errors.

"""Configuration loading for ``bartleby.yml``.

Error-message contract: every :class:`ConfigError` raised while loading a file
renders as ``<config file>: <key path>: <message> (fix: <hint>)`` (see
:func:`bartleby.errors.format_error`). The file is attached by :func:`load_config`,
so a raise site only supplies the key path, the message, and a concrete hint. A key
path names the offending field (``site.url``, ``content_types.blog.metadata.rating.type``)
and is absent only when the whole file is at fault (empty, invalid YAML, not a mapping).
Unknown top-level keys, unknown metadata field types, and removed ``theme`` keys
all follow this shape, so tests assert on substrings of it, not exact strings.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml

from bartleby.errors import format_error
from bartleby.theme_loader import DEFAULT_THEME_NAME, THEME_FEATURES

if TYPE_CHECKING:
    from pathlib import Path


_RENAMED_FEATURES: dict[str, str] = {
    "navigation.tabs": "nav.tabs",
    "navigation.sections": "nav.sidebar",
    "navigation.indexes": "nav.section-index",
    "navigation.top": "nav.back-to-top",
}
"""mkdocs-material feature names that have a native Bartleby replacement."""

_TOP_LEVEL_KEYS: tuple[str, ...] = (
    "site",
    "nav",
    "theme",
    "authors_file",
    "content_types",
    "taxonomies",
    "exclude_patterns",
    "markdown_extensions",
    "plugins",
    "extra_css",
    "extra_js",
    "ai",
    "dev_server",
    "output_dir",
)
"""Every key ``bartleby.yml`` accepts at the top level."""

METADATA_FIELD_TYPES: tuple[str, ...] = ("string", "integer", "boolean", "date", "list")
"""The ``type`` values a content type's ``metadata`` schema accepts."""


class ConfigError(Exception):
    """Raised when ``bartleby.yml`` is malformed or fails validation.

    ``str(error)`` is ``<source>: <key_path>: <message> (fix: <hint>)`` with absent
    parts dropped; :func:`load_config` fills in ``source`` as the error leaves it.

    :ivar message: The validation message describing the problem.
    :ivar key_path: The dotted key path identifying the offending field,
        or ``None`` when the problem is not tied to a specific field.
    :ivar hint: A concrete fix, or ``None`` when there is nothing more to say.
    :ivar source: The config file the error came from, once known.
    """

    def __init__(
        self,
        message: str,
        key_path: str | None = None,
        *,
        hint: str | None = None,
        source: Path | None = None,
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


def _expected(key_path: str, kind: str, example: str) -> ConfigError:
    """Build the error for a value of the wrong shape (``mapping`` or ``list``)."""
    return ConfigError(f"must be a {kind}", key_path=key_path, hint=f"write {example}")


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
    """Definition of one content type (e.g. ``blog``, ``tutorials``)."""

    name: str
    path: str
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
    """Root configuration object representing a fully-parsed ``bartleby.yml``."""

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


def load_config(config_path: Path) -> BartlebyConfig:
    """Load and validate a ``bartleby.yml`` configuration file.

    :param config_path: Path to the ``bartleby.yml`` file.
    :returns: A fully parsed and validated :class:`BartlebyConfig`.
    :raises FileNotFoundError: If ``config_path`` does not exist.
    :raises ConfigError: If the file is empty, malformed, or fails validation.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        return _load_config_text(config_path)
    except ConfigError as exc:
        exc.source = config_path
        raise


def _load_config_text(config_path: Path) -> BartlebyConfig:
    """Parse and validate the file at ``config_path``; the caller attaches the source."""
    raw_text = config_path.read_text(encoding="utf-8")
    try:
        parsed: Any = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ConfigError(
            f"invalid YAML{_yaml_location(exc)}",
            hint="fix the syntax at that line (check indentation, quotes, and brackets)",
        ) from exc

    if parsed is None:
        raise ConfigError(
            "config file is empty",
            hint="add a `site:` section with `title:` and `url:`",
        )
    if not isinstance(parsed, dict):
        raise ConfigError(
            "config root must be a YAML mapping",
            hint="start with top-level keys such as `site:`, one per line",
        )

    _reject_unknown_top_level_keys(parsed)
    config = _parse_config(parsed, config_path.parent)
    _validate_config(config)
    return config


def _yaml_location(exc: yaml.YAMLError) -> str:
    """Return `` at line N`` for a YAML syntax error that carries a position."""
    mark = getattr(exc, "problem_mark", None)
    return f" at line {mark.line + 1}" if mark is not None else ""


def _reject_unknown_top_level_keys(parsed: dict[str, Any]) -> None:
    """Raise for the first top-level key ``bartleby.yml`` does not define."""
    for key in parsed:
        if key in _TOP_LEVEL_KEYS:
            continue
        close = difflib.get_close_matches(str(key), _TOP_LEVEL_KEYS, n=1)
        hint = (
            f"did you mean {close[0]!r}?"
            if close
            else f"valid top-level keys are {', '.join(_TOP_LEVEL_KEYS)}"
        )
        raise ConfigError("unknown top-level key", key_path=str(key), hint=hint)


def _parse_config(raw: dict[str, Any], config_dir: Path) -> BartlebyConfig:
    """Convert a raw YAML mapping into a :class:`BartlebyConfig` with defaults."""
    nav_raw = raw.get("nav")
    nav: list[dict[str, object]] | None = nav_raw if isinstance(nav_raw, list) else None

    exclude_raw = raw.get("exclude_patterns")
    exclude_patterns: list[str] = (
        [str(pattern) for pattern in exclude_raw]
        if isinstance(exclude_raw, list)
        else list(DEFAULT_EXCLUDE_PATTERNS)
    )

    extensions_raw = raw.get("markdown_extensions")
    markdown_extensions: list[dict[str, object] | str] = (
        list(extensions_raw) if isinstance(extensions_raw, list) else []
    )

    plugins_raw = raw.get("plugins")
    plugins, disabled_plugins = _parse_plugins(plugins_raw)

    extra_css_raw = raw.get("extra_css")
    extra_css: list[str] = (
        [str(path) for path in extra_css_raw] if isinstance(extra_css_raw, list) else []
    )

    extra_js_raw = raw.get("extra_js")
    extra_js: list[str] = (
        [str(path) for path in extra_js_raw] if isinstance(extra_js_raw, list) else []
    )

    return BartlebyConfig(
        site=_parse_site(raw.get("site")),
        nav=nav,
        theme=_parse_theme(raw.get("theme")),
        authors_file=str(raw.get("authors_file", ".authors.yml")),
        content_types=_parse_content_types(raw.get("content_types")),
        taxonomies=_parse_taxonomies(raw.get("taxonomies")),
        exclude_patterns=exclude_patterns,
        markdown_extensions=markdown_extensions,
        plugins=plugins,
        disabled_plugins=disabled_plugins,
        extra_css=extra_css,
        extra_js=extra_js,
        ai=_parse_ai(raw.get("ai")),
        dev_server=_parse_dev_server(raw.get("dev_server")),
        config_dir=config_dir,
        output_dir=str(raw.get("output_dir", "site")),
    )


def _parse_plugins(raw: Any) -> tuple[list[str], set[str]]:
    """Parse the ``plugins`` section into enabled names and disabled names.

    The section accepts two forms (spec.md "plugins"):

    - a **list** of feature-module names to enable (e.g. ``[search, rss]``);
    - a **mapping** of ``<name>: bool`` where ``false`` disables an
      auto-registered plugin without uninstalling it.

    :param raw: The raw ``plugins`` value from the parsed YAML.
    :returns: A ``(enabled, disabled)`` tuple. ``enabled`` lists names mapped
        to a truthy value (or every item of the list form); ``disabled`` holds
        names mapped to ``false``.
    """
    if isinstance(raw, dict):
        enabled = [str(name) for name, value in raw.items() if value]
        disabled = {str(name) for name, value in raw.items() if not value}
        return enabled, disabled
    if isinstance(raw, list):
        return [str(name) for name in raw], set()
    return [], set()


def _parse_site(raw: Any) -> SiteConfig:
    """Parse the ``site`` section, raising :class:`ConfigError` if required fields are missing."""
    if not isinstance(raw, dict):
        raise ConfigError(
            "site section is required",
            key_path="site",
            hint="add `site:` with `title:` and `url:` lines under it",
        )
    for required in ("title", "url"):
        if required not in raw:
            raise ConfigError(
                "required field is missing",
                key_path=f"site.{required}",
                hint=f"add a `{required}:` line under `site:`",
            )
    return SiteConfig(
        title=str(raw["title"]),
        url=str(raw["url"]),
        description=str(raw.get("description", "")),
        author=str(raw.get("author", "")),
        default_image=_optional_str(raw.get("default_image")),
        twitter=_optional_str(raw.get("twitter")),
        feed=_parse_feed(raw.get("feed")),
    )


def _parse_feed(raw: Any) -> FeedConfig:
    """Parse the ``site.feed`` section, returning enabled defaults when absent."""
    if raw is None:
        return FeedConfig()
    if not isinstance(raw, dict):
        raise _expected("site.feed", "mapping", "`feed:` followed by indented `key: value` lines")
    formats_raw = raw.get("formats", ["rss", "atom"])
    if not isinstance(formats_raw, list):
        raise _expected("site.feed.formats", "list", "`formats: [rss, atom]`")
    include_raw = raw.get("include", [])
    if not isinstance(include_raw, list):
        raise _expected("site.feed.include", "list", "`include: [blog]`")
    return FeedConfig(
        enabled=bool(raw.get("enabled", True)),
        formats=[str(fmt) for fmt in formats_raw],
        include=[str(name) for name in include_raw],
        limit=int(raw.get("limit", 50)),
        title=_optional_str(raw.get("title")),
    )


def _parse_theme(raw: Any) -> ThemeConfig:
    """Parse the ``theme`` section, returning defaults when absent."""
    if raw is None:
        return ThemeConfig()
    if not isinstance(raw, dict):
        raise _expected(
            "theme", "mapping", "`theme:` followed by indented keys such as `name: scrivener`"
        )
    _reject_removed_theme_keys(raw)
    sources = [key for key in ("name", "path", "package") if raw.get(key) is not None]
    if len(sources) > 1:
        raise ConfigError(
            f"set only one of name, path, or package (found {' and '.join(sources)})",
            key_path="theme",
            hint=f"delete all but one of {', '.join(sources)} under `theme:`",
        )
    name = _optional_str(raw.get("name"))
    return ThemeConfig(
        name=DEFAULT_THEME_NAME if name is None else name,
        path=_optional_str(raw.get("path")),
        package=_optional_str(raw.get("package")),
        features=_parse_theme_features(raw.get("features")),
        tokens=_parse_theme_tokens(raw.get("tokens")),
        color_mode=_parse_color_mode(raw.get("color_mode")),
        icon_packs={str(key): bool(value) for key, value in (raw.get("icon_packs") or {}).items()},
        logo=_site_url(raw.get("logo")),
        favicon=_site_url(raw.get("favicon")),
    )


def _parse_color_mode(raw: Any) -> dict[str, str]:
    """Parse ``theme.color_mode``, which carries only ``default`` (``light`` or ``dark``).

    The header toggle is the ``color-mode.toggle`` feature, so the old
    ``color_mode.toggle`` switch is rejected with a pointer to ``theme.features``.
    """
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise _expected("theme.color_mode", "mapping", "`color_mode:` followed by `default: dark`")
    if "toggle" in raw:
        raise ConfigError(
            "'toggle' is not a color_mode key",
            key_path="theme.color_mode.toggle",
            hint="enable the toggle with the `color-mode.toggle` feature under theme.features",
        )
    return {str(key): str(value) for key, value in raw.items()}


def _reject_removed_theme_keys(raw: dict[str, Any]) -> None:
    """Raise a migration hint for the mkdocs-material ``palette`` and ``font`` keys."""
    for key, example in (("palette", "color.primary"), ("font", "font.text")):
        if key in raw:
            raise ConfigError(
                f"{key!r} is not a Bartleby theme key",
                key_path=f"theme.{key}",
                hint=f"set design tokens under theme.tokens instead (for example {example})",
            )


def _parse_theme_features(raw: Any) -> list[str]:
    """Parse ``theme.features``, rejecting names outside the native vocabulary."""
    features = [str(feature) for feature in (raw or [])]
    for feature_name in features:
        if feature_name in THEME_FEATURES:
            continue
        replacement = _RENAMED_FEATURES.get(feature_name)
        if replacement is not None:
            raise ConfigError(
                f"unknown feature {feature_name!r}",
                key_path="theme.features",
                hint=f"the native name is {replacement!r}",
            )
        native = ", ".join(sorted(THEME_FEATURES))
        raise ConfigError(
            f"unknown feature {feature_name!r}: not a Bartleby feature",
            key_path="theme.features",
            hint=f"use one of the native features: {native}",
        )
    return features


def _parse_theme_tokens(raw: Any) -> dict[str, str]:
    """Parse ``theme.tokens`` as a flat map of dotted token names to strings."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise _expected(
            "theme.tokens",
            "mapping",
            '`tokens:` followed by lines like `color.primary: "#336699"`',
        )
    tokens: dict[str, str] = {}
    for token_name, value in raw.items():
        if not isinstance(value, str):
            raise ConfigError(
                f"token value must be a string, got {type(value).__name__}",
                key_path=f"theme.tokens.{token_name}",
                hint=f'quote the value, for example `{token_name}: "{value}"`',
            )
        tokens[str(token_name)] = value
    return tokens


def _parse_content_types(raw: Any) -> dict[str, ContentTypeConfig]:
    """Parse the ``content_types`` section into a name-keyed mapping."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise _expected(
            "content_types", "mapping", "`content_types:` followed by one named entry per type"
        )
    result: dict[str, ContentTypeConfig] = {}
    for type_name, definition in raw.items():
        result[str(type_name)] = _parse_content_type(str(type_name), definition)
    return result


def _parse_content_type(type_name: str, raw: Any) -> ContentTypeConfig:
    """Parse a single content type definition."""
    key_path = f"content_types.{type_name}"
    if not isinstance(raw, dict):
        raise _expected(
            key_path, "mapping", "the type name followed by indented keys such as `path: blog`"
        )
    if "path" not in raw:
        raise ConfigError(
            "required field is missing",
            key_path=f"{key_path}.path",
            hint=f"add `path:` under `{type_name}:`, the directory under content/ for this type",
        )
    return ContentTypeConfig(
        name=type_name,
        path=str(raw["path"]),
        url_base=_optional_str(raw.get("url_base")),
        url_format=_optional_str(raw.get("url_format")),
        pagination=_parse_pagination(raw.get("pagination"), key_path),
        taxonomies=[str(taxonomy) for taxonomy in (raw.get("taxonomies") or [])],
        feeds=[str(feed) for feed in (raw.get("feeds") or [])],
        readtime=bool(raw.get("readtime", False)),
        excerpt_separator=_optional_str(raw.get("excerpt_separator")),
        metadata=_parse_metadata_schema(raw.get("metadata"), key_path),
    )


def _parse_pagination(raw: Any, parent_key: str) -> PaginationConfig:
    """Parse a content type's ``pagination`` block, defaulting to disabled."""
    if raw is None:
        return PaginationConfig()
    if not isinstance(raw, dict):
        raise _expected(
            f"{parent_key}.pagination", "mapping", "`pagination:` followed by `enabled: true`"
        )
    return PaginationConfig(
        enabled=bool(raw.get("enabled", False)),
        per_page=int(raw.get("per_page", 10)),
        url_format=str(raw.get("url_format", "page/{page}")),
    )


def _parse_metadata_schema(raw: Any, parent_key: str) -> dict[str, MetadataFieldSchema]:
    """Parse a content type's ``metadata`` schema block."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise _expected(
            f"{parent_key}.metadata", "mapping", "`metadata:` followed by one entry per field"
        )
    result: dict[str, MetadataFieldSchema] = {}
    for field_name, definition in raw.items():
        field_key = f"{parent_key}.metadata.{field_name}"
        if not isinstance(definition, dict):
            raise _expected(field_key, "mapping", "the field name followed by `type: string`")
        valid_types = ", ".join(METADATA_FIELD_TYPES)
        if "type" not in definition:
            raise ConfigError(
                "required field is missing",
                key_path=f"{field_key}.type",
                hint=f"add `type:` under `{field_name}:`, one of {valid_types}",
            )
        field_type = str(definition["type"])
        if field_type not in METADATA_FIELD_TYPES:
            raise ConfigError(
                f"unknown field type {field_type!r}",
                key_path=f"{field_key}.type",
                hint=f"use one of {valid_types}",
            )
        choices_raw = definition.get("choices")
        if choices_raw is not None and not isinstance(choices_raw, list):
            raise _expected(f"{field_key}.choices", "list", "`choices: [easy, hard]`")
        choices = [str(choice) for choice in choices_raw] if choices_raw is not None else None
        result[str(field_name)] = MetadataFieldSchema(
            field_type=field_type,
            required=bool(definition.get("required", False)),
            choices=choices,
        )
    return result


def _parse_taxonomies(raw: Any) -> dict[str, TaxonomyConfig]:
    """Parse the ``taxonomies`` section into a name-keyed mapping."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise _expected(
            "taxonomies", "mapping", "`taxonomies:` followed by one named entry per taxonomy"
        )
    result: dict[str, TaxonomyConfig] = {}
    for taxonomy_name, definition in raw.items():
        key_path = f"taxonomies.{taxonomy_name}"
        if not isinstance(definition, dict):
            raise _expected(
                key_path, "mapping", 'the taxonomy name followed by `slug_format: "{slug}"`'
            )
        result[str(taxonomy_name)] = TaxonomyConfig(
            name=str(taxonomy_name),
            slug_format=str(definition.get("slug_format", "{slug}")),
        )
    return result


def _parse_ai(raw: Any) -> AIConfig:
    """Parse the ``ai`` section, returning defaults when absent."""
    if raw is None:
        return AIConfig()
    if not isinstance(raw, dict):
        raise _expected(
            "ai", "mapping", "`ai:` followed by indented keys such as `llms_txt: true`"
        )
    robots_raw = raw.get("robots") or {}
    if not isinstance(robots_raw, dict):
        raise _expected(
            "ai.robots", "mapping", "`robots:` followed by lines like `disallow: [GPTBot]`"
        )
    robots: dict[str, list[str]] = {
        str(directive): [str(crawler) for crawler in (crawlers or [])]
        for directive, crawlers in robots_raw.items()
    }
    return AIConfig(
        llms_txt=bool(raw.get("llms_txt", True)),
        llms_full_txt=bool(raw.get("llms_full_txt", True)),
        markdown_variants=bool(raw.get("markdown_variants", True)),
        agent_surface=bool(raw.get("agent_surface", True)),
        robots=robots,
        skills=_parse_skills(raw.get("skills")),
        agent_context=_parse_agent_context(raw.get("agent_context")),
    )


def _parse_skills(raw: Any) -> SkillsConfig:
    """Parse the ``ai.skills`` section, rejecting the reserved ``analyze_content`` key."""
    if raw is None:
        return SkillsConfig()
    if not isinstance(raw, dict):
        raise _expected("ai.skills", "mapping", "`skills:` followed by indented keys")
    if "analyze_content" in raw:
        raise ConfigError(
            "ai.skills.analyze_content is not yet supported (content analysis is "
            "deferred from v1)",
            key_path="ai.skills.analyze_content",
            hint="delete the key; describe voice and audience under ai.agent_context instead",
        )
    if "include_examples" in raw:
        raise ConfigError(
            "ai.skills.include_examples is not yet supported (generated skills carry "
            "no example pages)",
            key_path="ai.skills.include_examples",
            hint="delete the key; put example guidance in ai.skills.style_guide instead",
        )
    return SkillsConfig(
        output_dir=str(raw.get("output_dir", ".claude/skills")),
        style_guide=_optional_str(raw.get("style_guide")),
        regenerate_on_build=bool(raw.get("regenerate_on_build", False)),
    )


def _parse_agent_context(raw: Any) -> AgentContext:
    """Parse the ``ai.agent_context`` section (voice/audience/constraints)."""
    if raw is None:
        return AgentContext()
    if not isinstance(raw, dict):
        raise _expected(
            "ai.agent_context", "mapping", "`agent_context:` followed by `voice:` and `audience:`"
        )
    constraints_raw = raw.get("constraints") or []
    if not isinstance(constraints_raw, list):
        raise _expected("ai.agent_context.constraints", "list", "one `- constraint` line per rule")
    return AgentContext(
        voice=_optional_str(raw.get("voice")),
        audience=_optional_str(raw.get("audience")),
        constraints=[str(item) for item in constraints_raw],
    )


def _parse_dev_server(raw: Any) -> DevServerConfig:
    """Parse the ``dev_server`` section, returning defaults when absent."""
    if raw is None:
        return DevServerConfig()
    if not isinstance(raw, dict):
        raise _expected("dev_server", "mapping", "`dev_server:` followed by `host:` and `port:`")
    return DevServerConfig(
        host=str(raw.get("host", "127.0.0.1")),
        port=int(raw.get("port", 8000)),
    )


def _validate_config(config: BartlebyConfig) -> None:
    """Verify cross-references and constraints on a parsed config.

    :param config: The parsed config to validate.
    :raises ConfigError: If any content type references an undefined taxonomy.
    """
    defined_taxonomies = set(config.taxonomies.keys())
    for content_type_name, content_type in config.content_types.items():
        for taxonomy_name in content_type.taxonomies:
            if taxonomy_name not in defined_taxonomies:
                raise ConfigError(
                    f"references undefined taxonomy {taxonomy_name!r}",
                    key_path=f"content_types.{content_type_name}.taxonomies",
                    hint=(
                        f"declare it under `taxonomies:` (for example `{taxonomy_name}:`), "
                        "or remove it from this list"
                    ),
                )

    for include_name in config.site.feed.include:
        included_type = config.content_types.get(include_name)
        if included_type is None:
            raise ConfigError(
                f"references undefined content type {include_name!r}",
                key_path="site.feed.include",
                hint=f"use a name from `content_types:` ({', '.join(config.content_types)})",
            )
        if not included_type.feeds:
            raise ConfigError(
                f"content type {include_name!r} has no feeds of its own to aggregate",
                key_path="site.feed.include",
                hint=f"add `feeds: [rss]` under content_types.{include_name}, or drop it here",
            )


def _site_url(value: Any) -> str | None:
    """Normalize a ``static/``-relative asset path to a root-relative URL.

    ``None`` stays ``None``; ``http(s)://`` URLs and paths starting with ``/`` pass through.
    """
    if value is None:
        return None
    text = str(value)
    if text.startswith(("http://", "https://", "/")):
        return text
    return f"/{text}"


def _optional_str(value: Any) -> str | None:
    """Return ``str(value)`` when ``value`` is not ``None``, else ``None``."""
    return None if value is None else str(value)
