# ABOUTME: Tests for schema introspection — content-type, authors, taxonomy schemas.
# Covers the derivation functions and the `bartleby schema` CLI command.

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bartleby.authors import Author
from bartleby.config import (
    BartlebyConfig,
    ContentTypeConfig,
    MetadataFieldSchema,
    PaginationConfig,
    SiteConfig,
    TaxonomyConfig,
)
from bartleby.content import Page
from bartleby.schema_introspection import (
    SchemaError,
    derive_authors_schema,
    derive_content_type_schema,
    derive_taxonomies_schema,
)


def _config() -> BartlebyConfig:
    """A small config with one content type, two taxonomies, and a metadata schema."""
    from bartleby.config import AIConfig, DevServerConfig, ThemeConfig

    blog = ContentTypeConfig(
        name="blog",
        path="blog/posts",
        url_base="blog",
        url_format="{date:%Y/%m/%d}/{slug}",
        pagination=PaginationConfig(enabled=True, per_page=10),
        taxonomies=["tags", "categories"],
        feeds=["rss", "atom"],
        readtime=True,
        excerpt_separator="<!-- more -->",
        metadata={
            "difficulty": MetadataFieldSchema(
                field_type="string", required=True, choices=["beginner", "advanced"]
            ),
            "description": MetadataFieldSchema(field_type="string", required=False),
        },
    )
    return BartlebyConfig(
        site=SiteConfig(title="Test", url="https://example.com"),
        nav=None,
        theme=ThemeConfig(),
        authors_file=".authors.yml",
        content_types={"blog": blog},
        taxonomies={
            "tags": TaxonomyConfig(name="tags", slug_format="tag:{slug}"),
            "categories": TaxonomyConfig(name="categories", slug_format="category:{slug}"),
        },
        exclude_patterns=[],
        markdown_extensions=[],
        plugins=[],
        extra_css=[],
        extra_js=[],
        ai=AIConfig(),
        dev_server=DevServerConfig(),
        config_dir=Path("/tmp/site"),
    )


def test_content_type_schema_required_and_optional_fields() -> None:
    """A content-type schema separates required from optional metadata fields."""
    schema = derive_content_type_schema("blog", _config())
    payload = schema.to_dict()

    assert payload["content_type"] == "blog"
    assert payload["path"] == "blog/posts"
    assert payload["url_base"] == "blog"

    required = payload["required_fields"]
    optional = payload["optional_fields"]
    assert isinstance(required, list)
    assert isinstance(optional, list)

    required_names = {field["name"] for field in required}
    optional_names = {field["name"] for field in optional}
    assert "difficulty" in required_names
    assert "description" in optional_names


def test_content_type_schema_carries_types_and_choices() -> None:
    """Field type and declared choices come through in the schema."""
    schema = derive_content_type_schema("blog", _config())
    payload = schema.to_dict()
    required = payload["required_fields"]
    assert isinstance(required, list)
    difficulty = next(field for field in required if field["name"] == "difficulty")
    assert difficulty["type"] == "string"
    assert difficulty["choices"] == ["beginner", "advanced"]


def test_content_type_schema_features_block() -> None:
    """The schema reports a content type's build features (pagination, feeds, readtime)."""
    schema = derive_content_type_schema("blog", _config())
    features = schema.to_dict()["features"]
    assert isinstance(features, dict)
    assert features["pagination"] is True
    assert features["per_page"] == 10
    assert features["feeds"] == ["rss", "atom"]
    assert features["readtime"] is True


def test_content_type_schema_unknown_type_raises() -> None:
    """Asking for an undefined content type is a clear error."""
    with pytest.raises(SchemaError):
        derive_content_type_schema("nope", _config())


def test_authors_schema_public_fields_only() -> None:
    """The authors schema emits public author data only, with no private keys."""
    authors = {
        "mason": Author(
            key="mason",
            name="Mason Egger",
            description="Developer Advocate",
            avatar="images/mason.jpg",
            url="https://masonegger.com",
        )
    }
    schema = derive_authors_schema(authors)
    payload = schema.to_dict()
    listed = payload["authors"]
    assert isinstance(listed, list)
    entry = listed[0]
    assert entry["id"] == "mason"
    assert entry["name"] == "Mason Egger"
    assert entry["url"] == "https://masonegger.com"
    # No raw dataclass internals or private keys leak through.
    assert "key" not in entry


def test_taxonomies_schema_lists_in_use_terms_with_counts() -> None:
    """The taxonomies schema reports each taxonomy's in-use terms and counts."""
    pages = [
        Page(
            source_path=Path("blog/posts/a.md"),
            abs_source_path=Path("/tmp/site/content/blog/posts/a.md"),
            title="A",
            content_type_name="blog",
            taxonomy_values={"tags": ["python", "web"], "categories": ["tutorials"]},
        ),
        Page(
            source_path=Path("blog/posts/b.md"),
            abs_source_path=Path("/tmp/site/content/blog/posts/b.md"),
            title="B",
            content_type_name="blog",
            taxonomy_values={"tags": ["python"]},
        ),
    ]
    schema = derive_taxonomies_schema(pages, _config())
    payload = schema.to_dict()
    taxonomies = payload["taxonomies"]
    assert isinstance(taxonomies, list)
    by_name = {tax["name"]: tax for tax in taxonomies}

    assert by_name["tags"]["slug_format"] == "tag:{slug}"
    tag_terms = {term["term"]: term["count"] for term in by_name["tags"]["terms"]}
    assert tag_terms["python"] == 2
    assert tag_terms["web"] == 1
    cat_terms = {term["term"]: term["count"] for term in by_name["categories"]["terms"]}
    assert cat_terms["tutorials"] == 1


def test_schema_results_render_json_through_output_formatter() -> None:
    """Schema results render as stable JSON through the shared output formatter."""
    from bartleby.output import render

    schema = derive_content_type_schema("blog", _config())
    rendered = render(schema, "json")
    parsed = json.loads(rendered)
    assert parsed["content_type"] == "blog"
    # JSON is emitted byte-stable (sorted keys) like the rest of the contract.
    assert rendered == json.dumps(schema.to_dict(), sort_keys=True)


def test_schema_results_render_human_text() -> None:
    """Schema results have a readable text form for human CLI use."""
    schema = derive_authors_schema(
        {"mason": Author(key="mason", name="Mason Egger", description=None, avatar=None, url=None)}
    )
    text = schema.to_text()
    assert "mason" in text
    assert "Mason Egger" in text
