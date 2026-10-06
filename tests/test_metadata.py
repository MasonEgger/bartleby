# ABOUTME: Tests for build-time metadata validation against content type schemas.
# Covers required fields, type checking, choice constraints, and author references.

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bartleby.authors import Author
from bartleby.config import ContentTypeConfig, MetadataFieldSchema, PaginationConfig
from bartleby.content import Page
from bartleby.metadata import (
    ValidationError,
    validate_all_metadata,
    validate_page_metadata,
)

if TYPE_CHECKING:
    import datetime


def _make_page(
    *,
    source: str = "blog/posts/sample.md",
    title: str = "Sample",
    content_type_name: str | None = "blog",
    custom: dict[str, str | int | bool | list[str] | datetime.date] | None = None,
    author_keys: list[str] | None = None,
) -> Page:
    """Build a minimal Page with overrides — keeps each test focused on one field."""
    return Page(
        source_path=Path(source),
        abs_source_path=Path("/abs") / source,
        title=title,
        content_type_name=content_type_name,
        custom_metadata=custom or {},
        author_keys=author_keys or [],
    )


def _make_content_type(
    *,
    metadata: dict[str, MetadataFieldSchema] | None = None,
) -> ContentTypeConfig:
    """Build a ContentTypeConfig with an explicit metadata schema."""
    return ContentTypeConfig(
        name="blog",
        path="blog/posts",
        pagination=PaginationConfig(),
        metadata=metadata or {},
    )


def _authors() -> dict[str, Author]:
    return {
        "mason": Author(
            key="mason",
            name="Mason Egger",
            description=None,
            avatar=None,
            url=None,
        ),
    }


def test_valid_metadata_passes() -> None:
    """A page satisfying every schema constraint returns no errors."""
    schema = {
        "difficulty": MetadataFieldSchema(
            field_type="string",
            required=True,
            choices=["beginner", "intermediate", "advanced"],
        ),
    }
    page = _make_page(custom={"difficulty": "intermediate"})
    errors = validate_page_metadata(page, _make_content_type(metadata=schema), _authors())
    assert errors == []


def test_missing_required_field() -> None:
    """A required field that is absent produces an error with field and file path."""
    schema = {
        "difficulty": MetadataFieldSchema(field_type="string", required=True),
    }
    page = _make_page(custom={})
    errors = validate_page_metadata(page, _make_content_type(metadata=schema), _authors())
    assert len(errors) == 1
    assert errors[0].field == "difficulty"
    assert "blog/posts/sample.md" in errors[0].file_path
    assert "required" in errors[0].message.lower()


def test_optional_field_missing_ok() -> None:
    """Missing optional fields do not raise validation errors."""
    schema = {
        "difficulty": MetadataFieldSchema(field_type="string", required=False),
    }
    page = _make_page(custom={})
    errors = validate_page_metadata(page, _make_content_type(metadata=schema), _authors())
    assert errors == []


def test_wrong_type_date() -> None:
    """A field declared as ``date`` rejects unparseable string values."""
    schema = {"published": MetadataFieldSchema(field_type="date")}
    page = _make_page(custom={"published": "not-a-date"})
    errors = validate_page_metadata(page, _make_content_type(metadata=schema), _authors())
    assert len(errors) == 1
    assert errors[0].field == "published"
    assert "date" in errors[0].message.lower()


def test_wrong_type_string() -> None:
    """A field declared as ``string`` rejects non-string values."""
    schema = {"label": MetadataFieldSchema(field_type="string")}
    page = _make_page(custom={"label": 42})
    errors = validate_page_metadata(page, _make_content_type(metadata=schema), _authors())
    assert len(errors) == 1
    assert "string" in errors[0].message.lower()


def test_wrong_type_integer() -> None:
    """A field declared as ``integer`` rejects string values."""
    schema = {"count": MetadataFieldSchema(field_type="integer")}
    page = _make_page(custom={"count": "many"})
    errors = validate_page_metadata(page, _make_content_type(metadata=schema), _authors())
    assert len(errors) == 1
    assert "integer" in errors[0].message.lower()


