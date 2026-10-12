# ABOUTME: Tests for bartleby.yml configuration loading and validation.
# Covers schema parsing, defaults, validation errors, and edge cases.

from pathlib import Path
from typing import Any

import pytest

from bartleby.config import BartlebyConfig, ConfigError, apply_overrides, load_config
from bartleby.theme_loader import DEFAULT_THEME_NAME

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


def _load_theme_config(tmp_path: Path, theme_body: str) -> BartlebyConfig:
    """Write a minimal config whose ``theme:`` section is ``theme_body`` and load it."""
    config_path = tmp_path / "theme-config.yml"
    config_path.write_text(
        "site:\n  title: Site\n  url: https://example.com\ntheme:\n" + theme_body,
        encoding="utf-8",
    )
    return load_config(config_path)


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
    """Every native feature name is accepted without error."""
    from bartleby.theme_loader import THEME_FEATURES

    feature_lines = "".join(f"    - {name}\n" for name in sorted(THEME_FEATURES))
    config = _load_theme_config(tmp_path, "  features:\n" + feature_lines)
    assert set(config.theme.features) == THEME_FEATURES


def test_theme_features_are_the_documented_native_set() -> None:
    """The native feature vocabulary is exactly the documented eight names."""
    from bartleby.theme_loader import THEME_FEATURES

    assert {
        "search",
        "search.highlight",
        "nav.tabs",
        "nav.sidebar",
        "nav.section-index",
        "nav.back-to-top",
        "content.code.copy",
        "color-mode.toggle",
    } == THEME_FEATURES


@pytest.mark.parametrize(
    ("old_name", "new_name"),
    [
        ("navigation.tabs", "nav.tabs"),
        ("navigation.sections", "nav.sidebar"),
        ("navigation.indexes", "nav.section-index"),
        ("navigation.top", "nav.back-to-top"),
    ],
)
def test_renamed_material_feature_points_to_native_name(
    tmp_path: Path, old_name: str, new_name: str
) -> None:
    """A renamed mkdocs-material feature raises ConfigError naming the replacement."""
    with pytest.raises(ConfigError) as excinfo:
        _load_theme_config(tmp_path, f"  features:\n    - {old_name}\n")
    assert excinfo.value.key_path == "theme.features"
    assert old_name in str(excinfo.value)
    assert new_name in str(excinfo.value)


@pytest.mark.parametrize(
    "old_name",
    [
        "navigation.footer",
        "navigation.tracking",
        "content.code.annotate",
        "content.code.select",
        "content.tabs.link",
        "content.tooltips",
        "content.footnote.tooltips",
        "content.action.edit",
        "content.action.view",
        "search.suggest",
        "search.share",
    ],
)
def test_unsupported_material_feature_lists_native_features(tmp_path: Path, old_name: str) -> None:
    """A mkdocs-material feature with no native twin says so and lists the native names."""
    with pytest.raises(ConfigError) as excinfo:
        _load_theme_config(tmp_path, f"  features:\n    - {old_name}\n")
    message = str(excinfo.value)
    assert old_name in message
    assert "not a Bartleby feature" in message
    assert "nav.back-to-top" in message
    assert "color-mode.toggle" in message


def test_theme_palette_key_points_to_tokens(tmp_path: Path) -> None:
    """The removed ``palette`` key raises ConfigError pointing at ``theme.tokens``."""
    with pytest.raises(ConfigError) as excinfo:
        _load_theme_config(tmp_path, "  palette:\n    primary: indigo\n")
    assert excinfo.value.key_path == "theme.palette"
    assert "theme.tokens" in str(excinfo.value)
    assert "color.primary" in str(excinfo.value)


