# ABOUTME: Markdown rendering pipeline with all default extensions configured.
# Wires markwright, pymdownx, and standard extensions into Python-Markdown.

"""The Markdown rendering pipeline.

The markwright extensions and their options come from markwright's public config API,
driven by the ``markwright:`` section of ``bartleby.yml``: the section goes to
``config_from_mapping`` as written, ``selected_extensions`` names what loads, and
``extension_configs`` supplies the options. Bartleby never reimplements markwright's
schema; the one markwright setting it defaults differently is ``warn``, on unless the
section sets it, so a ``[environment NAME]`` directive that ``allowed_environments``
leaves out is reported (see :func:`disallowed_environments`). Every other markwright
default applies (embeds load eagerly, for one). The pymdownx and standard extensions
below load after markwright's, which keeps ``markwright.fence`` ahead of
``pymdownx.superfences``.
"""

from __future__ import annotations

import importlib
import logging
import warnings
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import TYPE_CHECKING, Any

import markdown
from markwright import ConfigWarning, extension_configs, selected_extensions

# The fence scanner is the one markwright's own fence pre stage walks blocks with; it is
# defined in markwright._fences and not re-exported, so it is imported from there.
from markwright._fences import find_fenced_blocks
from markwright.fence import ENVIRONMENT_RE, LABEL_RE, SECONDARY_LABEL_RE, read_options

from bartleby.config import ConfigError, markwright_config

if TYPE_CHECKING:
    from bartleby.config import BartlebyConfig

_LOGGER = logging.getLogger("bartleby")

_BUNDLED_EXTENSIONS: tuple[str, ...] = (
    # pymdownx
    "pymdownx.superfences",
    "pymdownx.highlight",
    "pymdownx.inlinehilite",
    "pymdownx.tabbed",
    "pymdownx.details",
    "pymdownx.tasklist",
    "pymdownx.arithmatex",
    "pymdownx.keys",
    "pymdownx.mark",
    "pymdownx.caret",
    "pymdownx.tilde",
    "pymdownx.critic",
    "pymdownx.smartsymbols",
    "pymdownx.emoji",
    "pymdownx.snippets",
    "pymdownx.blocks.caption",
    # Standard Python-Markdown extensions
    "tables",
    "toc",
    "attr_list",
    "def_list",
    "footnotes",
    "admonition",
    "abbr",
    "md_in_html",
)

# Options Bartleby sets on its own bundled pymdownx extensions. A ``markdown_extensions``
# override for one of these merges over its entry, so an unrelated key keeps the rest.
# The alternate tab style emits the .tabbed-labels row both bundled themes style; the
# legacy markup has no row. Generic math emits ``\(...\)`` and ``\[...\]`` inside
# ``.arithmatex`` elements, which MathJax 3 and KaTeX's auto-render script both read; the
# default emits MathJax 2 ``<script type="math/tex">`` blocks that neither one typesets.
# Emoji are the characters themselves (``to_alt`` on the twemoji index), so a page makes
# no request to an emoji CDN; ``to_svg`` or ``to_png`` opts a site into images.
_BUNDLED_EXTENSION_CONFIGS: dict[str, dict[str, object]] = {
    "pymdownx.tabbed": {"alternate_style": True},
    "pymdownx.arithmatex": {"generic": True},
    "pymdownx.emoji": {
        "emoji_index": "pymdownx.emoji.twemoji",
        "emoji_generator": "pymdownx.emoji.to_alt",
    },
}

# pymdownx.emoji takes callables for these two keys; bartleby.yml can only hold a string,
# so a string (the bundled defaults included) is a dotted path resolved to the callable
# before the renderer builds.
_EMOJI_CALLABLE_KEYS = ("emoji_index", "emoji_generator")


@dataclass(slots=True)
class RenderedContent:
    """The result of rendering markdown to HTML."""

    html: str
    toc_tokens: list[dict[str, object]] = field(default_factory=list)


