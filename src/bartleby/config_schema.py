# ABOUTME: Describes every bartleby.yml key as data: path, type, default, choices, description.
# The single source for --full-config, `config schema`, and the configuration reference docs.

"""The schema of ``bartleby.yml`` as data.

:data:`CONFIG_SCHEMA` lists every key :mod:`bartleby.config` accepts, grouped by top-level key.
It is the single source for ``new site --full-config``, ``config schema``, and the
configuration reference docs, so none of them keeps its own list of options.

The schema mirrors ``config.py``; it does not drive it. Defaults are read from the
``config.py`` dataclasses and closed sets from :data:`bartleby.theme_loader.THEME_FEATURES`
and :data:`bartleby.config.METADATA_FIELD_TYPES`, so a changed default cannot drift.
``tests/test_config_schema.py`` fails when ``config.py`` accepts a top-level key the
schema does not describe.

A path segment in angle brackets (``content_types.<name>.path``) stands for a
user-chosen name; such an entry is ``repeatable``.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bartleby import config
from bartleby.theme_loader import THEME_FEATURES

if TYPE_CHECKING:
    from pathlib import Path

_FEED_FORMATS: tuple[str, ...] = ("rss", "atom")
_COLOR_MODES: tuple[str, ...] = ("light", "dark")


@dataclass(slots=True, frozen=True)
class ConfigField:
    """One accepted ``bartleby.yml`` key.

    :ivar path: Dotted key path; ``<name>`` segments stand for user-chosen names.
    :ivar type_name: One of ``string``, ``integer``, ``boolean``, ``list``, ``mapping``.
    :ivar default: The value used when the key is absent (``None`` when there is none).
    :ivar choices: The allowed values for a closed set, else ``None``.
    :ivar repeatable: Whether the path holds a ``<name>`` segment, so it can occur many times.
    :ivar description: A one-line explanation of what the key does.
    :ivar required: Whether the key must be present.
    """

    path: str
    type_name: str
    default: object
    choices: tuple[str, ...] | None
    repeatable: bool
    description: str
    required: bool = False


def _field(
    path: str,
    type_name: str,
    description: str,
    *,
    default: object = None,
    choices: tuple[str, ...] | None = None,
    required: bool = False,
) -> ConfigField:
    """Build a :class:`ConfigField`, deriving ``repeatable`` from the path."""
    return ConfigField(
        path=path,
        type_name=type_name,
        default=default,
        choices=choices,
        repeatable="<" in path,
        description=description,
        required=required,
    )


def _default(owner: type, attribute: str) -> object:
    """Return a dataclass field's default (or a fresh default_factory value)."""
    for dataclass_field in dataclasses.fields(owner):
        if dataclass_field.name != attribute:
            continue
        if dataclass_field.default is not dataclasses.MISSING:
            return dataclass_field.default
        if dataclass_field.default_factory is not dataclasses.MISSING:
            return dataclass_field.default_factory()
        raise AttributeError(f"{owner.__name__}.{attribute} has no default")
    raise AttributeError(f"{owner.__name__} has no field {attribute!r}")


def _site_fields() -> tuple[ConfigField, ...]:
    """Fields under ``site`` and ``site.feed``."""
    site, feed = config.SiteConfig, config.FeedConfig
    return (
        _field("site.title", "string", "The site title.", required=True),
        _field(
            "site.url", "string", "The canonical site URL, used for absolute links.", required=True
        ),
        _field(
            "site.description",
            "string",
            "A short site description.",
            default=_default(site, "description"),
        ),
        _field(
            "site.author", "string", "The default author name.", default=_default(site, "author")
        ),
        _field(
            "site.default_image",
            "string",
            "A fallback social image path or URL.",
            default=_default(site, "default_image"),
        ),
        _field(
            "site.twitter",
            "string",
            "The site Twitter handle for social cards.",
            default=_default(site, "twitter"),
        ),
        _field(
            "site.feed.enabled",
            "boolean",
            "Generate the site-wide aggregate feed.",
            default=_default(feed, "enabled"),
        ),
        _field(
            "site.feed.formats",
            "list",
            "Feed formats to emit at the site root.",
            default=_default(feed, "formats"),
            choices=_FEED_FORMATS,
        ),
        _field(
            "site.feed.include",
            "list",
            "Content types to aggregate; empty means every type with feeds.",
            default=_default(feed, "include"),
        ),
        _field(
            "site.feed.limit",
            "integer",
            "Maximum items in the aggregate feed.",
            default=_default(feed, "limit"),
        ),
        _field(
            "site.feed.title",
            "string",
            "Feed title override; falls back to site.title.",
            default=_default(feed, "title"),
        ),
    )


