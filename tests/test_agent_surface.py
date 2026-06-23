# ABOUTME: Tests for the static agent surface — schema.json + content-index.json.
# Covers artifact shape, field curation, llms.txt discovery, alternate links, collisions, toggle.

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from bartleby.agent_surface import (
    AgentSurfaceError,
    build_content_index,
    build_schema_json,
    curate_page_fields,
    write_agent_surface,
)
from bartleby.authors import Author
from bartleby.config import (
    AIConfig,
    BartlebyConfig,
    ContentTypeConfig,
    DevServerConfig,
    MetadataFieldSchema,
    SiteConfig,
    TaxonomyConfig,
    ThemeConfig,
)
from bartleby.content import Page


def _config(*, agent_surface: bool = True) -> BartlebyConfig:
    """A small config with one content type, two taxonomies, and a custom metadata field."""
    blog = ContentTypeConfig(
        name="blog",
        path="blog/posts",
        url_base="blog",
        url_format="{date:%Y/%m/%d}/{slug}",
        taxonomies=["tags", "categories"],
        feeds=["rss", "atom"],
        metadata={
            "difficulty": MetadataFieldSchema(
                field_type="string", required=False, choices=["beginner", "advanced"]
            ),
        },
    )
    return BartlebyConfig(
        site=SiteConfig(
            title="Test Site",
            url="https://example.com",
            description="A test site",
        ),
        nav=None,
        theme=ThemeConfig(),
        authors_file=".authors.yml",
        content_types={"blog": blog},
        taxonomies={
            "tags": TaxonomyConfig(name="tags", slug_format="{slug}"),
            "categories": TaxonomyConfig(name="categories", slug_format="{slug}"),
        },
        exclude_patterns=[],
        markdown_extensions=[],
        plugins=[],
        extra_css=[],
        extra_js=[],
        ai=AIConfig(agent_surface=agent_surface),
        dev_server=DevServerConfig(),
        config_dir=Path("/tmp/site"),
    )


def _page(
    *,
    name: str,
    title: str,
    draft: bool = False,
    output_url: str,
    description: str | None = None,
    custom: dict[str, object] | None = None,
) -> Page:
    page = Page(
        source_path=Path(f"blog/posts/{name}.md"),
        abs_source_path=Path(f"/tmp/site/content/blog/posts/{name}.md"),
        title=title,
        description=description,
        draft=draft,
        content_type_name="blog",
        taxonomy_values={"tags": ["python"]},
        author_keys=["mason"],
        raw_content="Body text here.",
    )
    page.output_url = output_url
    if custom:
        page.custom_metadata = dict(custom)
    return page


def _authors() -> dict[str, Author]:
    return {
        "mason": Author(
            key="mason",
            name="Mason Egger",
            description="Developer",
            avatar="images/mason.jpg",
            url="https://masonegger.com",
        )
    }


def _pages() -> list[Page]:
    return [
        _page(
            name="first",
            title="First Post",
            output_url="blog/posts/first/",
            description="The first one",
            custom={"difficulty": "beginner"},
        ),
        _page(name="draft", title="Draft", draft=True, output_url="blog/posts/draft/"),
    ]


# --- schema.json -----------------------------------------------------------


def test_schema_json_carries_site_identity() -> None:
    """schema.json includes site title, description, and base URL."""
    schema = build_schema_json(_pages(), _config(), _authors())
    site = schema["site"]
    assert isinstance(site, dict)
    assert site["title"] == "Test Site"
    assert site["description"] == "A test site"
    assert site["url"] == "https://example.com"


def test_schema_json_carries_content_type_schemas() -> None:
    """schema.json describes each content type's metadata schema."""
    schema = build_schema_json(_pages(), _config(), _authors())
    content_types = schema["content_types"]
    assert isinstance(content_types, list)
    blog = next(entry for entry in content_types if entry["content_type"] == "blog")
    optional_names = {field["name"] for field in blog["optional_fields"]}
    assert "difficulty" in optional_names


def test_schema_json_carries_taxonomy_terms() -> None:
    """schema.json lists taxonomy terms in use with counts."""
    schema = build_schema_json(_pages(), _config(), _authors())
    taxonomies = schema["taxonomies"]
    assert isinstance(taxonomies, list)
    tags = next(tax for tax in taxonomies if tax["name"] == "tags")
    terms = {term["term"]: term["count"] for term in tags["terms"]}
    assert terms["python"] == 1  # only the published page counts


def test_schema_json_carries_public_authors() -> None:
    """schema.json includes public author data, never private fields."""
    schema = build_schema_json(_pages(), _config(), _authors())
    authors = schema["authors"]
    assert isinstance(authors, list)
    entry = authors[0]
    assert entry["name"] == "Mason Egger"
    assert "key" not in entry


