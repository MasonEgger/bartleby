# ABOUTME: Tests for content quality linting (broken links, missing desc, orphans).
# Covers the structured findings and the opt-in --check-external behaviour.

from __future__ import annotations

from pathlib import Path

from bartleby.content import Page
from bartleby.linting import Finding, lint_site


def _page(
    source: str,
    output_url: str,
    *,
    description: str | None = "A description.",
    rendered_content: str = "",
) -> Page:
    page = Page(
        source_path=Path(source),
        abs_source_path=Path("/abs") / source,
        title=source,
        description=description,
        content_type_name="blog",
    )
    page.output_url = output_url
    page.rendered_content = rendered_content
    return page


def test_broken_crossref_detected() -> None:
    """A ``.md`` link with no matching page yields a broken-crossref finding."""
    page = _page(
        "blog/posts/foo.md",
        "/blog/posts/foo/",
        rendered_content='<a href="missing.md">missing</a>',
    )
    findings = lint_site([page], _config(), Path("/content"))
    crossref = [f for f in findings if f.rule == "broken-crossref"]
    assert len(crossref) == 1
    assert crossref[0].severity == "error"
    assert crossref[0].file == "blog/posts/foo.md"
    assert "missing.md" in crossref[0].message
    assert crossref[0].fixable is False


def test_valid_crossref_not_flagged() -> None:
    """A resolvable ``.md`` link produces no broken-crossref finding."""
    target = _page("blog/posts/bar.md", "/blog/posts/bar/")
    page = _page(
        "blog/posts/foo.md",
        "/blog/posts/foo/",
        rendered_content='<a href="bar.md">bar</a>',
    )
    findings = lint_site([page, target], _config(), Path("/content"))
    assert [f for f in findings if f.rule == "broken-crossref"] == []


def test_missing_description_detected() -> None:
    """A page with no description yields a missing-description finding."""
    page = _page("blog/posts/foo.md", "/blog/posts/foo/", description=None)
    findings = lint_site([page], _config(), Path("/content"))
    missing = [f for f in findings if f.rule == "missing-description"]
    assert len(missing) == 1
    assert missing[0].severity == "warning"
    assert missing[0].file == "blog/posts/foo.md"


def test_present_description_not_flagged() -> None:
    """A page with a description produces no missing-description finding."""
    page = _page("blog/posts/foo.md", "/blog/posts/foo/", description="Set.")
    findings = lint_site([page], _config(), Path("/content"))
    assert [f for f in findings if f.rule == "missing-description"] == []


def test_orphan_page_detected() -> None:
    """A page with no inbound links and not in nav yields an orphan finding."""
    orphan = _page("blog/posts/lonely.md", "/blog/posts/lonely/")
    linker = _page(
        "blog/posts/hub.md",
        "/blog/posts/hub/",
        rendered_content='<a href="/blog/posts/hub/">self</a>',
    )
    findings = lint_site([orphan, linker], _config(), Path("/content"))
    orphans = [f for f in findings if f.rule == "orphaned-page"]
    assert any(f.file == "blog/posts/lonely.md" for f in orphans)
    assert all(f.severity == "warning" for f in orphans)


def test_linked_page_is_not_orphan() -> None:
    """A page that another page links to is not reported as an orphan."""
    target = _page("blog/posts/target.md", "/blog/posts/target/")
    linker = _page(
        "blog/posts/hub.md",
        "/blog/posts/hub/",
        rendered_content='<a href="/blog/posts/target/">go</a>',
    )
    findings = lint_site([target, linker], _config(), Path("/content"))
    orphans = [f.file for f in findings if f.rule == "orphaned-page"]
    assert "blog/posts/target.md" not in orphans


def test_check_external_off_by_default() -> None:
    """External links are not checked unless --check-external is requested.

    The default call must not produce any broken-external findings even when an
    external link is present, and must not attempt any network access.
    """
    page = _page(
        "blog/posts/foo.md",
        "/blog/posts/foo/",
        rendered_content='<a href="https://example.invalid/missing">ext</a>',
    )
    findings = lint_site([page], _config(), Path("/content"))
    assert [f for f in findings if f.rule == "broken-external"] == []


def test_check_external_opt_in_invokes_checker() -> None:
    """With check_external=True, the external checker is consulted per URL."""
    page = _page(
        "blog/posts/foo.md",
        "/blog/posts/foo/",
        rendered_content='<a href="https://example.com/page">ext</a>',
    )
    seen: list[str] = []

    def checker(url: str) -> bool:
        seen.append(url)
        return False

    findings = lint_site(
        [page], _config(), Path("/content"), check_external=True, external_checker=checker
    )
    assert "https://example.com/page" in seen
    external = [f for f in findings if f.rule == "broken-external"]
    assert len(external) == 1
    assert external[0].severity == "error"


def test_finding_is_structured() -> None:
    """A Finding carries severity, rule, file, message, and fixable fields."""
    finding = Finding(
        severity="warning",
        rule="orphaned-page",
        file="blog/posts/old.md",
        message="not linked",
    )
    assert finding.fixable is False
    assert finding.to_dict()["rule"] == "orphaned-page"


def _config() -> object:
    """A minimal stand-in config; linting only reads content_types/nav indirectly."""
    from bartleby.config import load_config

    sample = Path(__file__).parent / "fixtures" / "site" / "bartleby.yml"
    return load_config(sample)