def _nav_fields() -> tuple[ConfigField, ...]:
    """The ``nav`` field."""
    return (
        _field(
            "nav", "list", "Explicit navigation tree; omit to build it from the content directory."
        ),
    )


def _theme_fields() -> tuple[ConfigField, ...]:
    """Fields under ``theme``."""
    theme = config.ThemeConfig
    return (
        _field(
            "theme.name",
            "string",
            "A bundled theme name. Set only one of name, path, or package.",
            default=_default(theme, "name"),
        ),
        _field(
            "theme.path",
            "string",
            "A theme directory, relative to the project or absolute.",
            default=_default(theme, "path"),
        ),
        _field(
            "theme.package",
            "string",
            "A theme installed as a bartleby.themes entry point.",
            default=_default(theme, "package"),
        ),
        _field(
            "theme.features",
            "list",
            "Theme features to enable.",
            default=_default(theme, "features"),
            choices=tuple(sorted(THEME_FEATURES)),
        ),
        _field(
            "theme.tokens",
            "mapping",
            "Design-token overrides, dotted token name to CSS value.",
            default=_default(theme, "tokens"),
        ),
        _field(
            "theme.color_mode.default",
            "string",
            "The color mode used before a visitor chooses one.",
            choices=_COLOR_MODES,
        ),
        _field(
            "theme.icon_packs",
            "mapping",
            "Icon pack name to enabled flag.",
            default=_default(theme, "icon_packs"),
        ),
        _field(
            "theme.logo",
            "string",
            "The site logo, a path under static/ or a URL.",
            default=_default(theme, "logo"),
        ),
        _field(
            "theme.favicon",
            "string",
            "The site favicon, a path under static/ or a URL.",
            default=_default(theme, "favicon"),
        ),
    )


def _top_level_value_fields() -> tuple[ConfigField, ...]:
    """Plain top-level keys: authors file, exclusions, extensions, plugins, assets, output."""
    root = config.BartlebyConfig
    return (
        _field(
            "authors_file",
            "string",
            "The authors file, relative to the project.",
            default=".authors.yml",
        ),
        _field(
            "exclude_patterns",
            "list",
            "Glob patterns for content files to skip.",
            default=list(config.DEFAULT_EXCLUDE_PATTERNS),
        ),
        _field(
            "markdown_extensions",
            "list",
            "Extra Python-Markdown extensions, by name or name with options.",
            default=[],
        ),
        _field(
            "plugins",
            "list",
            "Plugins to enable; a name-to-boolean mapping also disables auto-registered ones.",
            default=[],
        ),
        _field(
            "extra_css",
            "list",
            "Extra stylesheet paths or URLs to load on every page.",
            default=[],
        ),
        _field(
            "extra_js",
            "list",
            "Extra script paths or URLs to load on every page.",
            default=[],
        ),
        _field(
            "output_dir",
            "string",
            "Where the built site is written.",
            default=_default(root, "output_dir"),
        ),
    )