def test_theme_font_key_points_to_tokens(tmp_path: Path) -> None:
    """The removed ``font`` key raises ConfigError pointing at ``theme.tokens``."""
    with pytest.raises(ConfigError) as excinfo:
        _load_theme_config(tmp_path, "  font:\n    text: Inter\n")
    assert excinfo.value.key_path == "theme.font"
    assert "theme.tokens" in str(excinfo.value)
    assert "font.text" in str(excinfo.value)


def test_theme_source_defaults_to_bundled_default_name(tmp_path: Path) -> None:
    """With no name, path, or package set, the theme is the bundled default name."""
    config = _load_theme_config(tmp_path, "  logo: logo.svg\n")
    assert config.theme.name == DEFAULT_THEME_NAME
    assert config.theme.path is None
    assert config.theme.package is None


def test_theme_without_theme_section_uses_default_name(tmp_path: Path) -> None:
    """A config with no ``theme:`` section selects the bundled default name."""
    config = load_config(FIXTURES / "minimal.yml")
    assert config.theme.name == DEFAULT_THEME_NAME


@pytest.mark.parametrize(
    ("body", "attribute", "expected"),
    [
        ("  name: material\n", "name", "material"),
        ("  path: themes/mine\n", "path", "themes/mine"),
        ("  package: acme-theme\n", "package", "acme-theme"),
    ],
)
def test_theme_accepts_exactly_one_source(
    tmp_path: Path, body: str, attribute: str, expected: str
) -> None:
    """Each of name, path, and package is accepted on its own."""
    config = _load_theme_config(tmp_path, body)
    assert getattr(config.theme, attribute) == expected


@pytest.mark.parametrize(
    ("body", "keys"),
    [
        ("  name: base\n  path: themes/mine\n", ("name", "path")),
        ("  name: base\n  package: acme\n", ("name", "package")),
        ("  path: themes/mine\n  package: acme\n", ("path", "package")),
    ],
)
def test_theme_rejects_two_sources(tmp_path: Path, body: str, keys: tuple[str, str]) -> None:
    """Setting two of name, path, and package raises ConfigError naming both keys."""
    with pytest.raises(ConfigError) as excinfo:
        _load_theme_config(tmp_path, body)
    assert excinfo.value.key_path == "theme"
    for key in keys:
        assert key in str(excinfo.value)


def test_theme_tokens_parse_as_flat_string_map(tmp_path: Path) -> None:
    """``theme.tokens`` maps dotted token names to strings."""
    body = (
        "  tokens:\n"
        '    color.primary: "#283618"\n'
        '    color.accent: "#BC6C25"\n'
        "    font.text: Inter\n"
        "    font.code: JetBrains Mono\n"
        "    radius: 4px\n"
    )
    config = _load_theme_config(tmp_path, body)
    assert config.theme.tokens == {
        "color.primary": "#283618",
        "color.accent": "#BC6C25",
        "font.text": "Inter",
        "font.code": "JetBrains Mono",
        "radius": "4px",
    }


def test_theme_tokens_reject_non_string_value(tmp_path: Path) -> None:
    """A non-string token value raises ConfigError naming the token."""
    with pytest.raises(ConfigError) as excinfo:
        _load_theme_config(tmp_path, "  tokens:\n    radius: 4\n")
    assert excinfo.value.key_path == "theme.tokens.radius"


def test_theme_tokens_reject_nested_mapping(tmp_path: Path) -> None:
    """A nested token map raises ConfigError; tokens are flat dotted names."""
    with pytest.raises(ConfigError) as excinfo:
        _load_theme_config(tmp_path, "  tokens:\n    color:\n      primary: red\n")
    assert excinfo.value.key_path == "theme.tokens.color"


def test_theme_tokens_must_be_a_mapping(tmp_path: Path) -> None:
    """A non-mapping ``theme.tokens`` raises ConfigError."""
    with pytest.raises(ConfigError) as excinfo:
        _load_theme_config(tmp_path, "  tokens: red\n")
    assert excinfo.value.key_path == "theme.tokens"


