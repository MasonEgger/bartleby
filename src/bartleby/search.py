# ABOUTME: Search index generation for client-side search with lunr.js.
# Produces a JSON index with one doc per page + one per heading-anchored section.

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from bartleby.config import BartlebyConfig
    from bartleby.content import Page


_HEADING_RE = re.compile(r'<h([1-6])(?:\s+[^>]*?id="([^"]+)")?[^>]*>(.*?)</h\1>', re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def build_search_index(pages: list[Page], config: BartlebyConfig) -> dict[str, object]:
    """Build the lunr.js-compatible search index for ``pages``.

    :param pages: All published pages whose HTML has been rendered.
    :param config: The parsed Bartleby config (currently used for the
        config block — language defaults to English).
    :returns: A dict with ``config`` and ``docs`` keys, JSON-serialisable.
    """
    del config  # not yet used — placeholder for future i18n-aware config
    docs: list[dict[str, object]] = []
    for page in pages:
        if page.draft:
            continue
        tags = page.taxonomy_values.get("tags", [])
        docs.append(
            {
                "location": page.output_url,
                "title": page.title,
                "text": _strip_html(page.rendered_content),
                "tags": list(tags),
            }
        )
        for anchor, heading_title, section_text in _split_sections(page.rendered_content):
            docs.append(
                {
                    "location": page.output_url + (f"#{anchor}" if anchor else ""),
                    "title": heading_title,
                    "text": section_text,
                    "tags": list(tags),
                }
            )
    return {
        "config": {
            "lang": ["en"],
            "separator": "[\\s\\-]+",
            "pipeline": ["stemmer"],
        },
        "docs": docs,
    }


def write_search_index(index: dict[str, object], output_dir: Path) -> None:
    """Write ``index`` to ``output_dir/search/search_index.json``."""
    target_dir = output_dir / "search"
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "search_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _split_sections(html: str) -> list[tuple[str, str, str]]:
    """Yield ``(anchor_id, heading_text, body_text)`` for each heading section in ``html``."""
    sections: list[tuple[str, str, str]] = []
    if not html:
        return sections
    headings = list(_HEADING_RE.finditer(html))
    for index, match in enumerate(headings):
        anchor = match.group(2) or ""
        heading_text = _strip_html(match.group(3)).strip()
        start = match.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(html)
        body_text = _strip_html(html[start:end]).strip()
        sections.append((anchor, heading_text, body_text))
    return sections


def _strip_html(html: str) -> str:
    """Strip every HTML tag and collapse whitespace."""
    return " ".join(_HTML_TAG_RE.sub(" ", html).split())
