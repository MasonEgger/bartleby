# ABOUTME: Integration tests for the build pipeline orchestrator.
# Drives the sample fixture site through build() and inspects the output.

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from bartleby.build import BuildError, BuildResult, build, calculate_readtime, extract_excerpt
from bartleby.config import ConfigError


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


def test_build_renders_standalone_404(project: Path) -> None:
    """``build`` renders a standalone ``site/404.html`` from the 404 template."""
    build(project / "bartleby.yml")
    not_found = project / "site" / "404.html"
    assert not_found.exists()
    rendered = not_found.read_text(encoding="utf-8")
    assert "404" in rendered
    # The 404 template extends base.html, so the site chrome must be present.
    assert "<html" in rendered.lower()


def test_tree_shake_retains_icon_referenced_only_in_template(project: Path) -> None:
    """An icon referenced only in a project template is copied to the output.

    The page bodies never mention ``icon-material-home``; only an overriding
    template does. Tree-shaking must scan template sources, not just rendered
    page bodies, to retain it.
    """
    templates_dir = project / "templates"
    templates_dir.mkdir()
    (templates_dir / "page.html").write_text(
        '{% extends "base.html" %}\n'
        "{% block content %}\n"
        '<span class="icon icon-material-home"></span>\n'
        "<article><h1>{{ page.title }}</h1>{{ page.content | safe }}</article>\n"
        "{% endblock %}\n",
        encoding="utf-8",
    )
    build(project / "bartleby.yml")
    assert (project / "site" / "icons" / "material" / "home.svg").exists()


