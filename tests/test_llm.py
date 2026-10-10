# ABOUTME: Tests for LLM-friendly output generation.
# Covers llms.txt, llms-full.txt, .md variants, and JSON-LD structured data.

from __future__ import annotations

import datetime
import json
import re
import shutil
from pathlib import Path

import pytest

from bartleby.build import BuildResult, build
from bartleby.config import (
    AIConfig,
    BartlebyConfig,
    ContentTypeConfig,
    DevServerConfig,
    PaginationConfig,
    SiteConfig,
    TaxonomyConfig,
    ThemeConfig,
    load_config,
)
from bartleby.content import Page, discover_content
from bartleby.content_query import select_published
from bartleby.llm import (
    generate_jsonld,
    generate_llms_full_txt,
    generate_llms_txt,
    write_markdown_variant,
)


def _page(
    *,
    source: str,
    title: str,
    content_type_name: str | None = "blog",
    date: datetime.date | None = None,
    raw: str = "Body content.\n",
    description: str | None = None,
) -> Page:
    page = Page(
        source_path=Path(source),
        abs_source_path=Path("/abs") / source,
        title=title,
        content_type_name=content_type_name,
        date=date,
        description=description,
        raw_content=raw,
    )
    page.output_url = "/" + source.removesuffix(".md") + "/"
    return page


def _config(*, ai: AIConfig | None = None) -> BartlebyConfig:
    return BartlebyConfig(
        site=SiteConfig(title="Site", url="https://example.com", description="Site desc"),
        nav=None,
        theme=ThemeConfig(),
        authors_file=".authors.yml",
        content_types={
            "blog": ContentTypeConfig(
                name="blog", path="blog/posts", pagination=PaginationConfig()
            ),
        },
        taxonomies={"tags": TaxonomyConfig(name="tags", slug_format="{slug}")},
        exclude_patterns=[],
        markdown_extensions=[],
        plugins=[],
        extra_css=[],
        extra_js=[],
        ai=ai if ai is not None else AIConfig(),
        dev_server=DevServerConfig(),
        config_dir=Path("/tmp"),
    )


def test_llms_txt_format() -> None:
    """``llms.txt`` opens with the site title and lists posts by content type."""
    pages = [_page(source="blog/posts/a.md", title="A")]
    text = generate_llms_txt(pages, _config())
    assert text.startswith("# Site")
    assert "Site desc" in text
    assert "## Blog" in text
    assert "A" in text


def test_llms_txt_links_to_md_variants() -> None:
    """The links in ``llms.txt`` resolve to ``.md`` variants of each page."""
    pages = [_page(source="blog/posts/a.md", title="A")]
    text = generate_llms_txt(pages, _config())
    assert "/blog/posts/a/index.md" in text


def test_llms_full_txt_includes_content() -> None:
    """``llms-full.txt`` embeds each page's raw markdown body."""
    pages = [
        _page(source="blog/posts/a.md", title="A", raw="First body."),
        _page(source="blog/posts/b.md", title="B", raw="Second body."),
    ]
    text = generate_llms_full_txt(pages, _config())
    assert "First body." in text
    assert "Second body." in text
    assert "---" in text


def test_llms_txt_links_are_absolute_urls() -> None:
    """Every page link in ``llms.txt`` is an absolute URL on the site."""
    pages = [_page(source="blog/posts/a.md", title="A")]
    text = generate_llms_txt(pages, _config())
    assert "- [A](https://example.com/blog/posts/a/index.md): " in text


def test_llms_txt_lists_sections_with_titles_and_skips_drafts() -> None:
    """Sections follow the config order, static pages land under Pages, drafts are absent."""
    draft = _page(source="blog/posts/d.md", title="Draft Post")
    draft.draft = True
    pages = [
        _page(source="blog/posts/a.md", title="A Post", description="About A"),
        _page(source="about.md", title="About", content_type_name=None),
        draft,
    ]
    text = generate_llms_txt(pages, _config())
    assert text.index("## Blog") < text.index("## Pages")
    assert "- [A Post](https://example.com/blog/posts/a/index.md): About A" in text
    assert "- [About](https://example.com/about/index.md)" in text
    assert "Draft Post" not in text


def test_llms_txt_entry_stays_on_one_line() -> None:
    """A multi-line description or excerpt cannot break the list entry."""
    page = _page(source="blog/posts/a.md", title="A")
    page.excerpt = "First line.\n\nSecond   paragraph."
    text = generate_llms_txt([page], _config())
    assert (
        "- [A](https://example.com/blog/posts/a/index.md): First line. Second paragraph." in text
    )


