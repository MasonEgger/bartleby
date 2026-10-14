# ABOUTME: The accessibility rules behind `bartleby lint`, run over each page's rendered body.
# ABOUTME: Alt text, heading order, link names, ids, table headers, iframe titles, site.language.

"""Accessibility checks on the HTML the Markdown pipeline renders for each page.

The bundled themes and the pipeline's own markup pass an axe-core audit, so what is
left is what an author writes: an image with no alt text, a heading that jumps two
levels, a link that says "here". Each rule in :data:`ACCESSIBILITY_RULES` has a stable
id, a severity, a one-line description, and the fix the finding prints, so the CLI,
the docs, and the generated skills read one table.

Pages are parsed with :mod:`html.parser` into a small element tree; the pipeline's
HTML is well formed, so no error recovery is needed. A finding's line is the first
line of the page's Markdown source that holds a distinctive piece of the element (the
image's file name, the heading's text, the link's target), counted from the top of the
file, or ``0`` when the source holds no such text.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bartleby.config import BartlebyConfig
    from bartleby.content import Page
    from bartleby.linting import Finding


@dataclass(frozen=True, slots=True)
class Rule:
    """One lint rule as the docs, the CLI, and the generated skills describe it.

    :ivar id: The stable kebab-case rule id that findings and ``--rules`` use.
    :ivar severity: ``"error"`` (fails the command) or ``"warning"``.
    :ivar description: One sentence saying what the rule reports.
    :ivar hint: The fix every finding of this rule prints.
    """

    id: str
    severity: str
    description: str
    hint: str

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "severity": self.severity,
            "description": self.description,
            "hint": self.hint,
        }


ACCESSIBILITY_RULES: tuple[Rule, ...] = (
    Rule(
        "image-missing-alt",
        "error",
        "An image has no alt attribute.",
        'write alt text that says what the image shows, or alt="" for a decorative image',
    ),
    Rule(
        "image-alt-is-filename",
        "warning",
        'An image\'s alt text is its file name or a bare word such as "image" or "screenshot".',
        "describe what the image shows in the alt text, as a reader who cannot see it needs",
    ),
    Rule(
        "heading-level-skip",
        "warning",
        "A heading is more than one level below the one before it, counted from the title (h1).",
        "use the next heading level down; a page body starts at ## because the title is the h1",
    ),
    Rule(
        "heading-empty",
        "error",
        "A heading has no text.",
        "give the heading text, or remove it",
    ),
    Rule(
        "link-empty",
        "error",
        "A link has no text, no aria-label, and no image with alt text inside it.",
        "put text inside the link, or give it an aria-label",
    ),
    Rule(
        "link-generic-text",
        "warning",
        'A link\'s text is only a stock phrase such as "here", "click here", or "read more".',
        "make the link text name its target, such as [the configuration reference](...)",
    ),
    Rule(
        "link-raw-url-text",
        "warning",
        "A link's text is a URL longer than 40 characters.",
        "give the link a name: [Name](https://...) instead of the bare URL",
    ),
    Rule(
        "duplicate-id",
        "error",
        "The same id appears more than once on a page, so its anchor reaches only the first.",
        "rename one of the ids; for repeated headings, change one heading's text",
    ),
    Rule(
        "table-missing-header",
        "warning",
        "A table has no thead and no th cells in its first row.",
        "give the table a header row; in Markdown, the first row is the header",
    ),
    Rule(
        "iframe-missing-title",
        "error",
        "An iframe has no title attribute.",
        'add title="..." saying what the frame shows, such as the video or map name',
    ),
    Rule(
        "emphasis-as-heading",
        "warning",
        "A paragraph is only a short bold or italic run followed by a list or paragraph.",
        "use a heading (## Text) instead of bold text to title a section",
    ),
    Rule(
        "language-invalid",
        "error",
        "site.language is not a BCP 47 language tag.",
        'set site.language in bartleby.yml to a tag such as "en", "de-AT", or "pt-BR"',
    ),
)

_RULES_BY_ID = {rule.id: rule for rule in ACCESSIBILITY_RULES}

_LANGUAGE_TAG_RE = re.compile(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*")
_HEADING_TAG_RE = re.compile(r"h[1-6]")
_IMAGE_SUFFIXES = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".avif",
    ".bmp",
    ".ico",
    ".tiff",
)
_BARE_ALT_WORDS = frozenset({"image", "photo", "picture", "screenshot"})
_GENERIC_LINK_TEXT = frozenset(
    {"here", "click here", "link", "this", "read more", "more", "learn more"}
)
_RAW_URL_MIN_LENGTH = 40
_EMPHASIS_MAX_LENGTH = 80
_EMPHASIS_FOLLOWERS = frozenset({"p", "ul", "ol"})
_VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)


# Identity equality: the parent and children links would otherwise compare recursively.
@dataclass(slots=True, eq=False)
class _Element:
    """One element of a page: its tag, attributes, parent, and children in order."""

    tag: str
    attrs: dict[str, str | None]
    parent: _Element | None = None
    children: list[_Element | str] = field(default_factory=list)

    def text(self) -> str:
        """Every piece of text under this element, joined, with whitespace collapsed."""
        pieces = [child if isinstance(child, str) else child.text() for child in self.children]
        return " ".join("".join(pieces).split())

    def elements(self) -> Iterator[_Element]:
        """Every descendant element in document order."""
        for child in self.children:
            if isinstance(child, _Element):
                yield child
                yield from child.elements()

    def child_elements(self) -> list[_Element]:
        return [child for child in self.children if isinstance(child, _Element)]

    def find(self, tag: str) -> _Element | None:
        """The first descendant with ``tag``, or ``None``."""
        return next((element for element in self.elements() if element.tag == tag), None)

    def next_sibling(self) -> _Element | None:
        """The element after this one under the same parent, or ``None``."""
        if self.parent is None:
            return None
        siblings = self.parent.child_elements()
        position = siblings.index(self)
        return siblings[position + 1] if position + 1 < len(siblings) else None


class _TreeBuilder(HTMLParser):
    """Build an :class:`_Element` tree from well-formed HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Element("body", {})
        self._open = self.root

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = _Element(tag, dict(attrs), parent=self._open)
        self._open.children.append(element)
        if tag not in _VOID_TAGS:
            self._open = element

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # ``<img />`` opens nothing, so the default start-then-end pair is not wanted.
        self.handle_starttag(tag, attrs)
        if tag not in _VOID_TAGS:
            self._open = self._open.parent or self.root

    def handle_endtag(self, tag: str) -> None:
        # Close back to the matching open element; a stray end tag closes nothing.
        element: _Element | None = self._open
        while element is not None and element.tag != tag:
            element = element.parent
        if element is not None and element.parent is not None:
            self._open = element.parent

    def handle_data(self, data: str) -> None:
        self._open.children.append(data)


