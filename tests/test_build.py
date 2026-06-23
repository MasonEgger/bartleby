# ABOUTME: Integration tests for the build pipeline orchestrator.
# Drives the sample fixture site through build() and inspects the output.

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from bartleby.build import BuildResult, build, calculate_readtime, extract_excerpt


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Copy the sample fixture site into a temp dir so build can mutate ``site/``."""
    source = Path(__file__).parent / "fixtures" / "site"
    destination = tmp_path / "site_project"
    shutil.copytree(source, destination)
    return destination


def test_build_produces_output_directory(project: Path) -> None:
    """``build`` writes a ``site/`` directory next to ``bartleby.yml``."""
    build(project / "bartleby.yml")
    assert (project / "site").is_dir()


def test_build_renders_index_page(project: Path) -> None:
    """The top-level ``index.md`` becomes ``site/index.html``."""
    build(project / "bartleby.yml")
    rendered = (project / "site" / "index.html").read_text(encoding="utf-8")
    assert "Welcome" in rendered


def test_build_renders_blog_post(project: Path) -> None:
    """Blog posts land at their generated URL path under ``site/``."""
    build(project / "bartleby.yml")
    rendered_dir = project / "site" / "blog" / "posts" / "first-post"
    assert (rendered_dir / "index.html").exists()


def test_build_post_renders_author_byline(project: Path) -> None:
    """Blog post HTML includes the resolved author name from ``.authors.yml``."""
    build(project / "bartleby.yml")
    rendered = (project / "site" / "blog" / "posts" / "first-post" / "index.html").read_text(
        encoding="utf-8"
    )
    # first-post.md front matter has `authors: [mason]`;
    # .authors.yml maps `mason` to `Mason Egger`.
    assert "Mason Egger" in rendered


def test_build_listing_page_lists_published_posts(project: Path) -> None:
    """The blog listing HTML contains a link to every published post."""
    build(project / "bartleby.yml")
    rendered = (project / "site" / "blog" / "index.html").read_text(encoding="utf-8")
    # Two published posts in the fixture: first-post and second-post.
    assert 'href="/blog/posts/first-post/"' in rendered
    assert 'href="/blog/posts/second-post/"' in rendered
    # Draft post must not appear.
    assert 'href="/blog/posts/draft-post/"' not in rendered


def test_on_pages_runs_after_draft_filter(project: Path) -> None:
    """The ``on_pages`` hook sees only published pages, never drafts.

    A hook registered in the project's ``hooks/`` directory records the titles
    of every page it receives. Because the draft filter now runs before the
    hook, a draft post must be absent from what the hook observed.
    """
    hooks_dir = project / "hooks"
    hooks_dir.mkdir()
    record_path = project / "seen_pages.txt"
    (hooks_dir / "record.py").write_text(
        "# ABOUTME: Test hook that records the titles on_pages receives.\n"
        "# Writes them to seen_pages.txt for the draft-filter ordering assertion.\n"
        "from __future__ import annotations\n"
        "from pathlib import Path\n"
        "\n"
        "RECORD = Path(__file__).parent.parent / 'seen_pages.txt'\n"
        "\n"
        "def on_pages(pages, config):\n"
        "    RECORD.write_text('\\n'.join(page.title for page in pages), encoding='utf-8')\n"
        "    return pages\n",
        encoding="utf-8",
    )
    build(project / "bartleby.yml")
    seen = record_path.read_text(encoding="utf-8")
    assert "Draft Post" not in seen
    # Sanity: the published posts the hook should see are present.
    assert "First Post" in seen


def test_build_sitemap_includes_listing_url(project: Path) -> None:
    """``sitemap.xml`` lists the navigable ``/blog/`` listing URL."""
    build(project / "bartleby.yml")
    sitemap = (project / "site" / "sitemap.xml").read_text(encoding="utf-8")
    assert "https://sample.example.com/blog/" in sitemap


def test_build_taxonomy_term_page_lists_tagged_posts(project: Path) -> None:
    """A ``/tags/python/`` term page links to every post tagged ``python``."""
    build(project / "bartleby.yml")
    target = project / "site" / "tags" / "python" / "index.html"
    assert target.exists(), "taxonomy term page should be generated for `python`"
    rendered = target.read_text(encoding="utf-8")
    assert 'href="/blog/posts/first-post/"' in rendered
    assert 'href="/blog/posts/second-post/"' in rendered


def test_build_html_is_valid_structure(project: Path) -> None:
    """Rendered pages include the standard HTML5 scaffolding."""
    build(project / "bartleby.yml")
    rendered = (project / "site" / "index.html").read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in rendered
    assert "<html" in rendered
    assert "<head>" in rendered
    assert "<body>" in rendered


def test_build_page_title_in_output(project: Path) -> None:
    """The page's front-matter title appears inside ``<title>``."""
    build(project / "bartleby.yml")
    rendered = (project / "site" / "index.html").read_text(encoding="utf-8")
    assert "<title>Home" in rendered


