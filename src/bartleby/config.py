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
    from collections.abc import Iterator
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
    "markwright",
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

FEED_FORMATS: tuple[str, ...] = ("rss", "atom")
"""The feed formats ``site.feed.formats`` and a content type's ``feeds`` accept."""

COLOR_MODES: tuple[str, ...] = ("light", "dark")
"""The values ``theme.color_mode.default`` accepts."""


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


def _expected(key_path: str, kind: str, example: str) -> ConfigError:
    """Build the error for a value of the wrong shape (``mapping`` or ``list``)."""
    return ConfigError(f"must be a {kind}", key_path=key_path, hint=f"write {example}")


def _string_list(
    raw: Any, key_path: str, example: str, default: list[str] | None = None
) -> list[str]:
    """Read a list-typed field as strings; a scalar or mapping is an error, not iterated.

    :param raw: The raw value; ``None`` means the key is absent.
    :param key_path: The dotted path named in the error.
    :param example: A literal showing a valid list, for the fix hint.
    :param default: What an absent key yields; a new empty list when omitted.
    :raises ConfigError: If the value is present and not a list.
    """
    if raw is None:
        return [] if default is None else list(default)
    if not isinstance(raw, list):
        raise _expected(key_path, "list", example)
    return [str(item) for item in raw]


def _check_choices(values: list[str], choices: tuple[str, ...], key_path: str) -> None:
    """Raise for the first of ``values`` that is not one of ``choices``."""
    for value in values:
        if value not in choices:
            raise ConfigError(
                f"unknown value {value!r}",
                key_path=key_path,
                hint=f"use one of {', '.join(choices)}",
            )


def _bool_field(raw: dict[str, Any], key: str, default: bool, parent_key: str) -> bool:
    """Read a boolean key; anything but ``true`` or ``false`` is an error.

    :param raw: The mapping that holds the key.
    :param key: The key to read; ``None`` or absent yields ``default``.
    :param default: The value for an absent key.
    :param parent_key: The dotted path of ``raw``, or empty for the file root.
    :raises ConfigError: If the value is not a boolean.
    """
    value = raw.get(key)
    if value is None:
        return default
    if not isinstance(value, bool):
        key_path = f"{parent_key}.{key}" if parent_key else key
        raise ConfigError(
            "must be true or false",
            key_path=key_path,
            hint=f"write `{key}: true` or `{key}: false`",
        )
    return value


