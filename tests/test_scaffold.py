# ABOUTME: Tests for `bartleby new site`: the docs-shaped site, its feature tour, and --blog.
# Builds the real scaffold so a green suite means a newcomer's first run renders well.

from __future__ import annotations

import html as html_lib
import logging
import re
from pathlib import Path

import pytest

from bartleby.cli import main
from bartleby.config import load_config
from bartleby.theme_loader import select_theme
from tests.feed_helpers import atom_entries, rss_entries

# Every claim the tour makes, one hook per claim: a regex its built HTML must match. The
# sections that show several claims (prompts, superscript, subscript) get one hook each.
TOUR_HOOKS: dict[str, str] = {
    "fence label": r'class="code-label" title="app\.py"',
    "fence secondary label": r'class="secondary-code-label" title="Output"',
    "fence environment": r'<pre class="environment-local">',
    "prefixed line_numbers": r'<pre class="prefixed line_numbers">',
    "prefixed command": r'<pre class="prefixed command">',
    "prefixed custom_prefix": r'<pre class="prefixed custom_prefix">',
    "directives combined": (
        r'class="code-label" title="server\.sh">server\.sh</div>\s*'
        r'<div class="highlight"><pre class="prefixed command environment-local">'
    ),
    "highlight marker": "<mark>highlighted phrase</mark>",
    "inline code highlight": '<code class="highlight">',
    "mark": "<mark>marked text</mark>",
    "caret insert": "<ins>inserted text</ins>",
    "caret superscript": "<sup>2</sup>",
    "tilde delete": "<del>deleted text</del>",
    "tilde subscript": "<sub>2</sub>",
    "keys": '<kbd class="key-control">',
    # The source prints literally (checked on the unescaped HTML), then the result follows.
    "critic": (
        r"(?s)<pre><code>Proposed edit: \{\+\+added text\+\+\}, \{--removed text--\}"
        r".*?<ins class=\"critic\">added text</ins>"
    ),
    "smartsymbols": "&copy;",
    "emoji": 'class="emojione"',
    "arithmatex": 'class="arithmatex"',
    "tabbed": 'class="tabbed-set tabbed-alternate"',
    "details": "<details",
    "admonition": 'class="admonition warning"',
    "tasklist": "task-list-item",
    "caption": "<figcaption>",
    "table": "<table>",
    "footnote": 'class="footnote"',
    "definition list": "<dl>",
    "abbreviation": '<abbr title="HyperText Markup Language">',
    "attr_list": 'id="tour-note"',
    "youtube": '<iframe src="https://www.youtube.com/embed/jNQXAC9IVRw"',
    "codepen": 'class="codepen"',
    "twitter": '<blockquote class="twitter-tweet"',
    "instagram": 'class="instagram-media"',
    "slideshow": 'class="slideshow"',
    "image compare": 'class="image-compare"',
}

# Hooks whose pattern reads the HTML after entity decoding, since the page escapes them.
UNESCAPED_HOOKS = frozenset({"critic"})

# The writing-hard-rules banned vocabulary; "dive into" is a phrase.
BANNED_WORDS = (
    "delve|dive into|tapestry|vibrant|seamless|comprehensive|robust|leverage|unlock|unleash"
    "|realm|holistic|transformative|showcase|fostering|boasts|bolstered|crucial|pivotal"
    "|landscape|meticulous|testament|underscore|intricate|interplay|enduring"
)


def _missing_tour_hooks(html: str) -> list[str]:
    """The names of the TOUR_HOOKS the tour page's HTML fails to match."""
    decoded = html_lib.unescape(html)
    return [
        name
        for name, hook in TOUR_HOOKS.items()
        if re.search(hook, decoded if name in UNESCAPED_HOOKS else html) is None
    ]


def _unresolved_links(site: Path, html: str) -> list[str]:
    """Root-relative href and src values in ``html`` that name no file under ``site``."""
    unresolved: list[str] = []
    for target in re.findall(r'(?:href|src)="(/[^"#?]*)', html):
        if target.startswith("//"):
            continue
        built = site / target.lstrip("/")
        if not (built.is_file() or (built / "index.html").is_file()):
            unresolved.append(target)
    return unresolved


