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
    assert config.ai.skills.include_examples == 5
    assert config.ai.skills.style_guide == "content/style-guide.md"
    assert config.ai.skills.regenerate_on_build is True
    assert config.ai.agent_context.voice == "Technical but approachable. Second person."
    assert config.ai.agent_context.audience == "Python developers with 2+ years experience"
    assert "All code examples must be runnable" in config.ai.agent_context.constraints
    assert config.dev_server.host == "0.0.0.0"
    assert config.dev_server.port == 9000
    assert config.site.feed.enabled is True
    assert config.site.feed.formats == ["rss", "atom"]
    assert config.site.feed.include == ["blog"]
    assert config.site.feed.limit == 25
    assert config.site.feed.title == "Full Test Firehose"


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
    assert config.ai.skills.output_dir == ".claude/skills"
    assert config.ai.skills.include_examples == 3
    assert config.ai.skills.style_guide is None
    assert config.ai.agent_context.voice is None
    assert config.ai.agent_context.constraints == []
    assert config.extra_css == []
    assert config.extra_js == []


def test_extra_css_and_js_parsed() -> None:
    """extra_css and extra_js lists are parsed into the config."""
    config = load_config(FIXTURES / "full.yml")
    assert "extra.css" in config.extra_css
    assert "stylesheets/print.css" in config.extra_css
    assert "js/site.js" in config.extra_js


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


def test_unknown_theme_feature_is_validation_error(tmp_path: Path) -> None:
    """An unknown theme.features entry raises ConfigError naming the bad entry."""
    config_path = tmp_path / "bad-feature.yml"
    config_path.write_text(
        "site:\n"
        "  title: Site\n"
        "  url: https://example.com\n"
        "theme:\n"
        "  features:\n"
        "    - search\n"
        "    - not_a_real_feature\n"
    )
    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)
    assert "not_a_real_feature" in str(excinfo.value)
    assert excinfo.value.key_path == "theme.features"


def test_known_theme_features_are_accepted(tmp_path: Path) -> None:
    """Every documented feature name is accepted without error."""
    from bartleby.config import KNOWN_FEATURES

    feature_lines = "".join(f"    - {name}\n" for name in sorted(KNOWN_FEATURES))
    config_path = tmp_path / "all-features.yml"
    config_path.write_text(
        "site:\n  title: Site\n  url: https://example.com\ntheme:\n  features:\n" + feature_lines
    )
    config = load_config(config_path)
    assert set(config.theme.features) == KNOWN_FEATURES


def test_plugins_list_form_enables_names(tmp_path: Path) -> None:
    """The list form of ``plugins:`` populates enabled names with no disabled entries."""
    config_path = tmp_path / "plugins-list.yml"
    config_path.write_text(
        "site:\n  title: Site\n  url: https://example.com\nplugins:\n  - search\n  - rss\n"
    )
    config = load_config(config_path)
    assert config.plugins == ["search", "rss"]
    assert config.disabled_plugins == set()


def test_plugins_mapping_form_disables_named_plugin(tmp_path: Path) -> None:
    """``plugins: {<name>: false}`` records the name in ``disabled_plugins``."""
    config_path = tmp_path / "plugins-map.yml"
    config_path.write_text(
        "site:\n"
        "  title: Site\n"
        "  url: https://example.com\n"
        "plugins:\n"
        "  search: true\n"
        "  legacy-redirects: false\n"
    )
    config = load_config(config_path)
    assert config.disabled_plugins == {"legacy-redirects"}
    assert config.plugins == ["search"]


def _config_with_feed(tmp_path: Path, feed_block: str, *, with_news: bool = False) -> Path:
    """Write a config that has a blog (with feeds) plus an optional news type."""
    news = "  news:\n    path: news/posts\n    feeds: [rss]\n" if with_news else ""
    config_path = tmp_path / "feed.yml"
    config_path.write_text(
        "site:\n"
        "  title: Site\n"
        "  url: https://example.com\n"
        f"{feed_block}"
        "content_types:\n"
        "  blog:\n"
        "    path: blog/posts\n"
        "    feeds: [rss, atom]\n"
        f"{news}"
    )
    return config_path


def test_site_feed_defaults_when_absent(tmp_path: Path) -> None:
    """A config with no ``site.feed`` block gets enabled defaults."""
    config = load_config(_config_with_feed(tmp_path, ""))
    feed = config.site.feed
    assert feed.enabled is True
    assert feed.formats == ["rss", "atom"]
    assert feed.include == []
    assert feed.limit == 50
    assert feed.title is None


def test_site_feed_block_is_parsed(tmp_path: Path) -> None:
    """An explicit ``site.feed`` block overrides every default."""
    feed_block = (
        "  feed:\n"
        "    enabled: false\n"
        "    formats: [rss]\n"
        "    include: [blog]\n"
        "    limit: 20\n"
        "    title: Firehose\n"
    )
    config = load_config(_config_with_feed(tmp_path, feed_block))
    feed = config.site.feed
    assert feed.enabled is False
    assert feed.formats == ["rss"]
    assert feed.include == ["blog"]
    assert feed.limit == 20
    assert feed.title == "Firehose"


def test_site_feed_include_unknown_type_raises(tmp_path: Path) -> None:
    """An ``include`` entry naming an undefined content type is a config error."""
    feed_block = "  feed:\n    include: [ghost]\n"
    with pytest.raises(ConfigError) as excinfo:
        load_config(_config_with_feed(tmp_path, feed_block))
    assert "ghost" in str(excinfo.value)
    assert excinfo.value.key_path == "site.feed.include"


def test_site_feed_include_type_without_own_feed_raises(tmp_path: Path) -> None:
    """Including a content type that has no ``feeds`` of its own is a config error."""
    feed_block = "  feed:\n    include: [pages]\n"
    config_path = tmp_path / "feed-no-own.yml"
    config_path.write_text(
        "site:\n"
        "  title: Site\n"
        "  url: https://example.com\n"
        f"{feed_block}"
        "content_types:\n"
        "  blog:\n"
        "    path: blog/posts\n"
        "    feeds: [rss]\n"
        "  pages:\n"
        "    path: pages\n"
    )
    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)
    assert "pages" in str(excinfo.value)
    assert excinfo.value.key_path == "site.feed.include"