def _content_type_fields() -> tuple[ConfigField, ...]:
    """Fields under ``content_types.<name>``."""
    content_type, pagination, metadata = (
        config.ContentTypeConfig,
        config.PaginationConfig,
        config.MetadataFieldSchema,
    )
    base = "content_types.<name>"
    return (
        _field(
            f"{base}.path",
            "string",
            "The directory under content/ that holds this type.",
            required=True,
        ),
        _field(
            f"{base}.enabled",
            "boolean",
            "Build this type's listing, pages, and feeds; false skips them but keeps the block.",
            default=_default(content_type, "enabled"),
        ),
        _field(
            f"{base}.url_base",
            "string",
            "The URL prefix for this type.",
            default=_default(content_type, "url_base"),
        ),
        _field(
            f"{base}.url_format",
            "string",
            "The URL pattern for pages of this type.",
            default=_default(content_type, "url_format"),
        ),
        _field(
            f"{base}.taxonomies",
            "list",
            "Taxonomies this type uses; each must be declared under taxonomies.",
            default=_default(content_type, "taxonomies"),
        ),
        _field(
            f"{base}.feeds",
            "list",
            "Feed formats to emit for this type.",
            default=_default(content_type, "feeds"),
            choices=_FEED_FORMATS,
        ),
        _field(
            f"{base}.readtime",
            "boolean",
            "Compute a reading time for each page.",
            default=_default(content_type, "readtime"),
        ),
        _field(
            f"{base}.excerpt_separator",
            "string",
            "The marker that ends a page excerpt.",
            default=_default(content_type, "excerpt_separator"),
        ),
        _field(
            f"{base}.pagination.enabled",
            "boolean",
            "Paginate the listing page.",
            default=_default(pagination, "enabled"),
        ),
        _field(
            f"{base}.pagination.per_page",
            "integer",
            "Items per listing page.",
            default=_default(pagination, "per_page"),
        ),
        _field(
            f"{base}.pagination.url_format",
            "string",
            "The URL pattern for pages after the first.",
            default=_default(pagination, "url_format"),
        ),
        _field(
            f"{base}.metadata.<field>.type",
            "string",
            "The front matter field type.",
            choices=config.METADATA_FIELD_TYPES,
            required=True,
        ),
        _field(
            f"{base}.metadata.<field>.required",
            "boolean",
            "Whether pages must set this field.",
            default=_default(metadata, "required"),
        ),
        _field(
            f"{base}.metadata.<field>.choices",
            "list",
            "Allowed values for this field.",
            default=_default(metadata, "choices"),
        ),
    )


def _taxonomy_fields() -> tuple[ConfigField, ...]:
    """Fields under ``taxonomies.<name>``."""
    return (
        _field(
            "taxonomies.<name>.slug_format",
            "string",
            "The URL slug pattern for a term.",
            default="{slug}",
        ),
    )


def _ai_fields() -> tuple[ConfigField, ...]:
    """Fields under ``ai``."""
    ai, skills, context = config.AIConfig, config.SkillsConfig, config.AgentContext
    return (
        _field("ai.llms_txt", "boolean", "Write llms.txt.", default=_default(ai, "llms_txt")),
        _field(
            "ai.llms_full_txt",
            "boolean",
            "Write llms-full.txt.",
            default=_default(ai, "llms_full_txt"),
        ),
        _field(
            "ai.markdown_variants",
            "boolean",
            "Write a Markdown variant of each page.",
            default=_default(ai, "markdown_variants"),
        ),
        _field(
            "ai.agent_surface",
            "boolean",
            "Write schema.json and content-index.json.",
            default=_default(ai, "agent_surface"),
        ),
        _field(
            "ai.robots",
            "mapping",
            "Crawler directives, such as disallow mapped to a list of crawlers.",
            default=_default(ai, "robots"),
        ),
        _field(
            "ai.skills.output_dir",
            "string",
            "Where generated agent skills are written.",
            default=_default(skills, "output_dir"),
        ),
        _field(
            "ai.skills.style_guide",
            "string",
            "A style guide file included in generated skills.",
            default=_default(skills, "style_guide"),
        ),
        _field(
            "ai.skills.regenerate_on_build",
            "boolean",
            "Regenerate skills on every build.",
            default=_default(skills, "regenerate_on_build"),
        ),
        _field(
            "ai.agent_context.voice",
            "string",
            "The writing voice, included in generated skills.",
            default=_default(context, "voice"),
        ),
        _field(
            "ai.agent_context.audience",
            "string",
            "The target audience, included in generated skills.",
            default=_default(context, "audience"),
        ),
        _field(
            "ai.agent_context.constraints",
            "list",
            "Rules generated skills must follow.",
            default=_default(context, "constraints"),
        ),
    )


def _dev_server_fields() -> tuple[ConfigField, ...]:
    """Fields under ``dev_server``."""
    dev_server = config.DevServerConfig
    return (
        _field(
            "dev_server.host",
            "string",
            "The host the dev server binds to.",
            default=_default(dev_server, "host"),
        ),
        _field(
            "dev_server.port",
            "integer",
            "The port the dev server listens on.",
            default=_default(dev_server, "port"),
        ),
    )


CONFIG_SCHEMA: tuple[ConfigField, ...] = (
    *_site_fields(),
    *_nav_fields(),
    *_theme_fields(),
    *_top_level_value_fields(),
    *_content_type_fields(),
    *_taxonomy_fields(),
    *_ai_fields(),
    *_dev_server_fields(),
)
"""Every accepted ``bartleby.yml`` key, grouped by top-level key."""


