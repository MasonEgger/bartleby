# ABOUTME: Tests for the static agent surface — schema.json + content-index.json.
# Covers artifact shape, field curation, llms.txt discovery, alternate links, collisions, toggle.

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from bartleby.agent_surface import (
    AgentSurfaceError,
    build_content_index,
    build_schema_json,
    curate_page_fields,
    write_agent_surface,
)
from bartleby.authors import Author
from bartleby.build import BuildResult, build
from bartleby.config import (
    AIConfig,
    BartlebyConfig,
    ContentTypeConfig,
    DevServerConfig,
    FeedConfig,
    MetadataFieldSchema,
    SiteConfig,
    TaxonomyConfig,
    ThemeConfig,
    load_config,
)
from bartleby.content import Page, discover_content
from bartleby.content_query import select_published
from bartleby.theme_loader import ResolvedTheme, ThemeLayer, ThemeManifest


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


def _theme(
    leaf_features: list[str] | None = None, base_features: list[str] | None = None
) -> ResolvedTheme:
    """A two-layer theme chain (stub over base) with the given manifest features."""
    leaf = ThemeManifest(name="stub", extends="base", features=leaf_features or [])
    base = ThemeManifest(name="base", features=base_features or [])
    return ResolvedTheme(
        chain=[
            ThemeLayer(name="stub", root=Path("/themes/stub"), manifest=leaf),
            ThemeLayer(name="base", root=Path("/themes/base"), manifest=base),
        ]
    )


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
    schema = build_schema_json(_pages(), _config(), _authors(), _theme())
    site = schema["site"]
    assert isinstance(site, dict)
    assert site["title"] == "Test Site"
    assert site["description"] == "A test site"
    assert site["url"] == "https://example.com"


def test_schema_json_carries_content_type_schemas() -> None:
    """schema.json describes each content type's metadata schema."""
    schema = build_schema_json(_pages(), _config(), _authors(), _theme())
    content_types = schema["content_types"]
    assert isinstance(content_types, list)
    blog = next(entry for entry in content_types if entry["content_type"] == "blog")
    optional_names = {field["name"] for field in blog["optional_fields"]}
    assert "difficulty" in optional_names


def test_schema_json_carries_taxonomy_terms() -> None:
    """schema.json lists taxonomy terms in use with counts."""
    schema = build_schema_json(_pages(), _config(), _authors(), _theme())
    taxonomies = schema["taxonomies"]
    assert isinstance(taxonomies, list)
    tags = next(tax for tax in taxonomies if tax["name"] == "tags")
    terms = {term["term"]: term["count"] for term in tags["terms"]}
    assert terms["python"] == 1  # only the published page counts


def test_schema_json_carries_public_authors() -> None:
    """schema.json includes public author data, never private fields."""
    schema = build_schema_json(_pages(), _config(), _authors(), _theme())
    authors = schema["authors"]
    assert isinstance(authors, list)
    entry = authors[0]
    assert entry["name"] == "Mason Egger"
    assert "key" not in entry


def test_schema_json_carries_resource_locations() -> None:
    """schema.json points at sitemap, llms.txt, content-index, and feeds by absolute URL."""
    schema = build_schema_json(_pages(), _config(), _authors(), _theme())
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


def test_schema_json_advertises_aggregate_rss_feed() -> None:
    """With the aggregate feed enabled and rss in formats, its URL is advertised."""
    config = _config()
    config.site.feed = FeedConfig(enabled=True, formats=["rss"])
    schema = build_schema_json(_pages(), config, _authors(), _theme())
    feeds = schema["resources"]["feeds"]  # type: ignore[index]
    feed_urls = {feed["url"] for feed in feeds}
    assert "https://example.com/feed.xml" in feed_urls
    assert "https://example.com/atom.xml" not in feed_urls


def test_schema_json_advertises_aggregate_atom_feed() -> None:
    """With the aggregate feed enabled and atom in formats, its URL is advertised."""
    config = _config()
    config.site.feed = FeedConfig(enabled=True, formats=["atom"])
    schema = build_schema_json(_pages(), config, _authors(), _theme())
    feeds = schema["resources"]["feeds"]  # type: ignore[index]
    feed_urls = {feed["url"] for feed in feeds}
    assert "https://example.com/atom.xml" in feed_urls
    assert "https://example.com/feed.xml" not in feed_urls


def test_schema_json_omits_aggregate_feed_when_disabled() -> None:
    """With the aggregate feed disabled, neither aggregate URL is advertised."""
    config = _config()
    config.site.feed = FeedConfig(enabled=False)
    schema = build_schema_json(_pages(), config, _authors(), _theme())
    feeds = schema["resources"]["feeds"]  # type: ignore[index]
    feed_urls = {feed["url"] for feed in feeds}
    assert "https://example.com/feed.xml" not in feed_urls
    assert "https://example.com/atom.xml" not in feed_urls


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