def test_theme_logo_favicon_icon_packs_and_color_mode_still_parse(tmp_path: Path) -> None:
    """The unchanged appearance keys keep parsing."""
    body = (
        "  logo: img/logo.png\n"
        "  favicon: img/favicon.ico\n"
        "  icon_packs:\n    material: true\n    simple: false\n"
        "  color_mode:\n    default: dark\n"
    )
    config = _load_theme_config(tmp_path, body)
    assert config.theme.logo == "/img/logo.png"
    assert config.theme.favicon == "/img/favicon.ico"
    assert config.theme.icon_packs == {"material": True, "simple": False}
    assert config.theme.color_mode == {"default": "dark"}


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


# --- error-message contract: file + key path + fix hint --------------------


def _write_config(tmp_path: Path, body: str) -> Path:
    config_path = tmp_path / "bartleby.yml"
    config_path.write_text(body, encoding="utf-8")
    return config_path


_BASE_CONFIG = "site:\n  title: Site\n  url: https://example.com\n"


def test_unknown_top_level_key_names_file_key_and_suggestion(tmp_path: Path) -> None:
    """A misspelled top-level key is rejected with the file, the key, and a close match."""
    config_path = _write_config(
        tmp_path, _BASE_CONFIG + "content_type:\n  blog:\n    path: blog\n"
    )
    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)
    message = str(excinfo.value)
    assert "bartleby.yml" in message
    assert "content_type" in message
    assert "content_types" in message
    assert excinfo.value.key_path == "content_type"


def test_unknown_top_level_key_without_close_match_lists_valid_keys(tmp_path: Path) -> None:
    """With no near match the hint lists the valid top-level keys."""
    config_path = _write_config(tmp_path, _BASE_CONFIG + "zzzzzz: 1\n")
    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)
    assert "site" in str(excinfo.value)
    assert "taxonomies" in str(excinfo.value)


def test_missing_required_field_names_the_file_and_a_fix(tmp_path: Path) -> None:
    """A missing ``site.url`` names the config file, the key path, and what to add."""
    config_path = _write_config(tmp_path, "site:\n  title: Site\n")
    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)
    message = str(excinfo.value)
    assert "bartleby.yml" in message
    assert "site.url" in message
    assert "fix:" in message


def test_empty_config_names_the_file_and_a_fix(tmp_path: Path) -> None:
    """An empty config file says which file and what to put in it."""
    config_path = _write_config(tmp_path, "")
    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)
    message = str(excinfo.value)
    assert "bartleby.yml" in message
    assert "site" in message


def test_invalid_yaml_is_a_config_error_naming_file_and_line(tmp_path: Path) -> None:
    """A YAML syntax error becomes a ConfigError with the file and the line number."""
    config_path = _write_config(tmp_path, "site:\n  title: [unclosed\n")
    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)
    message = str(excinfo.value)
    assert "bartleby.yml" in message
    assert "line" in message


def test_unknown_metadata_field_type_names_content_type_and_field(tmp_path: Path) -> None:
    """A metadata field with an unknown ``type`` names the content type, field, and valid types."""
    body = (
        _BASE_CONFIG
        + "content_types:\n  blog:\n    path: blog\n    metadata:\n"
        + "      rating:\n        type: strng\n"
    )
    with pytest.raises(ConfigError) as excinfo:
        load_config(_write_config(tmp_path, body))
    message = str(excinfo.value)
    assert "content_types.blog.metadata.rating.type" in message
    assert "strng" in message
    assert "string" in message
    assert "bartleby.yml" in message


def test_metadata_choices_must_be_a_list(tmp_path: Path) -> None:
    """A non-list ``choices`` is rejected instead of silently ignored."""
    body = (
        _BASE_CONFIG
        + "content_types:\n  blog:\n    path: blog\n    metadata:\n"
        + "      level:\n        type: string\n        choices: easy\n"
    )
    with pytest.raises(ConfigError) as excinfo:
        load_config(_write_config(tmp_path, body))
    assert "content_types.blog.metadata.level.choices" in str(excinfo.value)