@pytest.fixture
def scaffold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Scaffold `mysite` in a temp dir and make it the working directory."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    project = tmp_path / "mysite"
    monkeypatch.chdir(project)
    return project


@pytest.fixture
def blog_scaffold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Scaffold `blogsite` with `--blog` and make it the working directory."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "blogsite", "--blog"])
    project = tmp_path / "blogsite"
    monkeypatch.chdir(project)
    return project


def test_scaffold_writes_docs_pages_and_no_blog_files(scaffold: Path) -> None:
    """The docs shape ships a home page, the tour, and its images; nothing blog-shaped."""
    assert (scaffold / "content" / "index.md").is_file()
    assert (scaffold / "content" / "tour" / "index.md").is_file()
    assert {path.name for path in (scaffold / "content" / "tour").glob("*.svg")} == {
        "slide-1.svg",
        "slide-2.svg",
        "slide-3.svg",
        "before.svg",
        "after.svg",
    }
    assert not (scaffold / "content" / "blog").exists()
    assert not (scaffold / ".authors.yml").exists()


def test_scaffold_config_is_minimal_and_defines_no_blog_or_markwright(scaffold: Path) -> None:
    """The config sets only what the site needs: no content types, taxonomies, or markwright."""
    text = (scaffold / "bartleby.yml").read_text(encoding="utf-8")
    top_level_keys = {
        line.split(":")[0]
        for line in text.splitlines()
        if line and not line.startswith((" ", "#"))
    }
    assert top_level_keys == {"site", "theme", "nav"}
    assert len(text.splitlines()) < 25
    config = load_config(scaffold / "bartleby.yml")
    assert config.content_types == {}
    assert config.markwright == {}
    assert config.site.title == "mysite"


def test_scaffold_selects_scrivener_with_features_its_manifest_declares(scaffold: Path) -> None:
    """The scaffold gets scrivener by default and enables only features the theme implements."""
    config = load_config(scaffold / "bartleby.yml")
    assert config.theme.name == "scrivener"
    assert "color-mode.toggle" in config.theme.features
    assert "nav.sidebar" in config.theme.features
    assert "nav.tabs" not in config.theme.features
    theme = select_theme(config.theme, scaffold)
    declared = {feature for layer in theme.chain for feature in layer.manifest.features}
    assert set(config.theme.features) <= declared


