# ABOUTME: Cross-reference resolution — rewrite .md links to output URLs.
# Catches broken cross-references at build time and points at the offending page.

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

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
    errors: list[CrossRefError] = []
    source_dir = current_page.source_path.parent

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
                    source_path=current_page.source_path.as_posix(),
                    target_path=path_part,
                    message=f"link target not found: {path_part}",
                )
            )
            return match.group(0)
        new_href = target.output_url + (f"#{anchor}" if anchor else "")
        return f'href="{new_href}"'

    new_html = _HREF_RE.sub(replace, html)
    return new_html, errors


def resolve_all_crossrefs(pages: list[Page], content_dir: Path) -> list[CrossRefError]:
    """Run :func:`resolve_page_crossrefs` across every page, updating each page in place."""
    errors: list[CrossRefError] = []
    for page in pages:
        if not page.rendered_content:
            continue
        new_html, page_errors = resolve_page_crossrefs(
            page.rendered_content, page, pages, content_dir
        )
        page.rendered_content = new_html
        errors.extend(page_errors)
    return errors


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