def test_undefined_taxonomy_reference_names_the_taxonomy_and_a_fix(tmp_path: Path) -> None:
    """A content type naming an undeclared taxonomy says how to declare it."""
    body = _BASE_CONFIG + "content_types:\n  blog:\n    path: blog\n    taxonomies: [tags]\n"
    with pytest.raises(ConfigError) as excinfo:
        load_config(_write_config(tmp_path, body))
    message = str(excinfo.value)
    assert "content_types.blog.taxonomies" in message
    assert "tags" in message
    assert "taxonomies:" in message


def test_color_mode_toggle_key_points_at_the_feature(tmp_path: Path) -> None:
    """``theme.color_mode.toggle`` is replaced by the ``color-mode.toggle`` feature."""
    body = _BASE_CONFIG + "theme:\n  color_mode:\n    toggle: true\n"
    with pytest.raises(ConfigError) as excinfo:
        load_config(_write_config(tmp_path, body))
    message = str(excinfo.value)
    assert "theme.color_mode.toggle" in message
    assert "color-mode.toggle" in message
    assert "theme.features" in message


def test_logo_and_favicon_become_root_relative_urls_unless_absolute(tmp_path: Path) -> None:
    """A static-relative logo path gets a leading slash; URLs and rooted paths pass through."""
    config = _load_theme_config(
        tmp_path, "  logo: img/logo.svg\n  favicon: https://cdn.example.com/icon.png\n"
    )
    assert config.theme.logo == "/img/logo.svg"
    assert config.theme.favicon == "https://cdn.example.com/icon.png"
    rooted = _load_theme_config(tmp_path, "  logo: /img/logo.svg\n")
    assert rooted.theme.logo == "/img/logo.svg"


def test_include_examples_is_rejected_as_unsupported(tmp_path: Path) -> None:
    """``ai.skills.include_examples`` has no effect, so it is a ConfigError, not silent."""
    body = _BASE_CONFIG + "ai:\n  skills:\n    include_examples: 3\n"
    with pytest.raises(ConfigError) as excinfo:
        load_config(_write_config(tmp_path, body))
    message = str(excinfo.value)
    assert "ai.skills.include_examples" in message
    assert "not yet supported" in message
    assert "fix:" in message


def test_color_mode_default_left_blank_means_no_preference(tmp_path: Path) -> None:
    """A bare ``default:`` is null, so no color mode is pinned."""
    body = _BASE_CONFIG + "theme:\n  color_mode:\n    default:\n"
    config = load_config(_write_config(tmp_path, body))

    assert config.theme.color_mode == {}


def test_apply_overrides_parses_values_as_yaml() -> None:
    """Each value is YAML-typed: text stays a string, digits become an int, and so on."""
    raw: dict[str, Any] = {"site": {"title": "Old"}}
    result = apply_overrides(
        raw,
        ["site.title=Hi", "dev_server.port=9000", "ai.llms_txt=false", "extra_css=[a.css, b.css]"],
    )
    assert result is raw
    assert result["site"]["title"] == "Hi"
    assert result["dev_server"]["port"] == 9000
    assert result["ai"]["llms_txt"] is False
    assert result["extra_css"] == ["a.css", "b.css"]


def test_apply_overrides_creates_intermediate_mappings() -> None:
    """A dotted path builds the mappings it passes through, and the last repeat wins."""
    raw: dict[str, Any] = {}
    apply_overrides(raw, ["ai.skills.style_guide=one.md", "ai.skills.style_guide=two.md"])
    assert raw == {"ai": {"skills": {"style_guide": "two.md"}}}