def create_markdown_renderer(config: BartlebyConfig) -> markdown.Markdown:
    """Build a ``markdown.Markdown`` instance with Bartleby's default extensions.

    :param config: Parsed Bartleby config. ``config.markwright`` selects and configures the
        markwright extensions; per-extension overrides from ``config.markdown_extensions``
        are merged with the other defaults: the override's name replaces the
        default-list string entry, and any ``config`` mapping is merged over the bundled
        options for that extension (override keys win) and passed as
        ``extension_configs``. A string ``emoji_index`` or ``emoji_generator`` under
        ``pymdownx.emoji`` is a dotted path to the callable.
    :returns: A configured :class:`markdown.Markdown` instance.
    :raises ConfigError: When markwright rejects a ``markwright:`` section built by hand,
        or an emoji dotted path names nothing.
    :raises ImportError: When a required extension cannot be loaded; the
        error message names the offending extension.
    """
    # markwright reports no-op or contradictory options as ConfigWarning, from option
    # validation, from selection, and again at extension init; collect them all so each
    # distinct message reaches the bartleby log once instead of a raw Python warning.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConfigWarning)
        # markwright's extensions go first so markwright.fence precedes pymdownx.superfences
        markwright_names, markwright_configs = _markwright_extensions(config.markwright)
        extensions: list[str] = [*markwright_names, *_BUNDLED_EXTENSIONS]
        configs: dict[str, dict[str, object]] = {
            **_BUNDLED_EXTENSION_CONFIGS,
            **markwright_configs,
        }
        for name, override_config in _index_overrides(config.markdown_extensions).items():
            if name not in extensions:
                extensions.append(name)
            if override_config:
                configs[name] = {**configs.get(name, {}), **override_config}
        if "pymdownx.emoji" in configs:
            configs["pymdownx.emoji"] = _resolve_emoji_callables(configs["pymdownx.emoji"])

        try:
            renderer = markdown.Markdown(
                extensions=extensions,
                extension_configs=configs,
                output_format="html",
            )
        except (ImportError, ModuleNotFoundError) as exc:
            raise ImportError(f"Failed to load a configured markdown extension: {exc}") from exc

    logged: set[str] = set()
    for warning in caught:
        if not issubclass(warning.category, ConfigWarning):
            warnings.warn_explicit(
                warning.message, warning.category, warning.filename, warning.lineno
            )
            continue
        message = str(warning.message)
        if message not in logged:
            logged.add(message)
            _LOGGER.warning("%s", message)
    return renderer


def _markwright_extensions(
    section: dict[str, object],
) -> tuple[list[str], dict[str, dict[str, object]]]:
    """Resolve the ``markwright:`` section through markwright's public config API.

    :param section: The raw section, empty when ``bartleby.yml`` has none.
    :returns: The dotted extension names markwright selects, in its order, and the
        ``extension_configs`` entries for those with options.
    :raises ConfigError: When markwright rejects the section (``load_config`` has
        already checked it, so this fires only for a config built by hand).
    """
    resolved = markwright_config(section)
    names = selected_extensions(resolved)

    return [f"markwright.{name}" for name in names], extension_configs(resolved, names)


def _resolve_emoji_callables(options: dict[str, object]) -> dict[str, object]:
    """Resolve string ``emoji_index`` and ``emoji_generator`` options to their callables.

    :param options: The ``pymdownx.emoji`` options after overrides are merged.
    :returns: The options with each string under the two keys replaced by the object the
        dotted path names, such as ``pymdownx.emoji.to_svg``.
    :raises ConfigError: When a dotted path has no module part or names nothing.
    """
    resolved = dict(options)
    for key in _EMOJI_CALLABLE_KEYS:
        value = resolved.get(key)
        if not isinstance(value, str):
            continue
        module_name, _, attribute = value.rpartition(".")
        try:
            resolved[key] = getattr(importlib.import_module(module_name), attribute)
        except (ImportError, AttributeError, ValueError) as exc:
            raise ConfigError(
                f"{value!r} does not name a callable",
                key_path=f"markdown_extensions.pymdownx.emoji.{key}",
                hint="use a dotted path such as pymdownx.emoji.to_svg or pymdownx.emoji.twemoji",
            ) from exc
    return resolved