def test_llms_full_txt_has_title_absolute_url_and_body_per_published_page() -> None:
    """Each section of ``llms-full.txt`` carries the title, absolute URL, and body."""
    draft = _page(source="blog/posts/d.md", title="Draft Post", raw="Secret.")
    draft.draft = True
    pages = [
        _page(
            source="blog/posts/a.md", title="A", raw="First body.", date=datetime.date(2026, 1, 2)
        ),
        draft,
    ]
    text = generate_llms_full_txt(pages, _config())
    assert "# A\nURL: https://example.com/blog/posts/a/\nDate: 2026-01-02\n\nFirst body." in text
    assert "Secret." not in text


def test_markdown_variant_written(tmp_path: Path) -> None:
    """A page at ``/blog/posts/a/`` produces ``/blog/posts/a/index.md`` next to the HTML."""
    page = _page(source="blog/posts/a.md", title="A", raw="Body content.\n")
    write_markdown_variant(page, tmp_path)
    assert (tmp_path / "blog" / "posts" / "a" / "index.md").exists()


def test_markdown_variant_strips_front_matter(tmp_path: Path) -> None:
    """The ``.md`` variant contains only the body — no YAML front matter."""
    page = _page(source="blog/posts/a.md", title="A", raw="Body only.")
    write_markdown_variant(page, tmp_path)
    contents = (tmp_path / "blog" / "posts" / "a" / "index.md").read_text()
    assert "Body only." in contents
    assert "---" not in contents


def test_jsonld_article_for_post() -> None:
    """Pages with a content type get ``@type=Article`` in JSON-LD."""
    page = _page(
        source="blog/posts/a.md",
        title="A",
        date=datetime.date(2026, 3, 1),
        description="A desc",
    )
    payload = json.loads(generate_jsonld(page, _config().site))
    assert payload["@type"] == "Article"
    assert payload["headline"] == "A"
    assert payload["datePublished"] == "2026-03-01"


def test_jsonld_webpage_for_static() -> None:
    """Pages without a content type get ``@type=WebPage``."""
    page = _page(source="about.md", title="About", content_type_name=None)
    payload = json.loads(generate_jsonld(page, _config().site))
    assert payload["@type"] == "WebPage"


def test_jsonld_fields_populated() -> None:
    """JSON-LD carries headline, description, url, and (for articles) datePublished."""
    page = _page(
        source="blog/posts/a.md",
        title="A",
        date=datetime.date(2026, 3, 1),
        description="A desc",
    )
    payload = json.loads(generate_jsonld(page, _config().site))
    assert payload["headline"] == "A"
    assert payload["description"] == "A desc"
    assert payload["url"] == "https://example.com/blog/posts/a/"


def test_jsonld_round_trips_special_characters() -> None:
    """Headline and description survive a double quote, a backslash, and a < character."""
    page = _page(
        source="blog/posts/a.md",
        title='The "Best" \\ <Way>',
        date=datetime.date(2026, 3, 1),
        description='A "great" \\ <thing>',
    )
    payload = json.loads(generate_jsonld(page, _config().site))
    assert payload["headline"] == 'The "Best" \\ <Way>'
    assert payload["description"] == 'A "great" \\ <thing>'


def test_jsonld_escapes_script_close_tag() -> None:
    """A title containing a literal </script> cannot break out of the inline script block.

    The output still round trips through json.loads back to the original title
    (this is the scenario the jsonld partial emits via ``| safe``).
    """
    page = _page(source="blog/posts/a.md", title="A </script> B")
    output = generate_jsonld(page, _config().site)
    assert "</script>" not in output
    payload = json.loads(output)
    assert payload["headline"] == "A </script> B"


_JSONLD_PATTERN = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL)
_ALTERNATE_MARKDOWN_PATTERN = re.compile(
    r'<link rel="alternate" type="text/markdown" href="([^"]+)">'
)
_FIXTURE_SITE = Path(__file__).parent / "fixtures" / "site"


