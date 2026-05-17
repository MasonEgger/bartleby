# ABOUTME: Configuration loading and validation for bartleby.yml.
# Provides typed dataclass representation and structured validation errors.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path


class ConfigError(Exception):
    """Raised when ``bartleby.yml`` is malformed or fails validation.

    :ivar message: The validation message describing the problem.
    :ivar key_path: The dotted key path identifying the offending field,
        or ``None`` when the problem is not tied to a specific field.
    """

    def __init__(self, message: str, key_path: str | None = None) -> None:
        self.message = message
        self.key_path = key_path
        full = f"{key_path}: {message}" if key_path else message
        super().__init__(full)


@dataclass(slots=True)
class SiteConfig:
    """Global site metadata loaded from the ``site`` section."""

    title: str
    url: str
    description: str = ""
    author: str = ""
    default_image: str | None = None
    twitter: str | None = None


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
    """Theme appearance, features, and asset paths."""

    palette: dict[str, str] = field(default_factory=dict)
    color_mode: dict[str, str | bool] = field(default_factory=dict)
    features: list[str] = field(default_factory=list)
    icon_packs: dict[str, bool] = field(default_factory=dict)
    logo: str | None = None
    favicon: str | None = None
    font: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class AIConfig:
    """AI and agent integration settings (LLM output, robots directives)."""

    llms_txt: bool = True
    llms_full_txt: bool = True
    markdown_variants: bool = True
    robots: dict[str, list[str]] = field(default_factory=dict)


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
    nav: list[dict[str, str]] | None
    theme: ThemeConfig
    authors_file: str
    content_types: dict[str, ContentTypeConfig]
    taxonomies: dict[str, TaxonomyConfig]
    exclude_patterns: list[str]
    markdown_extensions: list[dict[str, object] | str]
    plugins: list[str]
    ai: AIConfig
    dev_server: DevServerConfig
    config_dir: Path


def load_config(config_path: Path) -> BartlebyConfig:
    """Load and validate a ``bartleby.yml`` configuration file.

    :param config_path: Path to the ``bartleby.yml`` file.
    :returns: A fully parsed and validated :class:`BartlebyConfig`.
    :raises FileNotFoundError: If ``config_path`` does not exist.
    :raises ConfigError: If the file is empty, malformed, or fails validation.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    raw_text = config_path.read_text(encoding="utf-8")
    parsed: Any = yaml.safe_load(raw_text)

    if parsed is None:
        raise ConfigError("config file is empty")
    if not isinstance(parsed, dict):
        raise ConfigError("config root must be a YAML mapping")

    config = _parse_config(parsed, config_path.parent)
    _validate_config(config)
    return config


def _parse_config(raw: dict[str, Any], config_dir: Path) -> BartlebyConfig:
    """Convert a raw YAML mapping into a :class:`BartlebyConfig` with defaults."""
    nav_raw = raw.get("nav")
    nav: list[dict[str, str]] | None = nav_raw if isinstance(nav_raw, list) else None

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
    plugins: list[str] = (
        [str(name) for name in plugins_raw] if isinstance(plugins_raw, list) else []
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
        ai=_parse_ai(raw.get("ai")),
        dev_server=_parse_dev_server(raw.get("dev_server")),
        config_dir=config_dir,
    )


def _parse_site(raw: Any) -> SiteConfig:
    """Parse the ``site`` section, raising :class:`ConfigError` if required fields are missing."""
    if not isinstance(raw, dict):
        raise ConfigError("site section is required", key_path="site")
    if "title" not in raw:
        raise ConfigError("required field is missing", key_path="site.title")
    if "url" not in raw:
        raise ConfigError("required field is missing", key_path="site.url")
    return SiteConfig(
        title=str(raw["title"]),
        url=str(raw["url"]),
        description=str(raw.get("description", "")),
        author=str(raw.get("author", "")),
        default_image=_optional_str(raw.get("default_image")),
        twitter=_optional_str(raw.get("twitter")),
    )


def _parse_theme(raw: Any) -> ThemeConfig:
    """Parse the ``theme`` section, returning defaults when absent."""
    if raw is None:
        return ThemeConfig()
    if not isinstance(raw, dict):
        raise ConfigError("theme must be a mapping", key_path="theme")
    return ThemeConfig(
        palette={str(key): str(value) for key, value in (raw.get("palette") or {}).items()},
        color_mode=dict(raw.get("color_mode") or {}),
        features=[str(feature) for feature in (raw.get("features") or [])],
        icon_packs={str(key): bool(value) for key, value in (raw.get("icon_packs") or {}).items()},
        logo=_optional_str(raw.get("logo")),
        favicon=_optional_str(raw.get("favicon")),
        font={str(key): str(value) for key, value in (raw.get("font") or {}).items()},
    )


def _parse_content_types(raw: Any) -> dict[str, ContentTypeConfig]:
    """Parse the ``content_types`` section into a name-keyed mapping."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError("content_types must be a mapping", key_path="content_types")
    result: dict[str, ContentTypeConfig] = {}
    for type_name, definition in raw.items():
        result[str(type_name)] = _parse_content_type(str(type_name), definition)
    return result