def test_scaffold_loads_without_warnings_and_builds_clean(
    scaffold: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """The minimal config loads, then the first build logs no warnings."""
    with caplog.at_level(logging.WARNING):
        load_config(scaffold / "bartleby.yml")
        main(["build", "--strict"])
    assert [record.getMessage() for record in caplog.records] == []
    site = scaffold / "site"
    assert (site / "index.html").is_file()
    assert (site / "tour" / "index.html").is_file()
    assert not (site / "blog").exists()


def test_scaffold_passes_lint(scaffold: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """`bartleby lint` finds nothing to report on a fresh site."""
    main(["lint"])
    assert "no issues" in capsys.readouterr().out


def test_tour_html_carries_the_output_of_every_feature_it_claims(scaffold: Path) -> None:
    """Each feature the tour shows renders to its own output hook, not as literal source."""
    main(["build"])
    html = (scaffold / "site" / "tour" / "index.html").read_text(encoding="utf-8")
    assert _missing_tour_hooks(html) == []


def test_tour_critic_source_prints_the_literal_markers_inside_a_pre(scaffold: Path) -> None:
    """The Critic Markup source is inert text: its braces and markers survive in a pre."""
    main(["build"])
    html = (scaffold / "site" / "tour" / "index.html").read_text(encoding="utf-8")
    pre_bodies = [
        html_lib.unescape(body)
        for body in re.findall(r"<pre><code>(.*?)</code></pre>", html, re.S)
    ]
    assert any(
        "{++added text++}" in body and "{>>A comment about it.<<}" in body for body in pre_bodies
    )


@pytest.mark.parametrize("theme", ["scrivener", "material"])
def test_bundled_theme_css_styles_extension_output_the_tour_shows(theme: str) -> None:
    """Emoji, Critic Markup comments, and task items need rules the compiled CSS keeps."""
    css_path = Path(__file__).parent.parent / "src" / "bartleby" / "themes" / theme
    css = (css_path / "static" / "css" / "main.css").read_text(encoding="utf-8")
    for selector in (".emojione", ".critic.comment", ".task-list-item", ".tabbed-labels"):
        assert selector in css, selector


def test_tour_shows_each_source_in_a_code_block(scaffold: Path) -> None:
    """Directive sources stay inert text inside code blocks beside their rendered result."""
    main(["build"])
    html = (scaffold / "site" / "tour" / "index.html").read_text(encoding="utf-8")
    for source in ("[youtube jNQXAC9IVRw]", "[codepen MattCowley vwPzeX]", "[compare before.svg"):
        assert source in html
    assert html.count("<iframe") == 1


def test_tour_images_sit_next_to_the_page_and_are_referenced_relatively(scaffold: Path) -> None:
    """The slideshow and compare images are copied beside the tour page they belong to."""
    main(["build"])
    tour = scaffold / "site" / "tour"
    html = (tour / "index.html").read_text(encoding="utf-8")
    for name in ("slide-1.svg", "slide-2.svg", "slide-3.svg", "before.svg", "after.svg"):
        assert (tour / name).is_file()
        assert f'src="{name}"' in html


def test_tour_has_three_columns_with_the_tour_in_the_sidebar(scaffold: Path) -> None:
    """The tour page gets the docs grid: section tree, reading column, and table of contents."""
    main(["build"])
    html = (scaffold / "site" / "tour" / "index.html").read_text(encoding="utf-8")
    assert 'class="layout-docs"' in html
    assert "sidebar-nav" in html
    assert 'href="/tour/"' in html
    assert 'class="toc-sidebar"' in html
    assert '<a href="#code-blocks"' in html


def test_home_page_leads_to_the_tour_and_the_blog_opt_in(scaffold: Path) -> None:
    """The home page links the tour and names both ways to add a blog."""
    main(["build"])
    html = (scaffold / "site" / "index.html").read_text(encoding="utf-8")
    text = re.sub(r"<[^>]+>", "", html)
    assert 'href="/tour/"' in html
    assert "bartleby serve" in text
    assert "bartleby enable blog blog" in text
    assert "new site my-site --blog" in text


def test_readme_shows_the_click_to_load_opt_in(scaffold: Path) -> None:
    """The quickstart gives the exact markwright section and names eager as the default."""
    readme = (scaffold / "README.md").read_text(encoding="utf-8")
    assert "markwright:\n  youtube:\n    load: click\n" in readme
    assert "Eager loading is the default" in readme
    assert "bartleby enable blog blog" in readme


def test_scaffold_prose_follows_the_writing_rules() -> None:
    """No dash characters, curly quotes, or banned vocabulary in the shipped Markdown."""
    root = Path(__file__).parent.parent / "src" / "bartleby"
    banned = re.compile(rf"\b(?:{BANNED_WORDS})\b", re.I)
    for path in [*(root / "scaffold").rglob("*.md"), *(root / "scaffold_blog").rglob("*.md")]:
        text = path.read_text(encoding="utf-8")
        assert not re.search("[–—‘’“”]", text), path
        assert banned.search(text) is None, path


def test_blog_flag_adds_the_blog_type_taxonomy_nav_entry_and_sample_post(
    blog_scaffold: Path,
) -> None:
    """`--blog` writes the same blog block `enable` writes, plus a sample post."""
    config = load_config(blog_scaffold / "bartleby.yml")
    blog = config.content_types["blog"]
    assert blog.path == "blog/posts"
    assert "tags" in blog.taxonomies
    assert list(blog.feeds) == ["rss", "atom"]
    assert "tags" in config.taxonomies
    assert config.nav is not None
    assert [next(iter(entry)) for entry in config.nav] == ["Home", "Feature Tour", "Blog"]
    post = blog_scaffold / "content" / "blog" / "posts" / "welcome.md"
    assert "\ndraft: false\n" in post.read_text(encoding="utf-8")
    assert (blog_scaffold / ".authors.yml").is_file()
    assert (blog_scaffold / "content" / "tour" / "index.md").is_file()


def test_blog_flag_site_builds_with_the_post_in_listing_and_feeds(
    blog_scaffold: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """The blog listing, the post page, and the feed files all carry the sample post."""
    with caplog.at_level(logging.WARNING):
        main(["build", "--strict"])
    assert [record.getMessage() for record in caplog.records] == []
    site = blog_scaffold / "site"
    assert "/blog/posts/welcome/" in (site / "blog" / "index.html").read_text(encoding="utf-8")
    assert (site / "blog" / "posts" / "welcome" / "index.html").is_file()
    welcome = [("Welcome to Bartleby", "https://example.com/blog/posts/welcome/")]
    for feed in ("blog/feed.xml", "feed.xml"):
        assert rss_entries((site / feed).read_text(encoding="utf-8")) == welcome, feed
    for feed in ("blog/atom.xml", "atom.xml"):
        assert atom_entries((site / feed).read_text(encoding="utf-8")) == welcome, feed
    tour = (site / "tour" / "index.html").read_text(encoding="utf-8")
    assert 'href="/blog/"' in tour


def test_blog_flag_matches_what_enable_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The scaffold's blog block and `enable blog blog` produce the same content type."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "viaflag", "--blog"])
    main(["new", "site", "viaenable"])
    main(["enable", "blog", "blog", "--config", str(tmp_path / "viaenable" / "bartleby.yml")])
    flagged = load_config(tmp_path / "viaflag" / "bartleby.yml")
    enabled = load_config(tmp_path / "viaenable" / "bartleby.yml")
    assert flagged.content_types == enabled.content_types
    assert flagged.taxonomies == enabled.taxonomies


def test_blog_and_full_config_flags_combine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The full config is written first and the blog block is merged into it; it builds."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "both", "--blog", "--full-config"])
    config_path = tmp_path / "both" / "bartleby.yml"
    text = config_path.read_text(encoding="utf-8")
    assert "A bundled theme name." in text
    with caplog.at_level(logging.WARNING):
        config = load_config(config_path)
        main(["build", "--strict", "--config", str(config_path)])
    assert caplog.records == []
    assert "blog" in config.content_types
    assert "tags" in config.taxonomies
    assert "Welcome to Bartleby" in (tmp_path / "both" / "site" / "feed.xml").read_text(
        encoding="utf-8"
    )


def test_new_post_fits_the_blog_the_flag_adds(blog_scaffold: Path) -> None:
    """`new post` writes into the scaffolded blog path and the site still builds."""
    main(["new", "post", "Second Post", "--type", "blog"])
    assert (blog_scaffold / "content" / "blog" / "posts" / "second-post.md").is_file()
    main(["build"])


def test_first_run_site_holds_every_claim_end_to_end(blog_scaffold: Path) -> None:
    """Scaffold with a blog, build strictly, then check links, the tour, and the feeds."""
    main(["build", "--strict"])
    site = blog_scaffold / "site"
    home = (site / "index.html").read_text(encoding="utf-8")
    assert _unresolved_links(site, home) == []
    tour = (site / "tour" / "index.html").read_text(encoding="utf-8")
    assert _missing_tour_hooks(tour) == []
    base = load_config(blog_scaffold / "bartleby.yml").site.url
    assert base == "https://example.com"
    welcome = [("Welcome to Bartleby", f"{base}/blog/posts/welcome/")]
    assert rss_entries((site / "feed.xml").read_text(encoding="utf-8")) == welcome
    assert atom_entries((site / "atom.xml").read_text(encoding="utf-8")) == welcome
