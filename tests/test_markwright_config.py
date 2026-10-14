# ABOUTME: Build-level tests for the `markwright:` section of bartleby.yml.
# Covers the ignored markwright.toml / [tool.markwright] warning and per-site extension toggles.

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from bartleby.build import build

if TYPE_CHECKING:
    from collections.abc import Callable

    ProjectFactory = Callable[..., Path]

_TWEET = "[twitter someone/status/1234567890]"
_EMBED_PAGE = f"---\ntitle: Embeds\ndescription: An embed page\n---\n\n{_TWEET}\n"


@pytest.fixture
def make_project(tmp_path: Path) -> ProjectFactory:
    """Factory: copy the sample site to a fresh directory with an embed page and extra config."""
    counter = 0

    def _make(extra_config: str = "") -> Path:
        nonlocal counter
        counter += 1
        project = tmp_path / f"project-{counter}"
        shutil.copytree(Path(__file__).parent / "fixtures" / "site", project)
        (project / "content" / "embeds.md").write_text(_EMBED_PAGE, encoding="utf-8")
        config_path = project / "bartleby.yml"
        config_path.write_text(
            config_path.read_text(encoding="utf-8") + "\n" + extra_config, encoding="utf-8"
        )
        return project

    return _make


def _ignored_warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.levelname == "WARNING" and "ignored" in record.getMessage()
    ]