def test_apply_overrides_keeps_sibling_keys() -> None:
    """Setting one key leaves the keys beside it alone."""
    raw: dict[str, Any] = {"site": {"title": "T", "url": "https://x.test"}}
    apply_overrides(raw, ["site.title=New"])
    assert raw["site"] == {"title": "New", "url": "https://x.test"}


def test_apply_overrides_missing_equals_names_set_and_token() -> None:
    """A token with no ``=`` fails and the message names ``--set`` and the token."""
    with pytest.raises(ConfigError) as exc_info:
        apply_overrides({}, ["site.title"])
    message = str(exc_info.value)
    assert message.startswith("--set")
    assert "site.title" in message
    assert "key.path=value" in message


def test_apply_overrides_rejects_non_mapping_parent() -> None:
    """A path through a scalar fails instead of replacing the scalar."""
    with pytest.raises(ConfigError, match="site.title is not a mapping"):
        apply_overrides({"site": {"title": "T"}}, ["site.title.deep=1"])


def test_load_config_applies_overrides_before_validation() -> None:
    """Overrides land in the loaded config."""
    config = load_config(
        FIXTURES / "minimal.yml", overrides=["site.title=Over", "dev_server.port=9100"]
    )
    assert config.site.title == "Over"
    assert config.dev_server.port == 9100


def test_load_config_override_failure_is_labeled_set() -> None:
    """An override the validator rejects reports ``--set`` as its source, not the file."""
    with pytest.raises(ConfigError) as exc_info:
        load_config(FIXTURES / "minimal.yml", overrides=["dev_server.port=notaport"])
    message = str(exc_info.value)
    assert message.startswith("--set: dev_server.port")
    assert "minimal.yml" not in message


def test_load_config_empty_override_value_is_labeled_set() -> None:
    """``site.url=`` parses as null and the validator's complaint names ``--set``."""
    with pytest.raises(ConfigError) as exc_info:
        load_config(FIXTURES / "minimal.yml", overrides=["site.url="])
    assert str(exc_info.value).startswith("--set: site.url")


def test_load_config_file_failure_keeps_file_source_when_overrides_given() -> None:
    """A bad file value unrelated to any override still names the file."""
    with pytest.raises(ConfigError) as exc_info:
        load_config(FIXTURES / "invalid_missing_url.yml", overrides=["site.title=Fine"])
    assert "invalid_missing_url.yml" in str(exc_info.value)


def test_quoted_port_string_still_loads_as_int(tmp_path: Path) -> None:
    """A quoted port in the file keeps its pre-override int() coercion."""
    config_path = tmp_path / "port.yml"
    config_path.write_text(
        'site:\n  title: Site\n  url: https://example.com\ndev_server:\n  port: "8000"\n',
        encoding="utf-8",
    )
    assert load_config(config_path).dev_server.port == 8000


def test_file_section_error_stays_file_sourced_when_override_is_beneath(
    tmp_path: Path,
) -> None:
    """A file-only theme error is not relabeled ``--set`` by an override under it."""
    config_path = tmp_path / "theme-clash.yml"
    config_path.write_text(
        "site:\n  title: Site\n  url: https://example.com\n"
        "theme:\n  name: material\n  path: ./mine\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError) as exc_info:
        load_config(config_path, overrides=["theme.color_mode.default=dark"])
    message = str(exc_info.value)
    assert "theme-clash.yml" in message
    assert not message.startswith("--set")


def test_content_type_enabled_defaults_to_true_and_reads_false(tmp_path: Path) -> None:
    """`enabled` is True when absent and False when `enabled: false` is written."""
    config_path = tmp_path / "bartleby.yml"
    config_path.write_text(
        "site:\n  title: T\n  url: https://example.com\n"
        "content_types:\n"
        "  blog:\n    path: blog/posts\n"
        "  notes:\n    path: notes\n    enabled: false\n",
        encoding="utf-8",
    )
    config = load_config(config_path)
    assert config.content_types["blog"].enabled is True
    assert config.content_types["notes"].enabled is False
