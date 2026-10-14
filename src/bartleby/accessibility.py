# ABOUTME: Markdown extension that makes the rendered HTML accessible before any theme sees it.
# ABOUTME: Type markers on admonitions, details, and environment fences; labels on controls.

"""The accessibility pass of the Markdown pipeline.

Every theme and user theme renders the same HTML, so the cues that assistive technology
and color-blind readers need are added here rather than per theme:

- Each admonition title and ``details`` summary starts with an inline SVG from the base
  theme's Octicons (``aria-hidden``, class ``admonition-icon``) and, when the title is
  not the type word itself, a ``visually-hidden`` span reading ``Danger: ``. Both
  bundled themes tint by type; the icon and the hidden word carry the type without color.
- Each ``pre.environment-<name>`` starts with a ``visually-hidden`` span reading
  ``Environment <name>.``, before the code.
- Each task-list checkbox (pymdownx.tasklist) takes its item text as ``aria-label``;
  the extension emits a bare, disabled input with the text beside it. The input is
  stashed raw HTML, so the attribute is written into the stash entry the item's
  placeholder names.
- Each table takes ``tabindex="0"`` so it can be scrolled from the keyboard when the
  theme lets a wide table scroll inside its box.
- markwright's embeds get the attributes they ship without: a title on the YouTube
  iframe, a label on the image-compare slider, and keyboard focus on the slideshow's
  scroll container. These are a stopgap until markwright emits them.

Icons resolve through :func:`bartleby.icons.get_icon_path` with the active theme chain,
so a theme can override a glyph by shipping ``icons/octicons/<name>-16.svg``.
"""

from __future__ import annotations

import copy
import html
import re
from typing import TYPE_CHECKING
from xml.etree import ElementTree as etree

from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.treeprocessors import Treeprocessor
from markdown.util import HTML_PLACEHOLDER_RE

from bartleby.icons import DEFAULT_ICON_PACKS, get_icon_path

if TYPE_CHECKING:
    from pathlib import Path

    from markdown import Markdown

ICON_CLASS = "admonition-icon"
HIDDEN_CLASS = "visually-hidden"

#: Octicon per admonition type. A type outside this map gets ``FALLBACK_ICON``.
ADMONITION_ICONS: dict[str, str] = {
    "note": "info",
    "info": "info",
    "abstract": "book",
    "example": "book",
    "tip": "light-bulb",
    "success": "check-circle",
    "question": "question",
    "warning": "alert",
    "failure": "x-circle",
    "danger": "stop",
    "bug": "bug",
    "quote": "quote",
}
FALLBACK_ICON = "info"

# Block-level tags whose text is not part of a task item's own label.
_BLOCK_TAGS = frozenset({"ul", "ol", "p", "pre", "div", "blockquote", "table", "details"})

_ENVIRONMENT_PRE_RE = re.compile(r'(<pre class="[^"]*\benvironment-([a-z0-9_-]+)\b[^"]*"[^>]*>)')

# markwright embed tags, matched on the exact strings its templates print.
_EMBED_REPAIRS: tuple[tuple[str, str], ...] = (
    (
        '<iframe src="https://www.youtube.com/embed/',
        '<iframe title="YouTube video" src="https://www.youtube.com/embed/',
    ),
    (
        '<input type="range" class="control"',
        '<input type="range" class="control" aria-label="Image comparison position"',
    ),
    ('<div class="slides">', '<div class="slides" tabindex="0">'),
)


class AccessibilityMarkup(Extension):
    """Register the tree passes and the post passes.

    :param icons_dirs: The theme chain's ``icons/`` directories, leaf-first, or
        ``None`` for the default theme's.
    """

    def __init__(self, icons_dirs: list[Path] | None = None) -> None:
        super().__init__()
        self._icons_dirs = icons_dirs

    def extendMarkdown(self, md: Markdown) -> None:  # noqa: N802 (Python-Markdown's hook name)
        # After inline, attr_list, and toc have run (priorities 20, 8, and 5), before
        # unescape (0), so each block's own markup and attributes are already in place.
        md.treeprocessors.register(AdmonitionMarker(md, self._icons_dirs), "admonition-marker", 3)
        md.treeprocessors.register(ControlLabels(md), "control-labels", 3)
        # markwright's fence postprocessor places the finished block at 25; the
        # environment span and the embed attributes go in once the HTML is in the document.
        md.postprocessors.register(EnvironmentMarker(md), "environment-marker", 15)
        md.postprocessors.register(EmbedRepairs(md), "embed-repairs", 15)


