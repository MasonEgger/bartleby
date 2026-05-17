# ABOUTME: Tests for bartleby.yml configuration loading and validation.
# Covers schema parsing, defaults, validation errors, and edge cases.

from pathlib import Path

import pytest

from bartleby.config import BartlebyConfig, ConfigError, load_config

FIXTURES = Path(__file__).parent / "fixtures" / "configs"


def test_load_minimal_config() -> None:
    """A minimal config (only site.title and site.url) loads with defaults applied."""
    config = load_config(FIXTURES / "minimal.yml")
    assert config.site.title == "Test Site"
    assert config.site.url == "https://example.com"


def test_load_full_config() -> None:
    """A complete config populates every section."""
    config = load_config(FIXTURES / "full.yml")
    assert config.site.title == "Full Test Site"
    assert config.site.author == "Test Author"
    assert "blog" in config.content_types
    assert "tutorials" in config.content_types
    assert "tags" in config.taxonomies
    assert "categories" in config.taxonomies
    assert isinstance(config.theme.features, list)
    assert "search" in config.theme.features
    assert config.ai.llms_txt is True
    assert config.ai.markdown_variants is True
    assert config.dev_server.host == "0.0.0.0"
    assert config.dev_server.port == 9000


def test_missing_site_title_raises() -> None:
    """Missing site.title raises ConfigError with the key path in the message."""
    with pytest.raises(ConfigError) as exc_info:
        load_config(FIXTURES / "invalid_missing_title.yml")
    assert "site.title" in str(exc_info.value)


def test_missing_site_url_raises() -> None:
    """Missing site.url raises ConfigError with the key path in the message."""
    with pytest.raises(ConfigError) as exc_info:
        load_config(FIXTURES / "invalid_missing_url.yml")
    assert "site.url" in str(exc_info.value)


def test_undefined_taxonomy_reference_raises() -> None:
    """A content type referencing an undefined taxonomy raises ConfigError."""
    with pytest.raises(ConfigError) as exc_info:
        load_config(FIXTURES / "invalid_taxonomy_ref.yml")
    message = str(exc_info.value)
    assert "series" in message


def test_default_values_applied() -> None:
    """Loading a minimal config applies all documented defaults."""
    config = load_config(FIXTURES / "minimal.yml")
    assert config.authors_file == ".authors.yml"
    assert "_drafts/**" in config.exclude_patterns
    assert config.dev_server.host == "127.0.0.1"
    assert config.dev_server.port == 8000
    assert config.ai.llms_txt is True
    assert config.ai.markdown_variants is True


def test_content_type_pagination_defaults() -> None:
    """A content type without explicit pagination gets enabled=False."""
    config = load_config(FIXTURES / "full.yml")
    blog = config.content_types["blog"]
    assert blog.pagination.enabled is True
    assert blog.pagination.per_page == 10
    tutorials = config.content_types["tutorials"]
    assert tutorials.pagination.enabled is True
    assert tutorials.pagination.per_page == 5


def test_content_type_with_metadata_schema() -> None:
    """Metadata field schemas are parsed with type, required, and choices."""
    config = load_config(FIXTURES / "full.yml")
    tutorials = config.content_types["tutorials"]
    assert "last_verified" in tutorials.metadata
    assert tutorials.metadata["last_verified"].field_type == "date"
    assert tutorials.metadata["last_verified"].required is True

    difficulty = tutorials.metadata["difficulty"]
    assert difficulty.field_type == "string"
    assert difficulty.required is False
    assert difficulty.choices == ["beginner", "intermediate", "advanced"]


def test_config_file_not_found() -> None:
    """A nonexistent config path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_config(FIXTURES / "does_not_exist.yml")


def test_empty_config_file(tmp_path: Path) -> None:
    """An empty config file raises ConfigError."""
    empty_path = tmp_path / "empty.yml"
    empty_path.write_text("")
    with pytest.raises(ConfigError):
        load_config(empty_path)


def test_config_dir_is_set() -> None:
    """The loaded config records the directory containing bartleby.yml."""
    config = load_config(FIXTURES / "minimal.yml")
    assert isinstance(config, BartlebyConfig)
    assert config.config_dir == FIXTURES
