# ABOUTME: Tests for the config schema object and its drift against config.py.
# Pins field shape, allowed values, dataclass defaults, and top-level key coverage.

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

import pytest

from bartleby import config, theme_loader
from bartleby.config_schema import CONFIG_SCHEMA, ConfigField, schema_field

if TYPE_CHECKING:
    from pathlib import Path

# Schema path -> (dataclass, attribute) for every field that has a dataclass default.
DATACLASS_DEFAULTS: dict[str, tuple[type, str]] = {
    "site.description": (config.SiteConfig, "description"),
    "site.author": (config.SiteConfig, "author"),
    "site.default_image": (config.SiteConfig, "default_image"),
    "site.twitter": (config.SiteConfig, "twitter"),
    "site.feed.enabled": (config.FeedConfig, "enabled"),
    "site.feed.formats": (config.FeedConfig, "formats"),
    "site.feed.include": (config.FeedConfig, "include"),
    "site.feed.limit": (config.FeedConfig, "limit"),
    "site.feed.title": (config.FeedConfig, "title"),
    "theme.name": (config.ThemeConfig, "name"),
    "theme.path": (config.ThemeConfig, "path"),
    "theme.package": (config.ThemeConfig, "package"),
    "theme.features": (config.ThemeConfig, "features"),
    "theme.tokens": (config.ThemeConfig, "tokens"),
    "theme.icon_packs": (config.ThemeConfig, "icon_packs"),
    "theme.logo": (config.ThemeConfig, "logo"),
    "theme.favicon": (config.ThemeConfig, "favicon"),
    "content_types.<name>.url_base": (config.ContentTypeConfig, "url_base"),
    "content_types.<name>.url_format": (config.ContentTypeConfig, "url_format"),
    "content_types.<name>.taxonomies": (config.ContentTypeConfig, "taxonomies"),
    "content_types.<name>.feeds": (config.ContentTypeConfig, "feeds"),
    "content_types.<name>.readtime": (config.ContentTypeConfig, "readtime"),
    "content_types.<name>.excerpt_separator": (config.ContentTypeConfig, "excerpt_separator"),
    "content_types.<name>.pagination.enabled": (config.PaginationConfig, "enabled"),
    "content_types.<name>.pagination.per_page": (config.PaginationConfig, "per_page"),
    "content_types.<name>.pagination.url_format": (config.PaginationConfig, "url_format"),
    "content_types.<name>.metadata.<field>.required": (config.MetadataFieldSchema, "required"),
    "content_types.<name>.metadata.<field>.choices": (config.MetadataFieldSchema, "choices"),
    "output_dir": (config.BartlebyConfig, "output_dir"),
    "ai.llms_txt": (config.AIConfig, "llms_txt"),
    "ai.llms_full_txt": (config.AIConfig, "llms_full_txt"),
    "ai.markdown_variants": (config.AIConfig, "markdown_variants"),
    "ai.agent_surface": (config.AIConfig, "agent_surface"),
    "ai.robots": (config.AIConfig, "robots"),
    "ai.skills.output_dir": (config.SkillsConfig, "output_dir"),
    "ai.skills.style_guide": (config.SkillsConfig, "style_guide"),
    "ai.skills.regenerate_on_build": (config.SkillsConfig, "regenerate_on_build"),
    "ai.agent_context.voice": (config.AgentContext, "voice"),
    "ai.agent_context.audience": (config.AgentContext, "audience"),
    "ai.agent_context.constraints": (config.AgentContext, "constraints"),
    "dev_server.host": (config.DevServerConfig, "host"),
    "dev_server.port": (config.DevServerConfig, "port"),
}


def _dataclass_default(owner: type, attribute: str) -> object:
    """Read a default from a slots dataclass without a literal."""
    for dataclass_field in dataclasses.fields(owner):
        if dataclass_field.name == attribute:
            if dataclass_field.default is not dataclasses.MISSING:
                return dataclass_field.default
            assert dataclass_field.default_factory is not dataclasses.MISSING
            return dataclass_field.default_factory()
    raise AssertionError(f"{owner} has no field {attribute}")