class AdmonitionMarker(Treeprocessor):
    """Prepend the type icon and hidden type word to each admonition and details title."""

    def __init__(self, md: Markdown, icons_dirs: list[Path] | None) -> None:
        super().__init__(md)
        self._icons_dirs = icons_dirs
        self._icons: dict[str, etree.Element | None] = {}

    def run(self, root: etree.Element) -> None:
        for block in root.iter("div"):
            if "admonition" in _classes(block):
                self._mark(block, "p", "admonition-title")
        for block in root.iter("details"):
            self._mark(block, "summary", None)

    def _mark(self, block: etree.Element, title_tag: str, title_class: str | None) -> None:
        # The title is the block's first child; both extensions put it there.
        classes = [name for name in _classes(block) if name != "admonition"]
        if not classes or len(block) == 0:
            return
        title = block[0]
        untitled = title_class is not None and title_class not in _classes(title)
        if title.tag != title_tag or untitled:
            return

        # The hidden type word is needed only when the title does not say it already.
        type_name = classes[0]
        heard = type_name.capitalize()
        original_text = title.text
        markers = [self._icon_for(type_name)]
        if (original_text or "").strip() != heard or len(title) > 0:
            hidden = etree.Element("span", {"class": HIDDEN_CLASS})
            hidden.text = f"{heard}: "
            markers.append(hidden)
        inserted = [marker for marker in markers if marker is not None]
        if not inserted:
            return

        # The title's own text moves behind the markers, as the tail of the last one.
        for position, marker in enumerate(inserted):
            title.insert(position, marker)
        inserted[-1].tail = original_text
        title.text = None

    def _icon_for(self, type_name: str) -> etree.Element | None:
        name = ADMONITION_ICONS.get(type_name, FALLBACK_ICON)
        if name not in self._icons:
            self._icons[name] = _load_icon(name, self._icons_dirs)
        icon = self._icons[name]
        return None if icon is None else copy.deepcopy(icon)


class ControlLabels(Treeprocessor):
    """Name each task-list checkbox after its item and make each table focusable."""

    def run(self, root: etree.Element) -> None:
        for item in root.iter("li"):
            if "task-list-item" in _classes(item):
                self._label_checkbox(item)
        for table in root.iter("table"):
            if table.get("tabindex") is None:
                table.set("tabindex", "0")

    def _label_checkbox(self, item: etree.Element) -> None:
        # In a loose list the checkbox and text sit in the item's first paragraph.
        holder = item[0] if len(item) > 0 and item[0].tag == "p" else item
        placeholder = HTML_PLACEHOLDER_RE.match(holder.text or "")
        if placeholder is None:
            return
        stash = self.md.htmlStash.rawHtmlBlocks
        index = int(placeholder.group(1))
        checkbox = stash[index]
        if not isinstance(checkbox, str) or "aria-label" in checkbox:
            return
        label = html.escape(_item_label(holder, placeholder.end()), quote=True)
        stash[index] = checkbox.replace(
            '<input type="checkbox"', f'<input type="checkbox" aria-label="{label}"', 1
        )


class EnvironmentMarker(Postprocessor):
    """Name the environment in hidden text at the top of each ``pre.environment-*``.

    The fence is a string by the time it reaches the document (superfences stashes it
    and places it after the tree is serialized), so the span goes in by substitution
    on the opening ``pre`` tag; nothing is parsed.
    """

    def run(self, text: str) -> str:
        return _ENVIRONMENT_PRE_RE.sub(
            lambda match: (
                f'{match.group(1)}<span class="{HIDDEN_CLASS}">'
                f"Environment {match.group(2)}. </span>"
            ),
            text,
        )


class EmbedRepairs(Postprocessor):
    """Add the attributes markwright's embed markup leaves out.

    markwright stashes each embed as a string, so the fixes are plain substitutions on
    the tags it prints. They go away once markwright emits the attributes itself.
    """

    def run(self, text: str) -> str:
        for printed, repaired in _EMBED_REPAIRS:
            text = text.replace(printed, repaired)
        return text


def _classes(element: etree.Element) -> list[str]:
    return element.get("class", "").split()


def _item_label(holder: etree.Element, start: int) -> str:
    """The text of a task item after its checkbox, up to the first nested block."""
    pieces: list[str] = [(holder.text or "")[start:]]
    for child in holder:
        if child.tag in _BLOCK_TAGS:
            break
        pieces.append("".join(child.itertext()))
        pieces.append(child.tail or "")
    return " ".join("".join(pieces).split())


def _load_icon(name: str, icons_dirs: list[Path] | None) -> etree.Element | None:
    """The Octicon ``name`` as an inline element, or ``None`` when no chain ships it."""
    icon_name = f"octicons-{name}-16"
    path = get_icon_path(icon_name, DEFAULT_ICON_PACKS, icons_dirs)
    if path is None and icons_dirs is not None:
        # A chain that does not extend base has no Octicons; the bundled set still applies.
        path = get_icon_path(icon_name, DEFAULT_ICON_PACKS, None)
    if path is None:
        return None
    svg = _without_namespace(etree.fromstring(path.read_text(encoding="utf-8")))
    for sized in ("width", "height"):
        svg.attrib.pop(sized, None)
    svg.set("class", ICON_CLASS)
    svg.set("aria-hidden", "true")
    svg.set("focusable", "false")
    return svg


def _without_namespace(element: etree.Element) -> etree.Element:
    """A copy of ``element`` with the SVG namespace dropped from every tag."""
    plain = etree.Element(element.tag.rpartition("}")[2], dict(element.attrib))
    plain.text = element.text
    plain.tail = element.tail
    for child in element:
        plain.append(_without_namespace(child))
    return plain
