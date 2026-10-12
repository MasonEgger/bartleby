# ABOUTME: Tests for the comment-preserving config writer and the full-config renderer.
# Covers set_key comment and order preservation, typed scalars, and the render/load round trip.

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from bartleby.cli import _SCAFFOLD_ROOT
from bartleby.config import ConfigError, load_config
from bartleby.config_edit import (
    PLACEHOLDER_MARKER,
    example_path,
    render_full_config,
    set_key,
)
from bartleby.config_schema import CONFIG_SCHEMA

if TYPE_CHECKING:
    from pathlib import Path

SAMPLE = """\
# The site block.
site:
  title: Old  # the title
  url: https://example.com

# Theme choice.
theme:
  name: scrivener
"""


def test_set_key_changes_the_value_and_keeps_comments() -> None:
    """A comment above `site:` and the inline comment survive a value change."""
    result = set_key(SAMPLE, "site.title", "New")

    assert "# The site block." in result
    assert "# Theme choice." in result
    assert "# the title" in result
    assert yaml.safe_load(result)["site"]["title"] == "New"


def test_set_key_creates_missing_intermediate_mappings() -> None:
    """A path that does not exist yet builds the intermediate mappings."""
    result = set_key(SAMPLE, "dev_server.port", 9000)

    assert yaml.safe_load(result)["dev_server"] == {"port": 9000}


def test_set_key_creates_mappings_from_empty_text() -> None:
    """Empty text is a valid starting point."""
    assert yaml.safe_load(set_key("", "site.title", "Hi")) == {"site": {"title": "Hi"}}


def test_set_key_leaves_siblings_and_order_untouched() -> None:
    """Sibling keys keep their values, comments, and position."""
    result = set_key(SAMPLE, "site.url", "https://new.test")

    parsed = yaml.safe_load(result)
    assert list(parsed["site"]) == ["title", "url"]
    assert parsed["site"]["title"] == "Old"
    assert "title: Old  # the title" in result
    assert list(parsed) == ["site", "theme"]


def test_set_key_fills_a_key_that_holds_only_a_comment() -> None:
    """A `site:` key with a null value becomes a mapping."""
    result = set_key("# keep\nsite:\n", "site.title", "Hi")

    assert "# keep" in result
    assert yaml.safe_load(result) == {"site": {"title": "Hi"}}


def test_set_key_rejects_a_path_through_a_scalar() -> None:
    """Descending through a non-mapping value is a ConfigError naming the key."""
    with pytest.raises(ConfigError) as error:
        set_key(SAMPLE, "site.title.deeper", "x")

    assert error.value.key_path == "site.title"


def test_set_key_emits_scalars_with_their_yaml_types() -> None:
    """A bool is not quoted, an int is not quoted, a lookalike string is quoted."""
    result = set_key("", "a.flag", True)
    result = set_key(result, "a.count", 3)
    result = set_key(result, "a.word", "true")
    result = set_key(result, "a.items", ["x", "y"])

    assert "flag: true" in result
    assert "count: 3" in result
    assert yaml.safe_load(result)["a"] == {
        "flag": True,
        "count": 3,
        "word": "true",
        "items": ["x", "y"],
    }


def test_set_key_round_trips_the_scaffold(tmp_path: Path) -> None:
    """Setting one nested scaffold value leaves a config that loads with only that change."""
    original = (_SCAFFOLD_ROOT / "bartleby.yml").read_text(encoding="utf-8")
    original_path = tmp_path / "original.yml"
    original_path.write_text(original.replace("${name}", "Demo"), encoding="utf-8")
    edited_path = tmp_path / "bartleby.yml"
    edited_path.write_text(
        set_key(original_path.read_text(encoding="utf-8"), "dev_server.port", 9100),
        encoding="utf-8",
    )

    before = load_config(original_path)
    after = load_config(edited_path)

    assert after.dev_server.port == 9100
    assert before.dev_server.port != 9100
    assert after.site.title == before.site.title
    assert after.theme == before.theme
    assert after.content_types == before.content_types
    assert "port: 9100" in edited_path.read_text(encoding="utf-8")


def test_render_full_config_loads_without_error(tmp_path: Path) -> None:
    """The rendered file re-parses through load_config."""
    path = tmp_path / "bartleby.yml"
    path.write_text(render_full_config(CONFIG_SCHEMA), encoding="utf-8")

    config = load_config(path)

    assert config.site.title


