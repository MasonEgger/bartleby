# ABOUTME: Markdown rendering pipeline with all default extensions configured.
# Wires markwright, pymdownx, and standard extensions into Python-Markdown.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import markdown

if TYPE_CHECKING:
    from bartleby.config import BartlebyConfig


_DEFAULT_EXTENSIONS: tuple[str, ...] = (
    # markwright — fence must load before superfences so its preprocessor
    # (priority 40) extracts directives before superfences's preprocessor
    # (priority 25) processes the fenced block.
    "markwright.fence",
    "markwright.highlight",
    "markwright.youtube",
    "markwright.codepen",
    "markwright.twitter",
    "markwright.instagram",
    "markwright.slideshow",
    "markwright.image_compare",
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


@dataclass(slots=True)
class RenderedContent:
    """The result of rendering markdown to HTML."""

    html: str
    toc_tokens: list[dict[str, object]] = field(default_factory=list)


def create_markdown_renderer(config: BartlebyConfig) -> markdown.Markdown:
    """Build a ``markdown.Markdown`` instance with Bartleby's default extensions.

    :param config: Parsed Bartleby config. Per-extension overrides from
        ``config.markdown_extensions`` are merged with the defaults — the
        override's name replaces the default-list string entry, and any
        ``config`` mapping is passed through as ``extension_configs``.
    :returns: A configured :class:`markdown.Markdown` instance.
    :raises ImportError: When a required extension cannot be loaded; the
        error message names the offending extension.
    """
    overrides = _index_overrides(config.markdown_extensions)
    extensions: list[str] = list(_DEFAULT_EXTENSIONS)
    extension_configs: dict[str, dict[str, object]] = {}
    for name, override_config in overrides.items():
        if name not in extensions:
            extensions.append(name)
        if override_config:
            extension_configs[name] = override_config

    try:
        return markdown.Markdown(
            extensions=extensions,
            extension_configs=extension_configs,
            output_format="html",
        )
    except (ImportError, ModuleNotFoundError) as exc:
        raise ImportError(f"Failed to load a configured markdown extension: {exc}") from exc


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
