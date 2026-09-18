# ABOUTME: Content quality linting — broken links, missing descriptions, orphans.
# Backs `bartleby lint`; reuses the crossref resolver for broken-link detection.

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.error import URLError
from urllib.request import Request, urlopen

from bartleby.crossrefs import resolve_page_crossrefs

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from bartleby.config import BartlebyConfig
    from bartleby.content import Page


# Severity levels used in findings, matching the spec's lint summary buckets.
_SEVERITY_ERROR = "error"
_SEVERITY_WARNING = "warning"

# Pull every href out of rendered HTML so we can map inbound links and external URLs.
_HREF_RE = re.compile(r'href="([^"]+)"')


@dataclass(slots=True)
class Finding:
    """One content-quality issue reported by :func:`lint_site`.

    :ivar severity: ``"error"``, ``"warning"``, or ``"info"``.
    :ivar rule: Stable machine-readable rule name (e.g. ``"orphaned-page"``).
    :ivar file: Source path of the offending page.
    :ivar message: Human-readable description of the issue.
    :ivar line: Line number when known; ``0`` when not applicable.
    :ivar fixable: Whether ``--fix`` can resolve this issue automatically.
    """

    severity: str
    rule: str
    file: str
    message: str
    line: int = 0
    fixable: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "rule": self.rule,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "fixable": self.fixable,
        }


def lint_site(
    pages: list[Page],
    config: BartlebyConfig,
    content_dir: Path,
    *,
    check_external: bool = False,
    external_checker: Callable[[str], bool] | None = None,
) -> list[Finding]:
    """Run content-quality checks across ``pages`` and return structured findings.

    Checks performed: broken internal cross-references, missing page
    descriptions, and orphaned pages (not in navigation and with no inbound
    links). External-link checking is opt-in via ``check_external`` and is off
    by default so a plain ``lint`` never touches the network.

    :param pages: Discovered content pages, with ``rendered_content`` populated.
    :param config: The loaded site configuration (used to resolve navigation).
    :param content_dir: The site's ``content/`` directory.
    :param check_external: When ``True``, external links are verified.
    :param external_checker: Predicate returning ``True`` for a reachable URL;
        defaults to :func:`check_external_url`. Only consulted when
        ``check_external`` is ``True``.
    :returns: Every :class:`Finding`, broken-link errors first.
    """
    findings: list[Finding] = []
    findings.extend(_lint_crossrefs(pages, content_dir))
    findings.extend(_lint_descriptions(pages))
    findings.extend(_lint_orphans(pages, config))
    if check_external:
        checker = external_checker if external_checker is not None else check_external_url
        findings.extend(_lint_external(pages, checker))
    return findings


def _lint_crossrefs(pages: list[Page], content_dir: Path) -> list[Finding]:
    """Report unresolved ``.md`` cross-references via the crossref resolver."""
    findings: list[Finding] = []
    for page in pages:
        if not page.rendered_content:
            continue
        _new_html, errors = resolve_page_crossrefs(page.rendered_content, page, pages, content_dir)
        for error in errors:
            findings.append(
                Finding(
                    severity=_SEVERITY_ERROR,
                    rule="broken-crossref",
                    file=error.source_path,
                    message=error.message,
                )
            )
    return findings


def _lint_descriptions(pages: list[Page]) -> list[Finding]:
    """Report content pages whose description front matter is empty or absent."""
    findings: list[Finding] = []
    for page in pages:
        if not page.description:
            findings.append(
                Finding(
                    severity=_SEVERITY_WARNING,
                    rule="missing-description",
                    file=page.source_path.as_posix(),
                    message="Page has no description; set one for search and previews",
                )
            )
    return findings


def _lint_orphans(pages: list[Page], config: BartlebyConfig) -> list[Finding]:
    """Report pages that are neither in navigation nor linked from any other page."""
    from bartleby.navigation import build_navigation

    nav = build_navigation(config, pages)
    nav_urls = {page.output_url for page in nav.pages_flat if page.output_url}
    inbound = _inbound_urls(pages)
    findings: list[Finding] = []
    for page in pages:
        if page.output_url in nav_urls or page.output_url in inbound:
            continue
        findings.append(
            Finding(
                severity=_SEVERITY_WARNING,
                rule="orphaned-page",
                file=page.source_path.as_posix(),
                message="Page is not in navigation and has no inbound links",
            )
        )
    return findings


def _inbound_urls(pages: list[Page]) -> set[str]:
    """Collect the set of output URLs that some page links to.

    A page that links to its own URL does not count as giving itself an inbound
    link, so self-references never rescue a page from the orphan check.
    """
    inbound: set[str] = set()
    for page in pages:
        if not page.rendered_content:
            continue
        for href in _HREF_RE.findall(page.rendered_content):
            target = href.split("#", 1)[0]
            if target and target != page.output_url:
                inbound.add(target)
    return inbound


def _lint_external(pages: list[Page], checker: Callable[[str], bool]) -> list[Finding]:
    """Report external links the ``checker`` predicate marks as unreachable."""
    findings: list[Finding] = []
    seen: set[str] = set()
    for page in pages:
        if not page.rendered_content:
            continue
        for href in _HREF_RE.findall(page.rendered_content):
            if "://" not in href or href in seen:
                continue
            seen.add(href)
            if not checker(href):
                findings.append(
                    Finding(
                        severity=_SEVERITY_ERROR,
                        rule="broken-external",
                        file=page.source_path.as_posix(),
                        message=f"External link is unreachable: {href}",
                    )
                )
    return findings


def check_external_url(url: str) -> bool:
    """Return ``True`` when ``url`` responds with a 2xx/3xx status.

    Uses a HEAD request with a short timeout. Any network failure (DNS, TLS,
    timeout, non-2xx) returns ``False`` so the link is reported as broken.

    :param url: The absolute external URL to probe.
    :returns: ``True`` if the URL appears reachable, ``False`` otherwise.
    """
    request = Request(url, method="HEAD")
    try:
        with urlopen(request, timeout=5) as response:  # noqa: S310 - external by design
            status = int(response.status)
            return 200 <= status < 400
    except URLError, ValueError, OSError:
        return False