@pytest.fixture(scope="module", params=["material", "scrivener"])
def built_site(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the sample fixture site once per visual theme and return the project dir."""
    project = tmp_path_factory.mktemp("agent_surface") / "site_project"
    shutil.copytree(_FIXTURE_SITE, project)
    config_path = project / "bartleby.yml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + f"\ntheme:\n  name: {request.param}\n",
        encoding="utf-8",
    )
    result = build(config_path)
    assert isinstance(result, BuildResult)
    return project


def _published_content_pages(project: Path) -> list[Page]:
    """Discover the fixture's content pages and keep the published ones."""
    config = load_config(project / "bartleby.yml")
    pages, _assets = discover_content(config, project / "content")
    return select_published(pages)


def _output_html_files(project: Path) -> list[Path]:
    return sorted((project / "site").rglob("*.html"))


def _jsonld_blocks(html_file: Path) -> list[dict[str, object]]:
    html = html_file.read_text(encoding="utf-8")
    blocks: list[dict[str, object]] = [
        json.loads(match) for match in _JSONLD_PATTERN.findall(html)
    ]
    return blocks


def test_every_published_page_has_a_markdown_variant(built_site: Path) -> None:
    """Each published content page has ``index.md`` at its output URL."""
    published = _published_content_pages(built_site)
    assert published
    for page in published:
        url = page.output_url.strip("/")
        variant = built_site / "site" / url / "index.md"
        assert variant.is_file(), f"missing variant for {page.source_path}"


def test_markdown_variant_count_equals_published_count(built_site: Path) -> None:
    """The number of ``index.md`` files in the output equals the published page count."""
    variants = list((built_site / "site").rglob("index.md"))
    assert len(variants) == len(_published_content_pages(built_site))


def test_every_alternate_markdown_link_points_at_an_existing_file(built_site: Path) -> None:
    """No page advertises a Markdown variant that was not written (404, taxonomies, listings)."""
    output_dir = built_site / "site"
    checked = 0
    for html_file in _output_html_files(built_site):
        html = html_file.read_text(encoding="utf-8")
        for href in _ALTERNATE_MARKDOWN_PATTERN.findall(html):
            checked += 1
            assert (output_dir / href.lstrip("/")).is_file(), f"{html_file}: {href}"
    assert checked > 0


def test_pages_without_a_variant_emit_no_alternate_link(built_site: Path) -> None:
    """404 and generated taxonomy pages carry no ``text/markdown`` alternate link."""
    output_dir = built_site / "site"
    not_found = (output_dir / "404.html").read_text(encoding="utf-8")
    assert "text/markdown" not in not_found
    taxonomy_html = (output_dir / "tags" / "index.html").read_text(encoding="utf-8")
    assert "text/markdown" not in taxonomy_html


def test_every_output_page_has_one_valid_jsonld_block(built_site: Path) -> None:
    """Each HTML file carries exactly one parseable JSON-LD block with the core fields."""
    for html_file in _output_html_files(built_site):
        blocks = _jsonld_blocks(html_file)
        assert len(blocks) == 1, html_file
        payload = blocks[0]
        assert payload["@context"] == "https://schema.org"
        assert payload["@type"] in {"Article", "WebPage", "CollectionPage"}
        assert payload["headline"] or payload["name"]
        assert str(payload["url"]).startswith("https://sample.example.com/")


def test_jsonld_type_matches_page_kind(built_site: Path) -> None:
    """Posts are Articles, generated pages CollectionPages, everything else WebPages."""
    output_dir = built_site / "site"
    post = _jsonld_blocks(output_dir / "blog" / "posts" / "first-post" / "index.html")[0]
    assert post["@type"] == "Article"
    assert post["url"] == "https://sample.example.com/blog/posts/first-post/"
    listing = _jsonld_blocks(output_dir / "blog" / "index.html")[0]
    assert listing["@type"] == "CollectionPage"
    taxonomy = _jsonld_blocks(output_dir / "tags" / "index.html")[0]
    assert taxonomy["@type"] == "CollectionPage"
    about = _jsonld_blocks(output_dir / "about" / "index.html")[0]
    assert about["@type"] == "WebPage"
    not_found = _jsonld_blocks(output_dir / "404.html")[0]
    assert not_found["@type"] == "WebPage"


def test_drafts_and_excluded_pages_get_no_variant_or_jsonld(built_site: Path) -> None:
    """Draft and exclude-pattern pages are absent: no HTML, no variant, no JSON-LD."""
    output_dir = built_site / "site"
    for absent in ("blog/posts/draft-post", "blog/posts/draft-with-asset", "_drafts/wip", "wip"):
        assert not (output_dir / absent).exists(), absent
    for html_file in _output_html_files(built_site):
        assert "Excluded WIP" not in html_file.read_text(encoding="utf-8")
        assert all(block.get("headline") != "Draft Post" for block in _jsonld_blocks(html_file))
    for variant in output_dir.rglob("index.md"):
        assert "Excluded WIP" not in variant.read_text(encoding="utf-8")


def test_markdown_variants_disabled_emits_no_alternate_link(tmp_path: Path) -> None:
    """With ``ai.markdown_variants`` off, no variant is written and no page links to one."""
    project = tmp_path / "site_project"
    shutil.copytree(_FIXTURE_SITE, project)
    config_path = project / "bartleby.yml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + "\nai:\n  markdown_variants: false\n",
        encoding="utf-8",
    )
    build(config_path)
    assert not list((project / "site").rglob("index.md"))
    for html_file in _output_html_files(project):
        assert "text/markdown" not in html_file.read_text(encoding="utf-8")