class TestShape:
    def test_entries_are_config_fields_with_descriptions(self) -> None:
        assert len(CONFIG_SCHEMA) > 0
        for entry in CONFIG_SCHEMA:
            assert isinstance(entry, ConfigField)
            assert entry.path
            assert entry.type_name in {"string", "integer", "boolean", "list", "mapping"}
            assert isinstance(entry.repeatable, bool)
            assert entry.description.strip()
            assert "\n" not in entry.description

    def test_paths_are_unique(self) -> None:
        paths = [entry.path for entry in CONFIG_SCHEMA]
        assert len(paths) == len(set(paths))

    def test_fields_are_grouped_by_top_level_key(self) -> None:
        seen: list[str] = []
        for entry in CONFIG_SCHEMA:
            top = entry.path.split(".")[0]
            if not seen or seen[-1] != top:
                assert top not in seen, f"{top} is split into non-adjacent groups"
                seen.append(top)

    def test_repeatable_means_a_name_placeholder_in_the_path(self) -> None:
        for entry in CONFIG_SCHEMA:
            assert entry.repeatable == ("<" in entry.path)


class TestChoices:
    def test_theme_features_list_exactly_the_vocabulary(self) -> None:
        choices = schema_field("theme.features").choices
        assert choices is not None
        assert set(choices) == theme_loader.THEME_FEATURES

    def test_feed_formats(self) -> None:
        assert schema_field("site.feed.formats").choices == ("rss", "atom")

    def test_content_type_feeds(self) -> None:
        assert schema_field("content_types.<name>.feeds").choices == ("rss", "atom")

    def test_metadata_field_types(self) -> None:
        field_type = schema_field("content_types.<name>.metadata.<field>.type")
        assert field_type.choices == config.METADATA_FIELD_TYPES

    def test_color_mode_default(self) -> None:
        assert schema_field("theme.color_mode.default").choices == ("light", "dark")

    def test_open_fields_have_no_choices(self) -> None:
        assert schema_field("site.title").choices is None


class TestDefaults:
    @pytest.mark.parametrize(("path", "source"), sorted(DATACLASS_DEFAULTS.items()))
    def test_default_matches_the_dataclass(self, path: str, source: tuple[type, str]) -> None:
        assert schema_field(path).default == _dataclass_default(*source)

    def test_required_fields_have_no_default(self) -> None:
        for path in ("site.title", "site.url", "content_types.<name>.path"):
            entry = schema_field(path)
            assert entry.required is True
            assert entry.default is None

    def test_exclude_patterns_match_the_module_constant(self) -> None:
        assert schema_field("exclude_patterns").default == list(config.DEFAULT_EXCLUDE_PATTERNS)

    @pytest.mark.parametrize(
        "path",
        ["authors_file", "markdown_extensions", "plugins", "extra_css", "extra_js"],
    )
    def test_absent_top_level_keys_default_as_config_py_parses_them(
        self, path: str, tmp_path: Path
    ) -> None:
        parsed = config._parse_config({"site": {"title": "t", "url": "u"}}, tmp_path)
        assert schema_field(path).default == getattr(parsed, path)

    def test_taxonomy_slug_format_matches_config_py(self) -> None:
        parsed = config._parse_taxonomies({"tags": {}})
        assert schema_field("taxonomies.<name>.slug_format").default == parsed["tags"].slug_format


class TestLookup:
    def test_returns_entry_by_dotted_path(self) -> None:
        assert schema_field("dev_server.port").type_name == "integer"

    def test_unknown_path_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="no.such.key"):
            schema_field("no.such.key")


class TestDrift:
    def test_every_top_level_key_has_a_schema_entry(self) -> None:
        covered = {entry.path.split(".")[0] for entry in CONFIG_SCHEMA}
        missing = set(config._TOP_LEVEL_KEYS) - covered
        assert not missing, f"config.py accepts keys with no schema entry: {sorted(missing)}"

    def test_schema_names_only_accepted_top_level_keys(self) -> None:
        covered = {entry.path.split(".")[0] for entry in CONFIG_SCHEMA}
        assert covered <= set(config._TOP_LEVEL_KEYS)

    def test_drift_check_fires_for_a_new_accepted_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Mutation check: a fake key added to config.py's known set must be reported.
        monkeypatch.setattr(config, "_TOP_LEVEL_KEYS", (*config._TOP_LEVEL_KEYS, "fake_key"))
        covered = {entry.path.split(".")[0] for entry in CONFIG_SCHEMA}
        assert set(config._TOP_LEVEL_KEYS) - covered == {"fake_key"}
