# ABOUTME: Cross-reference resolution — rewrite .md links to output URLs.
# Catches broken cross-references at build time and points at the offending page.

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bartleby.content import Page


_HREF_RE = re.compile(r'href="([^"]+)"')


@dataclass(slots=True)
class CrossRefError:
    """One unresolved cross-reference encountered during HTML rewriting."""

    source_path: str
    target_path: str
    message: str


def resolve_page_crossrefs(
    html: str,
    current_page: Page,
    all_pages: list[Page],
    content_dir: Path,
) -> tuple[str, list[CrossRefError]]:
    """Rewrite ``.md`` hrefs in ``html`` to the target page's output URL.

    :param html: The rendered HTML to scan.
    :param current_page: The page being rendered (used for relative-path resolution).
    :param all_pages: All known content pages (used to look up targets).
    :param content_dir: The site's ``content/`` directory.
    :returns: ``(rewritten_html, errors)`` — the modified HTML and any
        :class:`CrossRefError` for unresolved targets.
    """
    del content_dir  # path resolution works in terms of source_path; kept for parity
    pages_by_source = {page.source_path.as_posix(): page for page in all_pages}
    return _rewrite_hrefs(html, current_page.source_path, pages_by_source)


def resolve_all_crossrefs(pages: list[Page], content_dir: Path) -> list[CrossRefError]:
    """Run the cross-reference rewrite across every page, updating each page in place.

    Three kinds of HTML are rewritten: a page's body, its rendered excerpt, and a
    listing page's intro (the ``intro_content`` of ``content/{type}/index.md``).
    An excerpt is part of its page's body, so its broken links are reported once,
    from the body.
    """
    del content_dir  # path resolution works in terms of source_path; kept for parity
    pages_by_source = {page.source_path.as_posix(): page for page in pages}
    errors: list[CrossRefError] = []
    for page in pages:
        if page.rendered_content:
            page.rendered_content, page_errors = _rewrite_hrefs(
                page.rendered_content, page.source_path, pages_by_source
            )
            errors.extend(page_errors)
        if page.excerpt_html:
            page.excerpt_html, _body_reports_these = _rewrite_hrefs(
                page.excerpt_html, page.source_path, pages_by_source
            )
        intro_content = page.custom_metadata.get("intro_content")
        if isinstance(intro_content, str) and intro_content and page.content_type_name:
            # A listing page's own source path is a generated sentinel; the intro's
            # links are relative to the real file, content/{type}/index.md.
            intro_source = Path(page.content_type_name) / "index.md"
            page.custom_metadata["intro_content"], intro_errors = _rewrite_hrefs(
                intro_content, intro_source, pages_by_source
            )
            errors.extend(intro_errors)
    return errors


def _rewrite_hrefs(
    html: str, source_path: Path, pages_by_source: dict[str, Page]
) -> tuple[str, list[CrossRefError]]:
    """Rewrite ``.md`` hrefs in ``html`` as links written in the file at ``source_path``."""
    errors: list[CrossRefError] = []
    source_dir = source_path.parent

    def replace(match: re.Match[str]) -> str:
        href = match.group(1)
        if _is_external_or_anchor(href):
            return match.group(0)
        path_part, _separator, anchor = href.partition("#")
        if not path_part.endswith(".md"):
            return match.group(0)
        resolved_source = _resolve_relative(source_dir, path_part)
        target = pages_by_source.get(resolved_source)
        if target is None:
            errors.append(
                CrossRefError(
                    source_path=source_path.as_posix(),
                    target_path=path_part,
                    message=f"link target not found: {path_part}",
                )
            )
            return match.group(0)
        new_href = target.output_url + (f"#{anchor}" if anchor else "")
        return f'href="{new_href}"'

    return _HREF_RE.sub(replace, html), errors


def _is_external_or_anchor(href: str) -> bool:
    """True for absolute URLs, scheme-relative URLs, and bare anchor links."""
    if href.startswith("#"):
        return True
    if href.startswith("//"):
        return True
    if "://" in href:
        return True
    return href.startswith("mailto:") or href.startswith("tel:")


def _resolve_relative(source_dir: object, path_part: str) -> str:
    """Resolve a relative ``.md`` path against ``source_dir`` using POSIX semantics."""
    from pathlib import PurePosixPath

    base_str = source_dir.as_posix() if hasattr(source_dir, "as_posix") else str(source_dir)
    base = PurePosixPath(base_str)
    target = (base / path_part).as_posix()
    parts: list[str] = []
    for segment in target.split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            if parts:
                parts.pop()
            continue
        parts.append(segment)
    return "/".join(parts)