def test_on_files_runs_after_draft_filter(project: Path) -> None:
    """The ``on_files`` hook sees only published pages, never drafts.

    A hook registered in the project's ``hooks/`` directory records the titles
    of every page it receives. Because the draft filter runs before the hook, a
    draft post must be absent from what the hook observed.
    """
    hooks_dir = project / "hooks"
    hooks_dir.mkdir()
    record_path = project / "seen_pages.txt"
    (hooks_dir / "record.py").write_text(
        "# ABOUTME: Test hook that records the titles on_files receives.\n"
        "# Writes them to seen_pages.txt for the draft-filter ordering assertion.\n"
        "from __future__ import annotations\n"
        "from pathlib import Path\n"
        "\n"
        "RECORD = Path(__file__).parent.parent / 'seen_pages.txt'\n"
        "\n"
        "def on_files(pages, config):\n"
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
    project: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """In strict mode, an unresolved ``.md`` link aborts the build."""
    post_path = project / "content" / "blog" / "posts" / "first-post.md"
    text = post_path.read_text(encoding="utf-8")
    post_path.write_text(text + "\nSee [missing page](missing-target.md).\n", encoding="utf-8")
    with caplog.at_level("WARNING", logger="bartleby"), pytest.raises(ValueError) as exc:
        build(project / "bartleby.yml", strict=True)
    assert "strict" in str(exc.value).lower()
    assert "missing-target.md" in caplog.text


def test_build_non_strict_warns_on_broken_crossref(
    project: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Without strict mode, broken cross-references log a warning but do not abort."""
    post_path = project / "content" / "blog" / "posts" / "first-post.md"
    text = post_path.read_text(encoding="utf-8")
    post_path.write_text(text + "\nSee [missing page](missing-target.md).\n", encoding="utf-8")
    with caplog.at_level("WARNING", logger="bartleby"):
        result = build(project / "bartleby.yml")
    assert result.page_count > 0
    assert "missing-target.md" in caplog.text


def _inject_unknown_shortcode(post_path: Path, shortcode_name: str) -> None:
    """Append an unknown shortcode invocation to a content file so render fails."""
    text = post_path.read_text(encoding="utf-8")
    post_path.write_text(f"{text}\n[% {shortcode_name} %]\n", encoding="utf-8")


def test_build_collects_all_page_errors_into_one_build_error(project: Path) -> None:
    """Two pages with render errors raise a single BuildError carrying both.

    The render pass must not stop on the first failure. Both offending pages'
    paths appear in the collected error list.
    """
    first = project / "content" / "blog" / "posts" / "first-post.md"
    second = project / "content" / "blog" / "posts" / "second-post.md"
    _inject_unknown_shortcode(first, "totally_unknown_one")
    _inject_unknown_shortcode(second, "totally_unknown_two")

    with pytest.raises(BuildError) as exc:
        build(project / "bartleby.yml")

    collected = exc.value.errors
    assert len(collected) == 2, "render pass must collect both errors, not stop on the first"
    reported = "\n".join(str(error.file_path) for error in collected)
    assert "first-post.md" in reported
    assert "second-post.md" in reported


def test_failed_build_leaves_existing_site_untouched(project: Path) -> None:
    """A failing build never deletes or partially overwrites a pre-existing site/."""
    site_dir = project / "site"
    site_dir.mkdir()
    sentinel = site_dir / "sentinel.html"
    sentinel.write_text("previous good build", encoding="utf-8")

    first = project / "content" / "blog" / "posts" / "first-post.md"
    _inject_unknown_shortcode(first, "totally_unknown_one")

    with pytest.raises(BuildError):
        build(project / "bartleby.yml")

    assert sentinel.exists(), "failed build must not delete the existing site/"
    assert sentinel.read_text(encoding="utf-8") == "previous good build"
    # No partial output for the (would-be) new build leaked into site/.
    assert not (site_dir / "blog" / "posts" / "first-post" / "index.html").exists()


def test_successful_build_swaps_output_atomically(project: Path) -> None:
    """On success the new output replaces site/ wholesale and no temp dir lingers.

    A stale sentinel from a prior build must be gone (the directory is swapped,
    not merged into), and no sibling temp build directory is left behind.
    """
    site_dir = project / "site"
    site_dir.mkdir()
    (site_dir / "stale-from-old-build.html").write_text("old", encoding="utf-8")

    build(project / "bartleby.yml")

    assert (site_dir / "index.html").exists()
    assert not (site_dir / "stale-from-old-build.html").exists()
    leftover_temp = [
        child
        for child in project.iterdir()
        if child.is_dir() and child.name != "site" and child.name.startswith(".bartleby")
    ]
    assert leftover_temp == [], f"build left a temp directory behind: {leftover_temp}"


def test_invalid_config_fails_before_render(project: Path) -> None:
    """An invalid config raises ConfigError immediately, before any render pass."""
    site_dir = project / "site"
    site_dir.mkdir()
    sentinel = site_dir / "sentinel.html"
    sentinel.write_text("previous good build", encoding="utf-8")

    config_path = project / "bartleby.yml"
    config_path.write_text("site:\n  title: only a title, no url\n", encoding="utf-8")

    with pytest.raises(ConfigError):
        build(config_path)

    # Pre-render failure leaves the existing site/ completely untouched.
    assert sentinel.exists()
    assert sentinel.read_text(encoding="utf-8") == "previous good build"


def test_on_build_error_fires_once_with_collected_errors(project: Path) -> None:
    """A failing build dispatches ``on_build_error`` exactly once with the full error list.

    The hook receives the same :class:`BuildError` that is raised, so a plugin
    can inspect every collected :class:`PageError` in a single call rather than
    once per failure.
    """
    hooks_dir = project / "hooks"
    hooks_dir.mkdir()
    record_path = project / "build_errors.txt"
    (hooks_dir / "record_errors.py").write_text(
        "# ABOUTME: Test hook that records on_build_error invocations.\n"
        "# Appends one line per call carrying the count of collected errors.\n"
        "from __future__ import annotations\n"
        "from pathlib import Path\n"
        "\n"
        "RECORD = Path(__file__).parent.parent / 'build_errors.txt'\n"
        "\n"
        "def on_build_error(error):\n"
        "    paths = ','.join(str(page_error.file_path) for page_error in error.errors)\n"
        "    with RECORD.open('a', encoding='utf-8') as handle:\n"
        "        handle.write(f'{len(error.errors)}|{paths}\\n')\n",
        encoding="utf-8",
    )

    first = project / "content" / "blog" / "posts" / "first-post.md"
    second = project / "content" / "blog" / "posts" / "second-post.md"
    _inject_unknown_shortcode(first, "totally_unknown_one")
    _inject_unknown_shortcode(second, "totally_unknown_two")

    with pytest.raises(BuildError):
        build(project / "bartleby.yml")

    lines = record_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1, "on_build_error must fire exactly once, not per page error"
    count, paths = lines[0].split("|", 1)
    assert count == "2", "the hook must receive every collected error in one call"
    assert "first-post.md" in paths
    assert "second-post.md" in paths


def test_successful_build_does_not_fire_on_build_error(project: Path) -> None:
    """A clean build never dispatches ``on_build_error``."""
    hooks_dir = project / "hooks"
    hooks_dir.mkdir()
    record_path = project / "build_errors.txt"
    (hooks_dir / "record_errors.py").write_text(
        "# ABOUTME: Test hook that records on_build_error invocations.\n"
        "# Writes a marker file if the hook ever fires.\n"
        "from __future__ import annotations\n"
        "from pathlib import Path\n"
        "\n"
        "RECORD = Path(__file__).parent.parent / 'build_errors.txt'\n"
        "\n"
        "def on_build_error(error):\n"
        "    RECORD.write_text('fired', encoding='utf-8')\n",
        encoding="utf-8",
    )

    build(project / "bartleby.yml")

    assert not record_path.exists(), "on_build_error must not fire on a successful build"


def test_build_prefers_compiled_theme_css(project: Path) -> None:
    """A current ``.bartleby/theme.css`` overrides the shipped ``css/main.css``."""
    compiled = project / ".bartleby" / "theme.css"
    compiled.parent.mkdir(parents=True)
    compiled.write_text("/* compiled-by-tailwind */", encoding="utf-8")

    build(project / "bartleby.yml")

    rendered_css = (project / "site" / "css" / "main.css").read_text(encoding="utf-8")
    assert rendered_css == "/* compiled-by-tailwind */"


def test_build_ignores_stale_compiled_theme_css(project: Path) -> None:
    """A stale compiled CSS (older than a template) is not preferred."""
    import os
    import time

    templates_dir = project / "templates"
    templates_dir.mkdir(exist_ok=True)
    override = templates_dir / "custom-partial.html"
    override.write_text("<p>override</p>", encoding="utf-8")

    compiled = project / ".bartleby" / "theme.css"
    compiled.parent.mkdir(parents=True)
    compiled.write_text("/* compiled-but-stale */", encoding="utf-8")
    later = time.time() + 100
    os.utime(override, (later, later))

    build(project / "bartleby.yml")

    rendered_css = (project / "site" / "css" / "main.css").read_text(encoding="utf-8")
    assert "compiled-but-stale" not in rendered_css