def schema_field(path: str) -> ConfigField:
    """Return the schema entry for a dotted path.

    :param path: A dotted key path as it appears in :data:`CONFIG_SCHEMA`.
    :returns: The matching :class:`ConfigField`.
    :raises KeyError: If no entry has that path.
    """
    for entry in CONFIG_SCHEMA:
        if entry.path == path:
            return entry
    raise KeyError(path)


def resolve_with_sources(
    config_path: Path, overrides: list[str] | None = None
) -> dict[str, tuple[Any, str]]:
    """Resolve every config value together with where it came from.

    This lives beside :data:`CONFIG_SCHEMA`, which already imports :mod:`bartleby.config`,
    so the dependency stays one-directional. File and ``--set`` tags come from
    :func:`bartleby.config.source_tags`; a key neither supplied is filled from the
    schema and tagged :data:`bartleby.config.SOURCE_DEFAULT`. Keys under a user-chosen
    name (``content_types.<name>...``) get no default entry. A null or empty-mapping
    section in the file gives no row of its own when schema entries sit beneath it, so
    the result holds only real leaves.

    :param config_path: Path to the ``bartleby.yml`` file.
    :param overrides: ``key.path=value`` strings, as for :func:`bartleby.config.load_config`.
    :returns: Dotted path to ``(value, source)``, sorted by path.
    :raises FileNotFoundError: If ``config_path`` does not exist.
    :raises ConfigError: If the file or an override fails validation.
    """
    tagged = config.source_tags(config_path, overrides)

    # An empty or null section (`feed: {}`, a bare `theme:`) is a leaf in the file, but
    # the defaults beneath it are filled below, so the section itself is not a real value.
    resolved = {
        path: tagged_value
        for path, tagged_value in tagged.items()
        if not (
            (tagged_value[0] is None or tagged_value[0] == {})
            and any(entry.path.startswith(f"{path}.") for entry in CONFIG_SCHEMA)
        )
    }

    for entry in CONFIG_SCHEMA:
        if entry.repeatable:
            continue
        if not any(config.same_branch(path, entry.path) for path in resolved):
            resolved[entry.path] = (entry.default, config.SOURCE_DEFAULT)
    return dict(sorted(resolved.items()))


_MISSING = object()


def _parsed_value(parsed: config.BartlebyConfig, path: str, raw: Any) -> Any:
    """Read ``path`` off the loaded config, or return ``raw`` when it has no parsed form.

    A segment is looked up as a mapping key (on a dict) or an attribute (on a dataclass);
    a path that continues past any other value keeps the raw value. A path that does not
    resolve (``theme.color_mode.default`` when unset, a design-token name containing a
    dot) or that lands on a whole dataclass keeps the raw value.
    """
    node: object = parsed
    for segment in path.split("."):
        if isinstance(node, dict):
            node = node.get(segment, _MISSING)
        elif dataclasses.is_dataclass(node):
            node = getattr(node, segment, _MISSING)
        else:
            return raw
        if node is _MISSING:
            return raw
    return raw if dataclasses.is_dataclass(node) else node


def resolve_parsed_with_sources(
    config_path: Path, overrides: list[str] | None = None
) -> dict[str, tuple[Any, str]]:
    """Resolve every config value as the build sees it, with where it came from.

    :func:`resolve_with_sources` carries raw YAML values (a quoted feed limit ``"25"`` is
    the string there). This keeps its sources and takes each value from the loaded
    :class:`bartleby.config.BartlebyConfig` where a parsed value exists (``25`` as an
    int), so ``config show`` and ``config get`` print what the build uses. The keys and
    sources are those of :func:`resolve_with_sources`.

    :param config_path: Path to the ``bartleby.yml`` file.
    :param overrides: ``key.path=value`` strings, as for :func:`bartleby.config.load_config`.
    :returns: Dotted path to ``(parsed value, source)``, sorted by path.
    :raises FileNotFoundError: If ``config_path`` does not exist.
    :raises ConfigError: If the file or an override fails validation.
    """
    resolved = resolve_with_sources(config_path, overrides)
    parsed = config.load_config(config_path, overrides)
    return {
        path: (_parsed_value(parsed, path, raw), source)
        for path, (raw, source) in resolved.items()
    }