def _embed_html(project: Path) -> str:
    return (project / "site" / "embeds" / "index.html").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("file_name", "body", "named"),
    [
        ("markwright.toml", 'disable = ["twitter"]\n', "markwright.toml"),
        ("pyproject.toml", '[tool.markwright]\ndisable = ["twitter"]\n', "pyproject.toml"),
    ],
)
def test_ignored_markwright_config_warns_once_and_changes_nothing(
    make_project: ProjectFactory,
    file_name: str,
    body: str,
    named: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A stray markwright config beside bartleby.yml warns once and does not affect rendering."""
    baseline = make_project()
    build(baseline / "bartleby.yml")

    stray = make_project()
    (stray / file_name).write_text(body, encoding="utf-8")
    with caplog.at_level("WARNING", logger="bartleby"):
        build(stray / "bartleby.yml")

    warnings = _ignored_warnings(caplog)
    assert len(warnings) == 1
    assert named in warnings[0]
    assert "bartleby.yml" in warnings[0]
    assert _embed_html(stray) == _embed_html(baseline)
    assert "twitter-tweet" in _embed_html(stray)


def test_pyproject_without_a_markwright_table_does_not_warn(
    make_project: ProjectFactory, caplog: pytest.LogCaptureFixture
) -> None:
    """A pyproject.toml with no [tool.markwright] table is not a markwright config."""
    project = make_project()
    (project / "pyproject.toml").write_text('[project]\nname = "site"\n', encoding="utf-8")
    with caplog.at_level("WARNING", logger="bartleby"):
        build(project / "bartleby.yml")
    assert _ignored_warnings(caplog) == []


@pytest.mark.parametrize("tool_value", ["5", '"markwright"'])
def test_non_table_tool_key_neither_crashes_nor_warns(
    make_project: ProjectFactory, tool_value: str, caplog: pytest.LogCaptureFixture
) -> None:
    """A pyproject.toml whose `tool` is not a table is not a markwright config."""
    project = make_project()
    (project / "pyproject.toml").write_text(f"tool = {tool_value}\n", encoding="utf-8")
    with caplog.at_level("WARNING", logger="bartleby"):
        build(project / "bartleby.yml")
    assert _ignored_warnings(caplog) == []


def test_no_stray_config_means_no_warning(
    make_project: ProjectFactory, caplog: pytest.LogCaptureFixture
) -> None:
    """A plain project builds with no ignored-config warning."""
    project = make_project()
    with caplog.at_level("WARNING", logger="bartleby"):
        build(project / "bartleby.yml")
    assert _ignored_warnings(caplog) == []


def test_disabled_twitter_leaves_the_raw_fence_and_stray_file_warns(
    make_project: ProjectFactory, caplog: pytest.LogCaptureFixture
) -> None:
    """`markwright: {disable: [twitter]}` renders the directive as text, beside the warning."""
    project = make_project("markwright:\n  disable: [twitter]\n")
    (project / "markwright.toml").write_text('disable = ["youtube"]\n', encoding="utf-8")

    with caplog.at_level("WARNING", logger="bartleby"):
        build(project / "bartleby.yml")

    html = _embed_html(project)
    assert _TWEET in html
    assert "twitter-tweet" not in html
    assert len(_ignored_warnings(caplog)) == 1


_CLICK_SCRIPT = '<script defer src="/js/click_to_load.js"></script>'
_CLICK_STYLES = '<link rel="stylesheet" href="/css/click_to_load.css">'


@pytest.mark.parametrize("theme_name", ["scrivener", "material"])
def test_click_embed_page_loads_the_swap_script_and_styles(
    make_project: ProjectFactory, theme_name: str
) -> None:
    """A page with a `load: click` embed keeps markwright's preview and links the host assets."""
    project = make_project(
        f"theme:\n  name: {theme_name}\nmarkwright:\n  twitter: {{load: click}}\n"
    )

    build(project / "bartleby.yml")

    html = _embed_html(project)
    assert 'data-mw-load="click"' in html
    assert '<template class="mw-embed-content">' in html
    assert _CLICK_SCRIPT in html
    assert _CLICK_STYLES in html
    assert (project / "site" / "js" / "click_to_load.js").is_file()
    assert (project / "site" / "css" / "click_to_load.css").is_file()


@pytest.mark.parametrize("theme_name", ["scrivener", "material"])
def test_eager_embed_page_loads_no_click_assets(
    make_project: ProjectFactory, theme_name: str
) -> None:
    """Embeds are eager by default, so the page carries the live markup and no swap script."""
    project = make_project(f"theme:\n  name: {theme_name}\n")

    build(project / "bartleby.yml")

    html = _embed_html(project)
    assert "twitter-tweet" in html
    assert "mw-embed" not in html
    assert "click_to_load" not in html


_LISTING_POST = """---
title: Welcome
description: A post with a video in its excerpt.
date: 2026-10-12
tags: [news]
---

A post with a video up top.

{excerpt_body}

<!-- more -->

The rest of the post.
"""


def _make_blog(root: Path, theme_name: str, *, excerpt_body: str, load: str) -> Path:
    """Write a blog-shaped site whose one post has `excerpt_body` above the separator."""
    (root / "content" / "blog" / "posts").mkdir(parents=True)
    (root / "content" / "index.md").write_text(
        "---\ntitle: Home\n---\n\nHello.\n", encoding="utf-8"
    )
    (root / "content" / "blog" / "posts" / "welcome.md").write_text(
        _LISTING_POST.format(excerpt_body=excerpt_body), encoding="utf-8"
    )
    (root / "bartleby.yml").write_text(
        "site:\n  title: Listing\n  url: https://example.com\n"
        f"theme:\n  name: {theme_name}\n"
        "content_types:\n  blog:\n    path: blog/posts\n"
        '    excerpt_separator: "<!-- more -->"\n    taxonomies:\n      - tags\n'
        'taxonomies:\n  tags:\n    slug_format: "{slug}"\n'
        f"markwright:\n  youtube: {{load: {load}}}\n",
        encoding="utf-8",
    )
    return root / "bartleby.yml"


@pytest.mark.parametrize("theme_name", ["scrivener", "material"])
def test_listing_and_tag_pages_load_click_assets_for_a_click_excerpt(
    tmp_path: Path, theme_name: str
) -> None:
    """A listing or term page that prints a click embed's preview links the swap assets."""
    config = _make_blog(tmp_path, theme_name, excerpt_body="[youtube dQw4w9WgXcQ]", load="click")

    build(config)

    site = tmp_path / "site"
    pages = [
        site / "blog" / "index.html",
        site / "blog" / "tags" / "news" / "index.html",
        site / "tags" / "news" / "index.html",
        site / "blog" / "posts" / "welcome" / "index.html",
    ]
    for page in pages:
        html = page.read_text(encoding="utf-8")
        assert 'data-mw-load="click"' in html, page
        assert _CLICK_SCRIPT in html, page
        assert _CLICK_STYLES in html, page


@pytest.mark.parametrize("theme_name", ["scrivener", "material"])
def test_listing_without_a_click_excerpt_loads_no_click_assets(
    tmp_path: Path, theme_name: str
) -> None:
    """A listing whose excerpts hold no click embed carries neither asset tag."""
    config = _make_blog(tmp_path, theme_name, excerpt_body="Just text.", load="click")

    build(config)

    site = tmp_path / "site"
    for page in (site / "blog" / "index.html", site / "blog" / "tags" / "news" / "index.html"):
        html = page.read_text(encoding="utf-8")
        assert "click_to_load" not in html, page


@pytest.mark.parametrize("theme_name", ["scrivener", "material"])
def test_front_matter_named_like_listing_keys_neither_crashes_nor_loads_assets(
    make_project: ProjectFactory, theme_name: str
) -> None:
    """User front matter `posts`, `intro_content`, and `paginator` is data, not listing state."""
    project = make_project(f"theme:\n  name: {theme_name}\n")
    (project / "content" / "plain.md").write_text(
        "---\ntitle: Plain\ndescription: A plain page\n"
        "posts: 5\nintro_content: 5\npaginator: 5\n---\n\nHello.\n",
        encoding="utf-8",
    )

    build(project / "bartleby.yml")

    html = (project / "site" / "plain" / "index.html").read_text(encoding="utf-8")
    assert "click_to_load" not in html


def test_disallowed_environment_logs_one_warning_naming_it(
    make_project: ProjectFactory, caplog: pytest.LogCaptureFixture
) -> None:
    """A directive outside ``allowed_environments`` is reported once per page, by name."""
    project = make_project("markwright:\n  fence:\n    allowed_environments: [local]\n")
    (project / "content" / "envs.md").write_text(
        "---\ntitle: Envs\n---\n\n```\n[environment third]\nssh a\n```\n\n"
        "```\n[environment third]\nssh b\n```\n\n```\n[environment local]\nssh c\n```\n",
        encoding="utf-8",
    )
    with caplog.at_level("WARNING", logger="bartleby"):
        build(project / "bartleby.yml")

    warnings = [
        record.getMessage() for record in caplog.records if "environment" in record.getMessage()
    ]
    assert len(warnings) == 1
    assert "third" in warnings[0]
    assert "envs.md" in warnings[0]
    assert "allowed_environments" in warnings[0]


def test_warn_false_silences_the_disallowed_environment_warning(
    make_project: ProjectFactory, caplog: pytest.LogCaptureFixture
) -> None:
    """``warn: false`` in the markwright section turns the report off."""
    project = make_project(
        "markwright:\n  warn: false\n  fence:\n    allowed_environments: [local]\n"
    )
    (project / "content" / "envs.md").write_text(
        "---\ntitle: Envs\n---\n\n```\n[environment third]\nssh a\n```\n", encoding="utf-8"
    )
    with caplog.at_level("WARNING", logger="bartleby"):
        build(project / "bartleby.yml")

    assert [record for record in caplog.records if "environment" in record.getMessage()] == []
