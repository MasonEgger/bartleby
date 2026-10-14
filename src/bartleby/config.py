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

import dataclasses
import difflib
import os
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

import yaml
from markwright import ConfigError as MarkwrightConfigError
from markwright import config_from_mapping

from bartleby.config_model import (
    BUILD_INPUT_DIRS,
    COLOR_MODES,
    DEFAULT_EXCLUDE_PATTERNS,
    DOTTED_KEY_SECTIONS,
    FEED_FORMATS,
    MARKWRIGHT_KEY,
    METADATA_FIELD_TYPES,
    OVERRIDE_SOURCE,
    SOURCE_DEFAULT,
    SOURCE_FILE,
    AgentContext,
    AIConfig,
    BartlebyConfig,
    ConfigError,
    ContentTypeConfig,
    DevServerConfig,
    FeedConfig,
    MetadataFieldSchema,
    PaginationConfig,
    SiteConfig,
    SkillsConfig,
    TaxonomyConfig,
    ThemeConfig,
    _StrictLoader,
    existing_prefix,
    parse_override_value,
    same_branch,
    split_path,
    yaml_location,
)
from bartleby.config_schema import CONFIG_SCHEMA, override_value
from bartleby.theme_loader import DEFAULT_THEME_NAME, THEME_FEATURES

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from markwright import Config as MarkwrightConfig

__all__ = (
    "BUILD_INPUT_DIRS",
    "COLOR_MODES",
    "DEFAULT_EXCLUDE_PATTERNS",
    "DOTTED_KEY_SECTIONS",
    "FEED_FORMATS",
    "MARKWRIGHT_KEY",
    "METADATA_FIELD_TYPES",
    "OVERRIDE_SOURCE",
    "SOURCE_DEFAULT",
    "SOURCE_FILE",
    "AIConfig",
    "AgentContext",
    "BartlebyConfig",
    "ConfigError",
    "ContentTypeConfig",
    "DevServerConfig",
    "FeedConfig",
    "MetadataFieldSchema",
    "PaginationConfig",
    "SiteConfig",
    "SkillsConfig",
    "TaxonomyConfig",
    "ThemeConfig",
    "apply_overrides",
    "existing_prefix",
    "load_config",
    "markwright_config",
    "parse_override_value",
    "read_config_text",
    "resolve_parsed_with_sources",
    "resolve_with_sources",
    "same_branch",
    "source_tags",
    "split_path",
    "validate_config_text",
    "yaml_location",
)
"""The module's own entry points plus every :mod:`bartleby.config_model` name, re-exported."""


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


def _string_field(raw: dict[str, Any], key: str, default: str) -> str:
    """Read a string key; ``None`` or absent yields ``default``, anything else is ``str()``-ed.

    :param raw: The mapping that holds the key.
    :param key: The key to read.
    :param default: The value for an absent or null key.
    """
    value = raw.get(key)
    return default if value is None else str(value)


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


def apply_overrides(raw: dict[str, Any], sets: list[str]) -> dict[str, Any]:
    """Apply ``key.path=value`` overrides to a raw config mapping, in order.

    Each value is typed by the schema (:func:`bartleby.config_schema.override_value`):
    a string key keeps the text as typed, and any other key parses it as YAML, so
    ``42`` is an int, ``true`` a bool, ``[a, b]`` a list, and an empty value null. A
    dotted path creates the mappings it passes through, and a key set twice keeps the
    last value. The result still goes through the normal validator; :func:`load_config`
    labels any error it raises for an overridden key with ``--set`` as its source.

    :param raw: The parsed config mapping; mutated in place.
    :param sets: Overrides written ``key.path=value``.
    :returns: ``raw``.
    :raises ConfigError: If an override has no ``=``, names a key the schema lacks, has a
        malformed path or a value of the wrong type, or passes through a non-mapping.
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
            value = override_value(dotted_path, text)
            segments = split_path(dotted_path)
            holder, depth = existing_prefix(raw, segments)
        except ConfigError as exc:
            exc.source = OVERRIDE_SOURCE
            raise
        for segment in reversed(segments[depth + 1 :]):
            value = {segment: value}
        holder[segments[depth]] = value
    return raw


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
    neither supplied are absent; :func:`resolve_with_sources` adds them as
    :data:`SOURCE_DEFAULT`.

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


def resolve_with_sources(
    config_path: Path, overrides: list[str] | None = None
) -> dict[str, tuple[Any, str]]:
    """Resolve every config value together with where it came from.

    File and ``--set`` tags come from :func:`source_tags`; a key neither supplied is
    filled from :data:`bartleby.config_schema.CONFIG_SCHEMA` and tagged
    :data:`SOURCE_DEFAULT`. Keys under a user-chosen name (``content_types.<name>...``)
    get no default entry. A null or empty-mapping section in the file gives no row of
    its own when schema entries sit beneath it, so the result holds only real leaves.

    :param config_path: Path to the ``bartleby.yml`` file.
    :param overrides: ``key.path=value`` strings, as for :func:`load_config`.
    :returns: Dotted path to ``(value, source)``, sorted by path.
    :raises FileNotFoundError: If ``config_path`` does not exist.
    :raises ConfigError: If the file or an override fails validation.
    """
    tagged = source_tags(config_path, overrides)

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
        if not any(same_branch(path, entry.path) for path in resolved):
            resolved[entry.path] = (entry.default, SOURCE_DEFAULT)
    return dict(sorted(resolved.items()))


_MISSING = object()


def _parsed_value(parsed: BartlebyConfig, path: str, raw: Any) -> Any:
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
    :class:`BartlebyConfig` where a parsed value exists (``25`` as an int), so
    ``config show`` and ``config get`` print what the build uses. The keys and sources
    are those of :func:`resolve_with_sources`.

    :param config_path: Path to the ``bartleby.yml`` file.
    :param overrides: ``key.path=value`` strings, as for :func:`load_config`.
    :returns: Dotted path to ``(parsed value, source)``, sorted by path.
    :raises FileNotFoundError: If ``config_path`` does not exist.
    :raises ConfigError: If the file or an override fails validation.
    """
    resolved = resolve_with_sources(config_path, overrides)
    parsed = load_config(config_path, overrides)
    return {
        path: (_parsed_value(parsed, path, raw), source)
        for path, (raw, source) in resolved.items()
    }