def test_build_excludes_drafts(project: Path) -> None:
    """Draft posts are not written to ``site/`` by default."""
    build(project / "bartleby.yml")
    draft_dir = project / "site" / "blog" / "posts" / "draft-post"
    assert not draft_dir.exists()


def test_build_includes_drafts_when_requested(project: Path) -> None:
    """``include_drafts=True`` writes draft posts alongside published ones."""
    build(project / "bartleby.yml", include_drafts=True)
    draft_dir = project / "site" / "blog" / "posts" / "draft-post"
    assert draft_dir.exists()


def test_build_cleans_output_dir(project: Path) -> None:
    """``site/`` is cleaned at the start of each build — stale files vanish."""
    site_dir = project / "site"
    site_dir.mkdir()
    (site_dir / "stale.html").write_text("stale")
    build(project / "bartleby.yml")
    assert not (site_dir / "stale.html").exists()


def test_build_returns_result(project: Path) -> None:
    """``build`` returns a :class:`BuildResult` with positive page count and duration."""
    result = build(project / "bartleby.yml")
    assert isinstance(result, BuildResult)
    assert result.page_count > 0
    assert result.duration_seconds >= 0.0


def test_extract_excerpt_with_separator() -> None:
    """When a separator is present, the excerpt is the content above it rendered to HTML."""
    source = "Intro paragraph.\n\n<!-- more -->\n\nRest of post.\n"
    excerpt = extract_excerpt(source, "<!-- more -->")
    assert "Intro paragraph" in excerpt
    assert "Rest of post" not in excerpt


def test_extract_excerpt_first_paragraph() -> None:
    """Without a separator, the first paragraph of source is returned."""
    source = "First paragraph.\n\nSecond paragraph.\n"
    excerpt = extract_excerpt(source, None)
    assert "First paragraph" in excerpt
    assert "Second paragraph" not in excerpt


def test_calculate_readtime() -> None:
    """``calculate_readtime`` returns ~1 minute per 265 words (rounded up)."""
    text = "word " * 1000
    assert calculate_readtime(text) in {3, 4, 5}


def test_calculate_readtime_short_text() -> None:
    """Very short text still returns at least 1 minute."""
    assert calculate_readtime("hello world") == 1


def test_build_strict_fails_on_broken_crossref(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """In strict mode, an unresolved ``.md`` link aborts the build."""
    post_path = project / "content" / "blog" / "posts" / "first-post.md"
    text = post_path.read_text(encoding="utf-8")
    post_path.write_text(text + "\nSee [missing page](missing-target.md).\n", encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        build(project / "bartleby.yml", strict=True)
    assert "strict" in str(exc.value).lower()
    captured = capsys.readouterr()
    assert "missing-target.md" in captured.err


def test_build_non_strict_warns_on_broken_crossref(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without strict mode, broken cross-references print to stderr but do not abort."""
    post_path = project / "content" / "blog" / "posts" / "first-post.md"
    text = post_path.read_text(encoding="utf-8")
    post_path.write_text(text + "\nSee [missing page](missing-target.md).\n", encoding="utf-8")
    result = build(project / "bartleby.yml")
    assert result.page_count > 0
    captured = capsys.readouterr()
    assert "missing-target.md" in captured.err
