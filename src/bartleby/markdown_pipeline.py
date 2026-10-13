# ABOUTME: Markdown rendering pipeline with all default extensions configured.
# Wires markwright, pymdownx, and standard extensions into Python-Markdown.

"""The Markdown rendering pipeline.

The markwright extensions and their options come from markwright's public config API,
driven by the ``markwright:`` section of ``bartleby.yml``: the section goes to
``config_from_mapping`` as written, ``selected_extensions`` names what loads, and
``extension_configs`` supplies the options. Bartleby never reimplements markwright's
schema and sets no markwright option, so markwright's own defaults apply (embeds load
eagerly, for one). The pymdownx and standard extensions below load after markwright's,
which keeps ``markwright.fence`` ahead of ``pymdownx.superfences``.
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import TYPE_CHECKING, Any

import markdown
from markwright import ConfigWarning, extension_configs, selected_extensions

from bartleby.config import markwright_config

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

# Options Bartleby sets on its own bundled pymdownx extensions. The alternate tab style
# emits the .tabbed-labels row both bundled themes style; the legacy markup has no row.
_BUNDLED_EXTENSION_CONFIGS: dict[str, dict[str, object]] = {
    "pymdownx.tabbed": {"alternate_style": True},
}


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
        default-list string entry, and any ``config`` mapping is passed through as
        ``extension_configs``.
    :returns: A configured :class:`markdown.Markdown` instance.
    :raises ConfigError: When markwright rejects a ``markwright:`` section built by hand.
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
                configs[name] = override_config

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