def load_config(config_path: Path, overrides: list[str] | None = None) -> BartlebyConfig:
    """Load and validate a ``bartleby.yml`` configuration file.

    :param config_path: Path to the ``bartleby.yml`` file.
    :param overrides: ``key.path=value`` strings from ``--set``, applied by
        :func:`apply_overrides` to the parsed file before validation, so they face the
        same rules as file values. A validation error on an overridden key (or on a
        key beneath it) names ``--set`` as its source instead of the file.
    :returns: A fully parsed and validated :class:`BartlebyConfig`.
    :raises FileNotFoundError: If ``config_path`` does not exist.
    :raises ConfigError: If the file cannot be read, is empty, malformed, or fails validation.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    sets = overrides or []
    try:
        return _load_config_text(config_path, sets)
    except ConfigError as exc:
        if exc.source is None:
            exc.source = (
                OVERRIDE_SOURCE if _override_at_fault(exc, config_path, sets) else config_path
            )
        raise


def _override_at_fault(exc: ConfigError, config_path: Path, overrides: list[str]) -> bool:
    """Whether a validation error is down to a ``--set`` override rather than the file.

    An error at or under an override path is the override's. An error on a parent of
    an override path (``theme: set only one of name, path, or package``) is the
    override's only when the file, loaded with every override under that parent
    dropped, no longer raises it.
    """
    key_path = exc.key_path
    override_paths = [token.partition("=")[0] for token in overrides]
    if any(same_branch(key_path, path) for path in override_paths):
        return True
    if key_path is None or not any(same_branch(path, key_path) for path in override_paths):
        return False

    # Reload without the overrides beneath the failing key to see whether the file alone raises it.
    unrelated = [
        token for token in overrides if not same_branch(token.partition("=")[0], key_path)
    ]
    try:
        _load_config_text(config_path, unrelated)
    except ConfigError as file_exc:
        return (file_exc.key_path, file_exc.message) != (exc.key_path, exc.message)
    return True


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


def read_config_text(config_path: Path) -> str:
    """Read ``bartleby.yml`` exactly as written: byte order mark and line endings kept.

    The one place the config file is read, so an unreadable path is one error.

    :param config_path: The file to read.
    :returns: The file text.
    :raises ConfigError: If the path is a directory or cannot be read.
    """
    try:
        with config_path.open(encoding="utf-8", newline="") as handle:
            return handle.read()
    except OSError as exc:
        raise ConfigError(
            f"cannot read config file ({exc.strerror or exc})",
            hint="pass --config with the path to a readable bartleby.yml file",
            source=config_path,
        ) from exc


def _read_raw_config(config_path: Path) -> dict[str, Any]:
    """Read ``config_path`` as a YAML mapping; the caller attaches the source."""
    return _parse_raw_text(read_config_text(config_path))


def _parse_raw_text(raw_text: str) -> dict[str, Any]:
    """Parse config text as a YAML mapping; the caller attaches the source."""
    try:
        parsed: Any = yaml.load(raw_text.removeprefix("\ufeff"), Loader=_StrictLoader)
    except yaml.YAMLError as exc:
        raise ConfigError(
            f"invalid YAML{yaml_location(exc)}",
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
        authors_file=_string_field(raw, "authors_file", ".authors.yml"),
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
        output_dir=_string_field(raw, "output_dir", "site"),
        markwright=_parse_markwright(raw.get("markwright")),
    )


def _parse_markwright(raw: Any) -> dict[str, object]:
    """Carry the ``markwright`` section through as written, once markwright has validated it.

    :param raw: The raw ``markwright`` value from the parsed YAML.
    :returns: The section as a plain mapping, empty when the key is absent or null.
    :raises ConfigError: If the section is not a mapping, or markwright rejects it.
    """
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise _expected(MARKWRIGHT_KEY, "mapping", "`markwright: {disable: [youtube]}`")
    section = {str(key): value for key, value in raw.items()}
    markwright_config(section)
    return section


def markwright_config(section: dict[str, object]) -> MarkwrightConfig:
    """Resolve the ``markwright:`` section through markwright's public config API.

    Shared by validation here and by the renderer, so a section that loads always renders.
    ``warn`` defaults to true, so a fence directive the site's ``allowed_environments``
    leaves out is reported; the section may set it to false.

    :param section: The raw section, empty when ``bartleby.yml`` has none.
    :returns: markwright's resolved config.
    :raises ConfigError: With markwright's message under the ``markwright`` key path, when
        markwright rejects the section; the caller attaches the source.
    """
    try:
        return config_from_mapping({"warn": True, **section}, MARKWRIGHT_KEY)
    except MarkwrightConfigError as exc:
        raise ConfigError(
            str(exc).removeprefix(f"{MARKWRIGHT_KEY}: "),
            key_path=MARKWRIGHT_KEY,
            hint="fix the `markwright:` section; it takes the same keys as markwright.toml",
        ) from exc


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
        url=_site_base_url(str(raw["url"])),
        description=_string_field(raw, "description", ""),
        author=_string_field(raw, "author", ""),
        default_image=_optional_str(raw.get("default_image")),
        twitter=_optional_str(raw.get("twitter")),
        language=_string_field(raw, "language", "en"),
        feed=_parse_feed(raw.get("feed")),
    )


def _site_base_url(url: str) -> str:
    """Require ``site.url`` to be an absolute ``http`` or ``https`` URL with a host.

    :param url: The value as written.
    :returns: ``url`` unchanged.
    :raises ConfigError: If the scheme or host is missing (``""``, ``example.com``, ``https://``).
    """
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ConfigError(
            f"{url!r} is not an absolute http(s) URL",
            key_path="site.url",
            hint="write the full address with its scheme, such as `url: https://example.com`",
        )
    return url


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
        url_format=_string_field(raw, "url_format", "page/{page}"),
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
        slug_format = definition.get("slug_format")
        if slug_format is None:
            slug_format = "{slug}"
        if not isinstance(slug_format, str):
            raise ConfigError(
                "must be a string",
                key_path=f"{key_path}.slug_format",
                hint=(
                    "quote the pattern so YAML reads it as text: "
                    '`slug_format: "{slug}"` in the file; from the shell, '
                    "`config set taxonomies.<name>.slug_format '{slug}'` stores it as text"
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
        output_dir=_string_field(raw, "output_dir", ".claude/skills"),
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
        host=_string_field(raw, "host", "127.0.0.1"),
        port=_int_field(raw, "port", 8000, "dev_server"),
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

    _validate_output_dir(config)

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


def _validate_output_dir(config: BartlebyConfig) -> None:
    """Reject an ``output_dir`` the build would delete before reading from it.

    The build replaces the output directory whole, so it may not be the project
    directory, an ancestor of it, or any directory under the project that the
    build reads (:data:`BUILD_INPUT_DIRS` and a path theme), nor hold one of them.

    :param config: The parsed config to validate.
    :raises ConfigError: If ``output_dir`` overlaps a directory the build reads.
    """
    project_dir = config.config_dir.resolve()
    output_dir = (project_dir / config.output_dir).resolve()
    hint = "set output_dir to a directory the build does not read, such as site"

    if project_dir.is_relative_to(output_dir):
        raise ConfigError(
            f"{config.output_dir!r} holds the project itself, which the build would delete",
            key_path="output_dir",
            hint=hint,
        )

    input_dirs = [project_dir / name for name in BUILD_INPUT_DIRS]
    if config.theme.path is not None:
        input_dirs.append((project_dir / config.theme.path).resolve())
    for input_dir in input_dirs:
        if output_dir.is_relative_to(input_dir) or input_dir.is_relative_to(output_dir):
            overlapped = os.path.relpath(input_dir, project_dir)
            raise ConfigError(
                f"{config.output_dir!r} overlaps {overlapped}/, which the build reads",
                key_path="output_dir",
                hint=hint,
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