def _parse(html: str) -> _Element:
    builder = _TreeBuilder()
    builder.feed(html)
    builder.close()
    return builder.root


def lint_accessibility(pages: list[Page], config: BartlebyConfig) -> list[Finding]:
    """Run every accessibility rule and return the findings, page by page.

    :param pages: The published pages, each with ``rendered_content`` filled.
    :param config: The site configuration; ``site.language`` is checked once.
    :returns: Every :class:`~bartleby.linting.Finding`, the language check first.
    """
    findings = list(_lint_language(config))
    for page in pages:
        if not page.rendered_content:
            continue
        source = _Source(page)
        root = _parse(page.rendered_content)
        page_findings = [
            *_lint_images(root, source),
            *_lint_headings(root, source),
            *_lint_links(root, source),
            *_lint_ids(root, source),
            *_lint_tables(root, source),
            *_lint_iframes(root, source),
            *_lint_emphasis(root, source),
        ]
        # Findings read top to bottom of the source; an unlocated one (line 0) leads.
        findings += sorted(page_findings, key=lambda finding: finding.line)
    return findings


class _Source:
    """A page's Markdown source, for mapping an element back to a file line."""

    def __init__(self, page: Page) -> None:
        self.file = page.source_path.as_posix()
        self._lines = page.raw_content.splitlines()
        self._offset = _front_matter_lines(page)

    def line_of(self, *needles: str) -> int:
        """The file line of the first source line holding any needle, in needle order."""
        for needle in needles:
            if not needle:
                continue
            for number, line in enumerate(self._lines, 1):
                if needle in line:
                    return number + self._offset
        return 0

    def finding(self, rule_id: str, message: str, *needles: str) -> Finding:
        return _finding(rule_id, self.file, message, self.line_of(*needles))


def _finding(rule_id: str, file: str, message: str, line: int) -> Finding:
    """A finding of ``rule_id`` with the rule's severity and hint filled in."""
    # linting imports this module for the rule table, so Finding is imported on use.
    from bartleby.linting import Finding

    rule = _RULES_BY_ID[rule_id]
    return Finding(
        severity=rule.severity, rule=rule.id, file=file, message=message, line=line, hint=rule.hint
    )


def _front_matter_lines(page: Page) -> int:
    """How many lines of the file sit above the body, so body lines map to file lines."""
    if page.raw_content and page.abs_source_path.is_file():
        text = page.abs_source_path.read_text(encoding="utf-8")
        if text.endswith(page.raw_content):
            return text[: len(text) - len(page.raw_content)].count("\n")
    return 0


def _lint_language(config: BartlebyConfig) -> Iterator[Finding]:
    language = config.site.language
    if _LANGUAGE_TAG_RE.fullmatch(language) is None:
        yield _finding(
            "language-invalid",
            "bartleby.yml",
            f"site.language {language!r} is not a BCP 47 language tag",
            0,
        )