def test_schema_json_carries_resource_locations() -> None:
    """schema.json points at sitemap, llms.txt, content-index, and feeds by absolute URL."""
    schema = build_schema_json(_pages(), _config(), _authors())
    resources = schema["resources"]
    assert isinstance(resources, dict)
    assert resources["sitemap"] == "https://example.com/sitemap.xml"
    assert resources["llms_txt"] == "https://example.com/llms.txt"
    assert resources["content_index"] == "https://example.com/content-index.json"
    feeds = resources["feeds"]
    assert isinstance(feeds, list)
    feed_urls = {feed["url"] for feed in feeds}
    assert "https://example.com/blog/feed.xml" in feed_urls
    assert "https://example.com/blog/atom.xml" in feed_urls


# --- content-index.json ----------------------------------------------------


def test_content_index_lists_only_published_pages() -> None:
    """content-index.json excludes drafts."""
    index = build_content_index(_pages(), _config())
    entries = index["content"]
    assert isinstance(entries, list)
    titles = {entry["title"] for entry in entries}
    assert "First Post" in titles
    assert "Draft" not in titles


def test_content_index_entry_has_url_and_md_variant() -> None:
    """Each entry carries the page URL and the .md variant URL."""
    index = build_content_index(_pages(), _config())
    entry = index["content"][0]
    assert entry["url"] == "https://example.com/blog/posts/first/"
    assert entry["md_url"] == "https://example.com/blog/posts/first/index.md"


def test_content_index_includes_custom_schema_fields() -> None:
    """Custom metadata-schema fields (semantic) appear in the index entry."""
    index = build_content_index(_pages(), _config())
    entry = index["content"][0]
    assert entry["difficulty"] == "beginner"


# --- field curation rule ---------------------------------------------------


def test_curation_includes_semantic_fields() -> None:
    """Semantic fields included: title, description, date, type, taxonomy, authors, custom."""
    page = _page(
        name="x",
        title="Title X",
        output_url="blog/posts/x/",
        description="Desc",
        custom={"difficulty": "advanced"},
    )
    curated = curate_page_fields(page)
    assert curated["title"] == "Title X"
    assert curated["description"] == "Desc"
    assert curated["type"] == "blog"
    assert curated["tags"] == ["python"]
    assert curated["authors"] == ["mason"]
    assert curated["difficulty"] == "advanced"


def test_curation_excludes_mechanical_fields() -> None:
    """Mechanical fields (template, draft, url overrides) never reach the curated entry."""
    page = _page(name="y", title="Y", output_url="blog/posts/y/")
    page.template_override = "custom.html"
    page.url_override = "/somewhere/"
    curated = curate_page_fields(page)
    assert "template" not in curated
    assert "draft" not in curated
    assert "url_override" not in curated
    assert "url_base_override" not in curated
    assert "slug_override" not in curated


# --- llms.txt discovery section --------------------------------------------


def test_llms_txt_opens_with_machine_readable_section() -> None:
    """llms.txt opens with a section linking schema.json and content-index by absolute URL."""
    from bartleby.llm import generate_llms_txt

    body = generate_llms_txt(_pages(), _config())
    assert "https://example.com/schema.json" in body
    assert "https://example.com/content-index.json" in body
    # The machine-readable links come before the per-type content sections.
    assert body.index("schema.json") < body.index("## Blog")


# --- alternate link injection ----------------------------------------------


@pytest.fixture
def project(tmp_path: Path) -> Path:
    source = Path(__file__).parent / "fixtures" / "site"
    destination = tmp_path / "site_project"
    shutil.copytree(source, destination)
    return destination


def test_every_page_head_has_markdown_alternate_link(project: Path) -> None:
    """Every rendered page advertises its .md variant via rel=alternate in the head."""
    from bartleby.build import build

    build(project / "bartleby.yml")
    rendered = (project / "site" / "blog" / "posts" / "first-post" / "index.html").read_text(
        encoding="utf-8"
    )
    assert 'rel="alternate"' in rendered
    assert 'type="text/markdown"' in rendered
    assert "/blog/posts/first-post/index.md" in rendered


# --- collision detection ---------------------------------------------------


def test_collision_with_generated_artifact_is_a_clear_error(tmp_path: Path) -> None:
    """A user page that would overwrite schema.json is a build error with a clear message."""
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    colliding = _page(name="schema", title="Collide", output_url="schema.json")
    with pytest.raises(AgentSurfaceError, match="schema.json"):
        write_agent_surface([colliding], _config(), _authors(), output_dir)


# --- toggle ----------------------------------------------------------------


def test_agent_surface_disabled_suppresses_both_artifacts(project: Path) -> None:
    """ai.agent_surface: false means neither artifact is written."""
    from bartleby.build import build

    config_path = project / "bartleby.yml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + "\nai:\n  agent_surface: false\n",
        encoding="utf-8",
    )
    build(config_path)
    assert not (project / "site" / "schema.json").exists()
    assert not (project / "site" / "content-index.json").exists()


def test_agent_surface_enabled_writes_both_artifacts(project: Path) -> None:
    """By default both artifacts land at the site root and parse as JSON."""
    from bartleby.build import build

    build(project / "bartleby.yml")
    schema_path = project / "site" / "schema.json"
    index_path = project / "site" / "content-index.json"
    assert schema_path.exists()
    assert index_path.exists()
    json.loads(schema_path.read_text(encoding="utf-8"))
    json.loads(index_path.read_text(encoding="utf-8"))