def test_render_full_config_covers_every_field_with_default_and_comment() -> None:
    """Every schema field appears at its default, preceded by its description as a comment."""
    text = render_full_config(CONFIG_SCHEMA)
    parsed = yaml.safe_load(text)

    for entry in CONFIG_SCHEMA:
        node = parsed
        for segment in example_path(entry.path):
            assert segment in node, entry.path
            node = node[segment]
        if not entry.required:
            expected = list(entry.default) if isinstance(entry.default, tuple) else entry.default
            assert node == expected, entry.path
        assert f"# {entry.description}" in text, entry.path


def test_render_full_config_is_deterministic() -> None:
    """Two renders are byte-identical."""
    assert render_full_config(CONFIG_SCHEMA) == render_full_config(CONFIG_SCHEMA)


def test_render_full_config_marks_each_placeholder_in_its_comment() -> None:
    """Required fields carry an example value, and the comment above says so."""
    text = render_full_config(CONFIG_SCHEMA)
    required = [entry for entry in CONFIG_SCHEMA if entry.required]

    assert len(required) == 4
    for entry in required:
        assert f"# {entry.description} {PLACEHOLDER_MARKER}" in text, entry.path


def test_render_full_config_leaves_nav_and_color_mode_unset() -> None:
    """Auto-nav and the no-preference color mode are the defaults, so they render as null."""
    parsed = yaml.safe_load(render_full_config(CONFIG_SCHEMA))

    assert parsed["nav"] is None
    assert parsed["theme"]["color_mode"]["default"] is None


def test_set_key_new_key_keeps_the_next_comment_above_its_key() -> None:
    """A key added at the end of a mapping lands above the blank line and comment below it."""
    lines = set_key(SAMPLE, "site.description", "yes").splitlines()

    assert lines.index("  description: yes") < lines.index("# Theme choice.")
    assert lines[lines.index("theme:") - 1] == "# Theme choice."
    assert lines[lines.index("# Theme choice.") - 1] == ""


def test_set_key_new_key_leaves_the_last_key_line_comment_in_place() -> None:
    """The inline comment on the old last key stays on that key."""
    text = "site:\n  url: a  # the url\n\n# Theme choice.\ntheme:\n  name: x\n"
    lines = set_key(text, "site.title", "T").splitlines()

    assert lines[1] == "  url: a  # the url"
    assert lines[2] == "  title: T"
    assert lines[3:] == ["", "# Theme choice.", "theme:", "  name: x"]


def test_set_key_new_key_after_a_nested_mapping_keeps_the_next_comment() -> None:
    """The comment sits on the deepest last key; a new top-level-child key still clears it."""
    text = "site:\n  feed:\n    limit: 5\n\n# Theme choice.\ntheme:\n  name: x\n"
    lines = set_key(text, "site.title", "T").splitlines()

    assert lines == [
        "site:",
        "  feed:",
        "    limit: 5",
        "  title: T",
        "",
        "# Theme choice.",
        "theme:",
        "  name: x",
    ]


def test_set_key_new_content_type_keeps_the_scaffold_comment_position() -> None:
    """Adding content_types.<new>.path leaves the comment above the next scaffold key in place."""
    original = (_SCAFFOLD_ROOT / "bartleby.yml").read_text(encoding="utf-8")
    original_lines = original.splitlines()
    result_lines = set_key(original, "content_types.notes.path", "notes").splitlines()

    for index, line in enumerate(original_lines):
        if line and not line.startswith((" ", "#")) and index > 0:
            assert result_lines.index(line) > 0
            before = result_lines[result_lines.index(line) - 1]
            assert before == original_lines[index - 1], line


def test_set_key_nested_dict_value_keeps_the_next_comment_above_its_key() -> None:
    """A dict value is written as a mapping whose trailing comment slot is still found."""
    text = "site:\n  url: a\n\n# Theme choice.\ntheme:\n  name: x\n"
    block = {"path": "notes", "taxonomies": ["tags"], "feed": {"limit": 5}}
    lines = set_key(text, "site.extra", block).splitlines()

    assert lines[lines.index("theme:") - 1] == "# Theme choice."
    assert lines[lines.index("# Theme choice.") - 1] == ""
    assert lines.index("      limit: 5") < lines.index("# Theme choice.")