def _parse_content_type(type_name: str, raw: Any) -> ContentTypeConfig:
    """Parse a single content type definition."""
    key_path = f"content_types.{type_name}"
    if not isinstance(raw, dict):
        raise ConfigError("content type must be a mapping", key_path=key_path)
    if "path" not in raw:
        raise ConfigError("required field is missing", key_path=f"{key_path}.path")
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
        raise ConfigError("pagination must be a mapping", key_path=f"{parent_key}.pagination")
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
        raise ConfigError("metadata must be a mapping", key_path=f"{parent_key}.metadata")
    result: dict[str, MetadataFieldSchema] = {}
    for field_name, definition in raw.items():
        field_key = f"{parent_key}.metadata.{field_name}"
        if not isinstance(definition, dict):
            raise ConfigError("metadata field must be a mapping", key_path=field_key)
        if "type" not in definition:
            raise ConfigError("required field is missing", key_path=f"{field_key}.type")
        choices_raw = definition.get("choices")
        choices = (
            [str(choice) for choice in choices_raw] if isinstance(choices_raw, list) else None
        )
        result[str(field_name)] = MetadataFieldSchema(
            field_type=str(definition["type"]),
            required=bool(definition.get("required", False)),
            choices=choices,
        )
    return result


def _parse_taxonomies(raw: Any) -> dict[str, TaxonomyConfig]:
    """Parse the ``taxonomies`` section into a name-keyed mapping."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError("taxonomies must be a mapping", key_path="taxonomies")
    result: dict[str, TaxonomyConfig] = {}
    for taxonomy_name, definition in raw.items():
        key_path = f"taxonomies.{taxonomy_name}"
        if not isinstance(definition, dict):
            raise ConfigError("taxonomy must be a mapping", key_path=key_path)
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
        raise ConfigError("ai must be a mapping", key_path="ai")
    robots_raw = raw.get("robots") or {}
    if not isinstance(robots_raw, dict):
        raise ConfigError("ai.robots must be a mapping", key_path="ai.robots")
    robots: dict[str, list[str]] = {
        str(directive): [str(crawler) for crawler in (crawlers or [])]
        for directive, crawlers in robots_raw.items()
    }
    return AIConfig(
        llms_txt=bool(raw.get("llms_txt", True)),
        llms_full_txt=bool(raw.get("llms_full_txt", True)),
        markdown_variants=bool(raw.get("markdown_variants", True)),
        robots=robots,
    )


def _parse_dev_server(raw: Any) -> DevServerConfig:
    """Parse the ``dev_server`` section, returning defaults when absent."""
    if raw is None:
        return DevServerConfig()
    if not isinstance(raw, dict):
        raise ConfigError("dev_server must be a mapping", key_path="dev_server")
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
                )


def _optional_str(value: Any) -> str | None:
    """Return ``str(value)`` when ``value`` is not ``None``, else ``None``."""
    return None if value is None else str(value)