def _int_field(raw: dict[str, Any], key: str, default: int, parent_key: str) -> int:
    """Read an integer key; a numeric string such as ``"8000"`` is coerced, anything else errors.

    :param raw: The mapping that holds the key.
    :param key: The key to read; ``None`` or absent yields ``default``.
    :param default: The value for an absent key.
    :param parent_key: The dotted path of ``raw``.
    :raises ConfigError: If the value is not an integer or a string of digits.
    """
    value = raw.get(key)
    if value is None:
        return default
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    raise ConfigError(
        "must be an integer", key_path=f"{parent_key}.{key}", hint=f"write `{key}: {default}`"
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
        ``markwright.toml`` and is validated by markwright's own config API at render time
        (:func:`bartleby.markdown_pipeline.create_markdown_renderer`), never here.
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


def parse_override_value(dotted_path: str, text: str) -> Any:
    """Parse the text of a ``--set`` or ``config set`` value as YAML.

    ``42`` is an int, ``true`` a bool, ``[a, b]`` a list, and empty text null.

    :param dotted_path: The key the value is for; named in the error.
    :param text: The value as the user typed it.
    :returns: The parsed value.
    :raises ConfigError: If ``text`` is not valid YAML.
    """
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(
            f"value {text!r} is not valid YAML{_yaml_location(exc)}",
            key_path=dotted_path,
            hint="wrap the value in quotes, such as '\"Hello: World\"'",
        ) from exc


def apply_overrides(raw: dict[str, Any], sets: list[str]) -> dict[str, Any]:
    """Apply ``key.path=value`` overrides to a raw config mapping, in order.

    Each value is parsed as YAML, so ``42`` is an int, ``true`` a bool, ``[a, b]`` a
    list, and an empty value null. A dotted path creates the mappings it passes
    through, and a key set twice keeps the last value. The result still goes through
    the normal validator; :func:`load_config` labels any error it raises for an
    overridden key with ``--set`` as its source.

    :param raw: The parsed config mapping; mutated in place.
    :param sets: Overrides written ``key.path=value``.
    :returns: ``raw``.
    :raises ConfigError: If an override has no ``=``, a malformed path or YAML value,
        or passes through a key that holds a non-mapping.
    """
    for token in sets:
        dotted_path, separator, text = token.partition("=")
        if not separator:
            raise ConfigError(
                f"override {token!r} has no '='",
                hint="write --set key.path=value, such as --set site.title=Hello",
                source=OVERRIDE_SOURCE,
            )
        try:
            value = parse_override_value(dotted_path, text)
            segments = split_path(dotted_path)
            holder, depth = existing_prefix(raw, segments)
        except ConfigError as exc:
            exc.source = OVERRIDE_SOURCE
            raise
        for segment in reversed(segments[depth + 1 :]):
            value = {segment: value}
        holder[segments[depth]] = value
    return raw


SOURCE_DEFAULT = "default"
"""The provenance label for a value no file key or override supplied; set by ``config_schema``."""

SOURCE_FILE = "file"
"""The provenance label for a value read from ``bartleby.yml``."""


def _flatten(node: Any, prefix: str) -> Iterator[tuple[str, Any]]:
    """Yield ``(dotted path, value)`` for each leaf of a raw config mapping.

    A leaf is any non-mapping value (lists included) or an empty mapping.
    """
    if isinstance(node, dict) and node:
        for key, child in node.items():
            yield from _flatten(child, f"{prefix}.{key}" if prefix else str(key))
    else:
        yield prefix, node


def source_tags(
    config_path: Path, overrides: list[str] | None = None
) -> dict[str, tuple[Any, str]]:
    """Tag each key the file or an override supplies with where it came from.

    :data:`SOURCE_FILE` marks a key written in ``bartleby.yml``. :data:`OVERRIDE_SOURCE`
    (``--set``) marks a key given by an override, which wins over the file;
    ``--base-url`` is a ``site.url=<url>`` override, so it reads ``--set`` too. Keys
    neither supplied are absent; ``bartleby.config_schema.resolve_with_sources`` adds
    them as :data:`SOURCE_DEFAULT`.

    Provenance is tagged from the same merged mapping :func:`load_config` validates, so
    the two cannot disagree about a final value. Values are the raw YAML values, before
    the validator normalizes them.

    :param config_path: Path to the ``bartleby.yml`` file.
    :param overrides: ``key.path=value`` strings, as for :func:`load_config`.
    :returns: Dotted leaf path to ``(value, source)``, in file order.
    :raises FileNotFoundError: If ``config_path`` does not exist.
    :raises ConfigError: If the file or an override fails validation.
    """
    sets = overrides or []
    load_config(config_path, sets)
    merged = apply_overrides(_read_raw_config(config_path), sets)
    override_paths = [token.partition("=")[0] for token in sets]

    tagged: dict[str, tuple[Any, str]] = {}
    for path, value in _flatten(merged, ""):
        overridden = any(same_branch(path, override_path) for override_path in override_paths)
        tagged[path] = (value, OVERRIDE_SOURCE if overridden else SOURCE_FILE)
    return tagged


def load_config(config_path: Path, overrides: list[str] | None = None) -> BartlebyConfig:
    """Load and validate a ``bartleby.yml`` configuration file.

    :param config_path: Path to the ``bartleby.yml`` file.
    :param overrides: ``key.path=value`` strings from ``--set``, applied by
        :func:`apply_overrides` to the parsed file before validation, so they face the
        same rules as file values. A validation error on an overridden key (or on a
        key beneath it) names ``--set`` as its source instead of the file.
    :returns: A fully parsed and validated :class:`BartlebyConfig`.
    :raises FileNotFoundError: If ``config_path`` does not exist.
    :raises ConfigError: If the file is empty, malformed, or fails validation.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        return _load_config_text(config_path, overrides or [])
    except ConfigError as exc:
        if exc.source is None:
            overridden = (token.partition("=")[0] for token in overrides or [])
            exc.source = (
                OVERRIDE_SOURCE
                if any(same_branch(exc.key_path, path) for path in overridden)
                else config_path
            )
        raise


def validate_config_text(text: str, config_path: Path) -> None:
    """Validate candidate ``bartleby.yml`` text in memory, exactly as :func:`load_config` would.

    ``config set`` calls this on the edited text before writing it, so a rejected
    value never reaches the file.

    :param text: The candidate file contents.
    :param config_path: Where the text would be written; it names the error source and
        gives the directory relative paths resolve against.
    :raises ConfigError: If the text is empty, malformed, or fails validation.
    """
    try:
        _validate_raw(_parse_raw_text(text), config_path.parent)
    except ConfigError as exc:
        if exc.source is None:
            exc.source = config_path
        raise


def same_branch(key_path: str | None, override_path: str) -> bool:
    """Whether ``key_path`` equals ``override_path`` or sits under it."""
    if not key_path:
        return False
    return key_path == override_path or key_path.startswith(f"{override_path}.")


def _read_raw_config(config_path: Path) -> dict[str, Any]:
    """Read ``config_path`` as a YAML mapping; the caller attaches the source."""
    return _parse_raw_text(config_path.read_text(encoding="utf-8"))


def _parse_raw_text(raw_text: str) -> dict[str, Any]:
    """Parse config text as a YAML mapping; the caller attaches the source."""
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
    return parsed


def _load_config_text(config_path: Path, overrides: list[str]) -> BartlebyConfig:
    """Parse and validate the file at ``config_path``; the caller attaches the source."""
    parsed = _read_raw_config(config_path)
    apply_overrides(parsed, overrides)
    return _validate_raw(parsed, config_path.parent)


def _validate_raw(parsed: dict[str, Any], config_dir: Path) -> BartlebyConfig:
    """Reject unknown keys, parse ``parsed`` into a config, and run the cross-field checks."""
    _reject_unknown_top_level_keys(parsed)
    config = _parse_config(parsed, config_dir)
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
    if nav_raw is not None and not isinstance(nav_raw, list):
        raise _expected("nav", "list", "one `- Title: path.md` line per entry")
    nav: list[dict[str, object]] | None = nav_raw

    exclude_patterns = _string_list(
        raw.get("exclude_patterns"),
        "exclude_patterns",
        '`exclude_patterns: ["_drafts/**"]`',
        DEFAULT_EXCLUDE_PATTERNS,
    )

    extensions_raw = raw.get("markdown_extensions")
    if extensions_raw is not None and not isinstance(extensions_raw, list):
        raise _expected("markdown_extensions", "list", "`markdown_extensions: [tables]`")
    markdown_extensions: list[dict[str, object] | str] = list(extensions_raw or [])

    plugins, disabled_plugins = _parse_plugins(raw.get("plugins"))

    extra_css = _string_list(raw.get("extra_css"), "extra_css", "`extra_css: [css/extra.css]`")
    extra_js = _string_list(raw.get("extra_js"), "extra_js", "`extra_js: [js/extra.js]`")

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
        markwright=_parse_markwright(raw.get("markwright")),
    )


def _parse_markwright(raw: Any) -> dict[str, object]:
    """Carry the ``markwright`` section through untouched; markwright validates its contents.

    :param raw: The raw ``markwright`` value from the parsed YAML.
    :returns: The section as a plain mapping, empty when the key is absent or null.
    :raises ConfigError: If the section is not a mapping.
    """
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise _expected("markwright", "mapping", "`markwright: {disable: [youtube]}`")
    return {str(key): value for key, value in raw.items()}


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
    :raises ConfigError: If the value is neither a list nor a mapping.
    """
    if isinstance(raw, dict):
        enabled = [str(name) for name, value in raw.items() if value]
        disabled = {str(name) for name, value in raw.items() if not value}
        return enabled, disabled
    return _string_list(raw, "plugins", "`plugins: [search]` or `plugins: {search: false}`"), set()


def _parse_site(raw: Any) -> SiteConfig:
    """Parse the ``site`` section, raising :class:`ConfigError` if required fields are missing."""
    if not isinstance(raw, dict):
        raise ConfigError(
            "site section is required",
            key_path="site",
            hint="add `site:` with `title:` and `url:` lines under it",
        )
    for required in ("title", "url"):
        if raw.get(required) is None:
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
    formats = _string_list(
        raw.get("formats"), "site.feed.formats", "`formats: [rss, atom]`", list(FEED_FORMATS)
    )
    _check_choices(formats, FEED_FORMATS, "site.feed.formats")
    return FeedConfig(
        enabled=_bool_field(raw, "enabled", True, "site.feed"),
        formats=formats,
        include=_string_list(raw.get("include"), "site.feed.include", "`include: [blog]`"),
        limit=_int_field(raw, "limit", 50, "site.feed"),
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
        icon_packs=_parse_icon_packs(raw.get("icon_packs")),
        logo=_site_url(raw.get("logo")),
        favicon=_site_url(raw.get("favicon")),
    )


def _parse_icon_packs(raw: Any) -> dict[str, bool]:
    """Parse ``theme.icon_packs`` as a map of pack name to enabled flag."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise _expected("theme.icon_packs", "mapping", "`icon_packs:` followed by `lucide: true`")
    return {str(pack): _bool_field(raw, str(pack), False, "theme.icon_packs") for pack in raw}


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
    color_mode = {str(key): str(value) for key, value in raw.items() if value is not None}
    if "default" in color_mode:
        _check_choices([color_mode["default"]], COLOR_MODES, "theme.color_mode.default")
    return color_mode


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
    features = _string_list(raw, "theme.features", "`features: [search, nav.tabs]`")
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
    feeds = _string_list(raw.get("feeds"), f"{key_path}.feeds", "`feeds: [rss, atom]`")
    _check_choices(feeds, FEED_FORMATS, f"{key_path}.feeds")
    return ContentTypeConfig(
        name=type_name,
        path=str(raw["path"]),
        enabled=_bool_field(raw, "enabled", True, key_path),
        url_base=_optional_str(raw.get("url_base")),
        url_format=_optional_str(raw.get("url_format")),
        pagination=_parse_pagination(raw.get("pagination"), key_path),
        taxonomies=_string_list(
            raw.get("taxonomies"), f"{key_path}.taxonomies", "`taxonomies: [tags]`"
        ),
        feeds=feeds,
        readtime=_bool_field(raw, "readtime", False, key_path),
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
    pagination_key = f"{parent_key}.pagination"
    return PaginationConfig(
        enabled=_bool_field(raw, "enabled", False, pagination_key),
        per_page=_int_field(raw, "per_page", 10, pagination_key),
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
        choices = (
            _string_list(definition["choices"], f"{field_key}.choices", "`choices: [easy, hard]`")
            if definition.get("choices") is not None
            else None
        )
        result[str(field_name)] = MetadataFieldSchema(
            field_type=field_type,
            required=_bool_field(definition, "required", False, field_key),
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
        slug_format = definition.get("slug_format", "{slug}")
        if not isinstance(slug_format, str):
            raise ConfigError(
                "must be a string",
                key_path=f"{key_path}.slug_format",
                hint=(
                    "quote the pattern so YAML reads it as text: "
                    '`slug_format: "{slug}"` in the file, or '
                    "`config set taxonomies.<name>.slug_format '\"{slug}\"'` from the shell"
                ),
            )
        result[str(taxonomy_name)] = TaxonomyConfig(
            name=str(taxonomy_name), slug_format=slug_format
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
        str(directive): _string_list(
            crawlers, f"ai.robots.{directive}", f"`{directive}: [GPTBot]`"
        )
        for directive, crawlers in robots_raw.items()
    }
    return AIConfig(
        llms_txt=_bool_field(raw, "llms_txt", True, "ai"),
        llms_full_txt=_bool_field(raw, "llms_full_txt", True, "ai"),
        markdown_variants=_bool_field(raw, "markdown_variants", True, "ai"),
        agent_surface=_bool_field(raw, "agent_surface", True, "ai"),
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
        regenerate_on_build=_bool_field(raw, "regenerate_on_build", False, "ai.skills"),
    )


def _parse_agent_context(raw: Any) -> AgentContext:
    """Parse the ``ai.agent_context`` section (voice/audience/constraints)."""
    if raw is None:
        return AgentContext()
    if not isinstance(raw, dict):
        raise _expected(
            "ai.agent_context", "mapping", "`agent_context:` followed by `voice:` and `audience:`"
        )
    return AgentContext(
        voice=_optional_str(raw.get("voice")),
        audience=_optional_str(raw.get("audience")),
        constraints=_string_list(
            raw.get("constraints"),
            "ai.agent_context.constraints",
            "one `- constraint` line per rule",
        ),
    )


def _parse_dev_server(raw: Any) -> DevServerConfig:
    """Parse the ``dev_server`` section, returning defaults when absent."""
    if raw is None:
        return DevServerConfig()
    if not isinstance(raw, dict):
        raise _expected("dev_server", "mapping", "`dev_server:` followed by `host:` and `port:`")
    return DevServerConfig(
        host=str(raw.get("host", "127.0.0.1")), port=_int_field(raw, "port", 8000, "dev_server")
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