def test_wrong_type_boolean() -> None:
    """A field declared as ``boolean`` rejects string values."""
    schema = {"featured": MetadataFieldSchema(field_type="boolean")}
    page = _make_page(custom={"featured": "yes"})
    errors = validate_page_metadata(page, _make_content_type(metadata=schema), _authors())
    assert len(errors) == 1
    assert "boolean" in errors[0].message.lower()


def test_invalid_choice() -> None:
    """Values outside the declared choices list error with the valid options listed."""
    schema = {
        "difficulty": MetadataFieldSchema(
            field_type="string",
            choices=["beginner", "intermediate", "advanced"],
        ),
    }
    page = _make_page(custom={"difficulty": "expert"})
    errors = validate_page_metadata(page, _make_content_type(metadata=schema), _authors())
    assert len(errors) == 1
    message = errors[0].message
    assert "beginner" in message
    assert "intermediate" in message
    assert "advanced" in message


def test_valid_choice_passes() -> None:
    """A value present in ``choices`` is accepted without error."""
    schema = {
        "difficulty": MetadataFieldSchema(
            field_type="string",
            choices=["beginner", "intermediate", "advanced"],
        ),
    }
    page = _make_page(custom={"difficulty": "intermediate"})
    errors = validate_page_metadata(page, _make_content_type(metadata=schema), _authors())
    assert errors == []


def test_multiple_errors_all_reported() -> None:
    """All independent field errors surface — validation does not short-circuit."""
    schema = {
        "difficulty": MetadataFieldSchema(field_type="string", required=True),
        "count": MetadataFieldSchema(field_type="integer"),
    }
    page = _make_page(custom={"count": "many"})
    errors = validate_page_metadata(page, _make_content_type(metadata=schema), _authors())
    assert len(errors) == 2
    fields = {error.field for error in errors}
    assert fields == {"difficulty", "count"}


def test_validate_author_references() -> None:
    """Known author keys validate cleanly; unknown keys produce a clear error."""
    page_ok = _make_page(author_keys=["mason"])
    page_bad = _make_page(author_keys=["mason", "unknown"])
    assert validate_page_metadata(page_ok, _make_content_type(), _authors()) == []
    errors = validate_page_metadata(page_bad, _make_content_type(), _authors())
    assert any("unknown" in error.message for error in errors)


def test_page_without_content_type_skips_custom_validation() -> None:
    """Pages outside any content type ignore the schema entirely."""
    schema = {"difficulty": MetadataFieldSchema(field_type="string", required=True)}
    page = _make_page(content_type_name=None, custom={})
    errors = validate_page_metadata(page, _make_content_type(metadata=schema), _authors())
    assert errors == []


def test_standard_fields_validated() -> None:
    """``title`` is required for every page, including static ones."""
    page = _make_page(title="", content_type_name=None)
    errors = validate_page_metadata(page, None, _authors())
    assert any(error.field == "title" for error in errors)


def test_validate_all_metadata_dispatches_per_content_type() -> None:
    """``validate_all_metadata`` finds each page's content type config and aggregates errors."""
    from bartleby.config import (
        AIConfig,
        BartlebyConfig,
        DevServerConfig,
        SiteConfig,
        ThemeConfig,
    )

    schema = {"difficulty": MetadataFieldSchema(field_type="string", required=True)}
    config = BartlebyConfig(
        site=SiteConfig(title="t", url="u"),
        nav=None,
        theme=ThemeConfig(),
        authors_file=".authors.yml",
        content_types={"blog": _make_content_type(metadata=schema)},
        taxonomies={},
        exclude_patterns=[],
        markdown_extensions=[],
        plugins=[],
        extra_css=[],
        extra_js=[],
        ai=AIConfig(),
        dev_server=DevServerConfig(),
        config_dir=Path("/tmp"),
    )
    pages = [
        _make_page(source="blog/posts/a.md", custom={"difficulty": "intermediate"}),
        _make_page(source="blog/posts/b.md", custom={}),
    ]
    errors = validate_all_metadata(pages, config, _authors())
    assert len(errors) == 1
    assert "b.md" in errors[0].file_path
    assert isinstance(errors[0], ValidationError)