def _lint_images(root: _Element, source: _Source) -> Iterator[Finding]:
    for image in root.elements():
        if image.tag != "img":
            continue
        src = image.attrs.get("src") or ""
        name = src.rsplit("/", 1)[-1]
        alt = image.attrs.get("alt")
        if alt is None:
            yield source.finding(
                "image-missing-alt", f"<img src={src!r}> has no alt attribute", name, "<img"
            )
        elif _alt_is_filename(alt, name):
            yield source.finding(
                "image-alt-is-filename",
                f"<img src={src!r}> has alt text {alt.strip()!r}, which does not describe it",
                alt.strip(),
                name,
            )


def _alt_is_filename(alt: str, file_name: str) -> bool:
    text = alt.strip()
    lowered = text.lower()
    stem = file_name.rsplit(".", 1)[0]
    return (
        lowered in _BARE_ALT_WORDS
        or lowered.endswith(_IMAGE_SUFFIXES)
        or text in {file_name, stem}
    )


def _lint_headings(root: _Element, source: _Source) -> Iterator[Finding]:
    # The theme renders the page title as the h1, so the body is measured from level 1.
    previous = 1
    for heading in root.elements():
        if _HEADING_TAG_RE.fullmatch(heading.tag) is None:
            continue
        level = int(heading.tag[1])
        text = heading.text()
        if not text:
            yield source.finding(
                "heading-empty", f"<{heading.tag}> has no text", f"<{heading.tag}"
            )
        elif level > previous + 1:
            yield source.finding(
                "heading-level-skip",
                f"<{heading.tag}> {text!r} follows an h{previous}, skipping h{previous + 1}",
                text,
            )
        previous = level


def _lint_links(root: _Element, source: _Source) -> Iterator[Finding]:
    for link in root.elements():
        if link.tag != "a" or link.attrs.get("href") is None:
            continue
        href = link.attrs["href"] or ""
        text = link.text()
        if not text and not link.attrs.get("aria-label") and not _has_named_image(link):
            yield source.finding("link-empty", f"<a href={href!r}> has no text", href)
        elif _is_generic(text):
            yield source.finding(
                "link-generic-text",
                f"<a href={href!r}> reads only {text!r}",
                f"[{text}]",
                href,
            )
        elif text.startswith(("http://", "https://")) and len(text) > _RAW_URL_MIN_LENGTH:
            yield source.finding(
                "link-raw-url-text", f"<a href={href!r}> reads as the URL {text!r}", text, href
            )


def _has_named_image(link: _Element) -> bool:
    return any(
        element.tag == "img" and (element.attrs.get("alt") or "").strip()
        for element in link.elements()
    )


def _is_generic(text: str) -> bool:
    return text.strip(" .,:;!?()[]\"'").lower() in _GENERIC_LINK_TEXT


def _lint_ids(root: _Element, source: _Source) -> Iterator[Finding]:
    holders: defaultdict[str, list[_Element]] = defaultdict(list)
    for element in root.elements():
        if element.attrs.get("id"):
            holders[element.attrs["id"] or ""].append(element)
    for element_id, elements in holders.items():
        if len(elements) < 2:
            continue
        first = elements[0]
        if all(_HEADING_TAG_RE.fullmatch(element.tag) for element in elements):
            message = (
                f"heading {first.text()!r} repeats, so its anchor #{element_id} is used"
                f" {len(elements)} times"
            )
        else:
            tags = ", ".join(f"<{element.tag}>" for element in elements)
            message = f"id {element_id!r} is used {len(elements)} times ({tags})"
        yield source.finding("duplicate-id", message, f'id="{element_id}"', first.text())


def _lint_tables(root: _Element, source: _Source) -> Iterator[Finding]:
    for table in root.elements():
        if table.tag != "table" or table.find("thead") is not None:
            continue
        first_row = table.find("tr")
        if first_row is None or any(cell.tag == "th" for cell in first_row.child_elements()):
            continue
        first_cells = " | ".join(cell.text() for cell in first_row.child_elements())
        yield source.finding(
            "table-missing-header",
            f"<table> whose first row is {first_cells[:40]!r} has no header row",
            "<table",
            first_row.text()[:40],
        )


def _lint_iframes(root: _Element, source: _Source) -> Iterator[Finding]:
    for frame in root.elements():
        if frame.tag == "iframe" and not (frame.attrs.get("title") or "").strip():
            src = frame.attrs.get("src") or ""
            yield source.finding(
                "iframe-missing-title", f"<iframe src={src!r}> has no title", src, "<iframe"
            )


def _lint_emphasis(root: _Element, source: _Source) -> Iterator[Finding]:
    for paragraph in root.elements():
        if paragraph.tag != "p":
            continue
        runs = paragraph.child_elements()
        own_text = "".join(child for child in paragraph.children if isinstance(child, str))
        if len(runs) != 1 or runs[0].tag not in {"strong", "em"} or own_text.strip():
            continue
        text = runs[0].text()
        follower = paragraph.next_sibling()
        if (
            len(text) < _EMPHASIS_MAX_LENGTH
            and follower is not None
            and follower.tag in _EMPHASIS_FOLLOWERS
        ):
            yield source.finding(
                "emphasis-as-heading",
                f"paragraph {text!r} is only bold or italic text before a {follower.tag}",
                text,
            )