def fence_environment_limits(config: BartlebyConfig) -> list[str] | None:
    """The fence environments a site allows, when a directive outside them should be reported.

    :param config: Parsed Bartleby config.
    :returns: The ``markwright.fence.allowed_environments`` list, or ``None`` when every
        environment is allowed, ``markwright.fence`` is off, or ``markwright.warn`` is false.
    """
    resolved = markwright_config(config.markwright)
    with warnings.catch_warnings():
        # Selection and option ConfigWarnings are already logged when the renderer is built.
        warnings.simplefilter("ignore", ConfigWarning)
        if not resolved.warn or "fence" not in selected_extensions(resolved):
            return None
        return read_options(resolved.options.get("fence")).allowed_environments


def disallowed_environments(source: str, allowed: list[str] | None) -> list[str]:
    """The environment names a page's fence directives name outside ``allowed``.

    Walks the fenced blocks the way ``markwright.fence`` does: a directive counts only
    among the leading lines of a block, so a nested fence's source or a line of prose
    is not one. markwright leaves such a directive in the block as text, in silence.

    :param source: The page's Markdown source.
    :param allowed: The allowed environment names, or ``None`` to allow every one.
    :returns: Each disallowed name once, in order of first appearance.
    """
    if allowed is None:
        return []
    lines = source.split("\n")
    found: dict[str, None] = {}
    for block in find_fenced_blocks(lines):
        for line in lines[block.opening + 1 : block.closing]:
            stripped = line.strip()
            if LABEL_RE.match(stripped) or SECONDARY_LABEL_RE.match(stripped):
                continue
            environment_match = ENVIRONMENT_RE.match(stripped)
            if environment_match is None:
                break
            if environment_match.group(1) not in allowed:
                found[environment_match.group(1)] = None
    return list(found)


def render_markdown(source: str, renderer: markdown.Markdown) -> RenderedContent:
    """Render ``source`` to HTML and pull the TOC tokens off the renderer.

    :param source: Raw markdown content.
    :param renderer: Renderer built by :func:`create_markdown_renderer`.
    :returns: A :class:`RenderedContent` carrying the HTML and TOC tokens.
    """
    renderer.reset()
    html = renderer.convert(source)
    toc_tokens_raw: Any = getattr(renderer, "toc_tokens", [])
    toc_tokens: list[dict[str, object]] = (
        [dict(token) for token in toc_tokens_raw] if isinstance(toc_tokens_raw, list) else []
    )
    return RenderedContent(html=html, toc_tokens=toc_tokens)


class _TextCollector(HTMLParser):
    """Collect the text nodes of an HTML fragment."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self.chunks.append(data)


def html_to_plain_text(html: str) -> str:
    """Return the text of ``html`` with tags removed and whitespace collapsed.

    :param html: An HTML fragment, such as a rendered excerpt.
    :returns: Plain text on a single line, with entities decoded.
    """
    collector = _TextCollector()
    collector.feed(html)
    collector.close()
    # str.split() treats the non-breaking space from &nbsp; as whitespace too.
    return " ".join("".join(collector.chunks).split())


def _index_overrides(
    entries: list[dict[str, object] | str],
) -> dict[str, dict[str, object]]:
    """Normalise ``markdown_extensions`` config into ``{name: config_dict}``."""
    indexed: dict[str, dict[str, object]] = {}
    for entry in entries:
        if isinstance(entry, str):
            indexed[entry] = {}
            continue
        name_raw = entry.get("name")
        if not isinstance(name_raw, str):
            continue
        config_raw = entry.get("config")
        indexed[name_raw] = dict(config_raw) if isinstance(config_raw, dict) else {}
    return indexed