def test_schema_json_theme_block_names_the_chain_and_splits_features() -> None:
    """The theme block holds the name, the chain, and enabled/implemented/active features."""
    config = _config()
    config.theme.features = ["search", "search.highlight", "nav.sidebar"]
    theme = _theme(leaf_features=["search", "nav.tabs"], base_features=["search.highlight"])
    schema = build_schema_json(_pages(), config, _authors(), theme)
    assert schema["theme"] == {
        "name": "stub",
        "chain": ["stub", "base"],
        "features": {
            "enabled": ["nav.sidebar", "search", "search.highlight"],
            "implemented": ["nav.tabs", "search", "search.highlight"],
            "active": ["search", "search.highlight"],
        },
    }


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
        write_agent_surface([colliding], _config(), _authors(), _theme(), output_dir)


# --- toggle ----------------------------------------------------------------


def test_agent_surface_disabled_suppresses_both_artifacts(project: Path) -> None:
    """ai.agent_surface: false means neither artifact is written."""

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

    build(project / "bartleby.yml")
    schema_path = project / "site" / "schema.json"
    index_path = project / "site" / "content-index.json"
    assert schema_path.exists()
    assert index_path.exists()
    json.loads(schema_path.read_text(encoding="utf-8"))
    json.loads(index_path.read_text(encoding="utf-8"))


def test_collision_error_names_the_page_source_and_the_reserved_path(tmp_path: Path) -> None:
    """The error names the colliding source file, the artifact path, and a fix."""
    colliding = _page(name="schema", title="Collide", output_url="content-index.json")
    with pytest.raises(AgentSurfaceError) as excinfo:
        write_agent_surface([colliding], _config(), _authors(), _theme(), tmp_path)
    message = str(excinfo.value)
    assert "blog/posts/schema.md" in message
    assert "content-index.json" in message
    assert "fix:" in message


# --- integration: the docs site ----------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
_AGENT_FILES = ("llms.txt", "llms-full.txt", "schema.json", "content-index.json")


@pytest.fixture(scope="module")
def docs_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a copy of the repo's docs site and return the project directory."""
    project = tmp_path_factory.mktemp("docs_agent_surface") / "docs"
    shutil.copytree(_REPO_ROOT / "docs", project, ignore=shutil.ignore_patterns("site"))
    result = build(project / "bartleby.yml")
    assert isinstance(result, BuildResult)
    return project


def test_every_content_index_url_resolves_to_a_built_page(docs_site: Path) -> None:
    """Each content-index url and md_url maps to a file in the built site."""
    index = json.loads((docs_site / "site" / "content-index.json").read_text(encoding="utf-8"))
    assert index["count"] == len(index["content"]) > 0
    for entry in index["content"]:
        for key, filename in (("url", "index.html"), ("md_url", None)):
            path = urlsplit(entry[key]).path.strip("/")
            built = docs_site / "site" / path / filename if filename else docs_site / "site" / path
            assert built.is_file(), f"{entry[key]} has no built file at {built}"


def test_content_index_matches_the_published_pages_of_the_docs_site(docs_site: Path) -> None:
    """The index lists exactly the published pages, with no draft among them."""
    config = load_config(docs_site / "bartleby.yml")
    pages, _assets = discover_content(config, docs_site / "content")
    published = select_published(pages)
    index = json.loads((docs_site / "site" / "content-index.json").read_text(encoding="utf-8"))
    assert index["count"] == len(published)
    assert {entry["title"] for entry in index["content"]} == {page.title for page in published}


def test_schema_theme_block_matches_the_docs_config(docs_site: Path) -> None:
    """schema.json's theme block reflects docs/bartleby.yml and the resolved chain."""
    config = load_config(docs_site / "bartleby.yml")
    schema = json.loads((docs_site / "site" / "schema.json").read_text(encoding="utf-8"))
    theme = schema["theme"]
    assert theme["name"] == config.theme.name == "scrivener"
    assert theme["chain"] == ["scrivener", "base"]
    assert theme["features"]["enabled"] == sorted(config.theme.features)
    assert set(theme["features"]["active"]) == set(config.theme.features)
    assert set(theme["features"]["active"]) <= set(theme["features"]["implemented"])
    schema_types = [entry["content_type"] for entry in schema["content_types"]]
    assert schema_types == list(config.content_types)


def test_llms_txt_links_resolve_to_built_markdown_variants(docs_site: Path) -> None:
    """Every page link in llms.txt is absolute and points at a built variant."""
    body = (docs_site / "site" / "llms.txt").read_text(encoding="utf-8")
    links = re.findall(r"^- \[[^\]]+\]\((\S+)\)", body, flags=re.MULTILINE)
    assert links
    for link in links:
        assert link.startswith("https://bartleby.dev/")
        assert (docs_site / "site" / urlsplit(link).path.strip("/")).is_file()


def test_agent_outputs_are_identical_across_two_builds(project: Path, tmp_path: Path) -> None:
    """Two builds of the same input produce byte-identical agent files."""
    second = tmp_path / "second"
    shutil.copytree(project, second)
    assert isinstance(build(project / "bartleby.yml"), BuildResult)
    assert isinstance(build(second / "bartleby.yml"), BuildResult)
    for name in _AGENT_FILES:
        first_bytes = (project / "site" / name).read_bytes()
        assert first_bytes == (second / "site" / name).read_bytes(), name
        assert first_bytes
