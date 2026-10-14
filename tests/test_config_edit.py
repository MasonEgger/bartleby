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
    append_to_list,
    example_path,
    render_full_config,
    set_key,
    write_config_text,
)
from bartleby.config_schema import CONFIG_SCHEMA
from tests.config_helpers import uncomment_examples

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
    """A bool is not quoted, an int is not quoted, a lookalike string is quoted.

    ``Yes`` and ``on`` are strings to ruamel (YAML 1.2) but booleans to PyYAML (YAML
    1.1), so the writer quotes them for the loader.
    """
    result = set_key("", "a.flag", True)
    result = set_key(result, "a.count", 3)
    result = set_key(result, "a.word", "true")
    result = set_key(result, "a.answer", "Yes")
    result = set_key(result, "a.switch", "on")
    result = set_key(result, "a.items", ["x", "y"])

    assert "flag: true" in result
    assert "count: 3" in result
    assert 'answer: "Yes"' in result
    assert yaml.safe_load(result)["a"] == {
        "flag": True,
        "count": 3,
        "word": "true",
        "answer": "Yes",
        "switch": "on",
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
    """Every schema field appears at its default, preceded by its description as a comment.

    The ``<name>`` fields sit in the commented-out example block, which parses once
    uncommented.
    """
    text = render_full_config(CONFIG_SCHEMA)
    parsed = yaml.safe_load(uncomment_examples(text))

    for entry in CONFIG_SCHEMA:
        node = parsed
        for segment in example_path(entry.path):
            assert segment in node, entry.path
            node = node[segment]
        if not entry.required:
            expected = list(entry.default) if isinstance(entry.default, tuple) else entry.default
            assert node == expected, entry.path
        assert f"# {entry.description}" in text, entry.path


def test_render_full_config_comments_out_the_example_blocks() -> None:
    """The file as written defines no content type or taxonomy; the examples are comments."""
    text = render_full_config(CONFIG_SCHEMA)
    parsed = yaml.safe_load(text)

    assert "content_types" not in parsed
    assert "taxonomies" not in parsed
    assert "# content_types:" in text
    assert "#   example:" in text
    assert "# taxonomies:" in text


def test_render_full_config_keeps_the_base_values_and_fills_the_rest() -> None:
    """Keys the base sets keep their values; every other schema key gets its default."""
    base = (
        "site:\n  title: Mine\n  url: https://mine.test\n"
        "theme:\n  features:\n    - search\n"
        "nav:\n  - Home: index.md\n"
    )
    text = render_full_config(CONFIG_SCHEMA, base=base)
    parsed = yaml.safe_load(text)

    assert parsed["site"]["title"] == "Mine"
    assert parsed["site"]["url"] == "https://mine.test"
    assert parsed["theme"]["features"] == ["search"]
    assert parsed["nav"] == [{"Home": "index.md"}]
    assert parsed["dev_server"]["port"] == 8000
    assert "# The site title.\n" in text
    assert PLACEHOLDER_MARKER not in text.split("# content_types:")[0]


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


def test_set_key_keeps_a_comment_only_document_above_the_new_key() -> None:
    """A file holding only comments keeps them when the first key is added."""
    result = set_key("# Site config.\n# Edit me.\n", "site.title", "Hi")

    assert result.startswith("# Site config.\n# Edit me.\n")
    assert yaml.safe_load(result) == {"site": {"title": "Hi"}}


def test_set_key_keeps_a_byte_order_mark_and_crlf_line_endings() -> None:
    """The edited text starts with the same mark and uses the same line endings as before."""
    text = "\ufeffsite:\r\n  title: Old\r\n"
    result = set_key(text, "site.title", "New")

    assert result.startswith("\ufeffsite:\r\n")
    assert "\r\n" in result
    assert "\n" not in result.replace("\r\n", "")
    assert yaml.safe_load(result.removeprefix("\ufeff")) == {"site": {"title": "New"}}


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ("site:\n  title: a\n  title: b\n", "duplicate"),
        ("site:\n\ttitle: a\n", "line 2"),
    ],
)
def test_set_key_reports_a_yaml_error_with_its_line_and_the_file(text: str, problem: str) -> None:
    """A repeated key or a tab indent is a ConfigError naming the line and the source file."""
    with pytest.raises(ConfigError) as error:
        set_key(text, "site.url", "https://x.test", source="bartleby.yml")

    message = str(error.value)
    assert message.startswith("bartleby.yml: invalid YAML at line")
    assert problem in message
    assert "fix:" in message


def test_append_to_list_keeps_the_other_items_and_their_comments() -> None:
    """Appending a nav entry leaves the existing entries, comments included, in place."""
    text = "nav:\n  - Home: index.md  # the front page\n  - Docs: docs/\n"
    result = append_to_list(text, "nav", {"Blog": "blog/"})

    assert "# the front page" in result
    assert yaml.safe_load(result)["nav"] == [
        {"Home": "index.md"},
        {"Docs": "docs/"},
        {"Blog": "blog/"},
    ]


def test_append_to_list_keeps_the_next_comment_above_its_key() -> None:
    """The comment above the key after the list stays there; the new item goes before it."""
    text = (
        "nav:\n  - Home: index.md\n  - Tour: tour/index.md\n"
        "# The authors file.\nauthors_file: a.yml\n"
    )
    lines = append_to_list(text, "nav", {"Blog": "blog/"}).splitlines()

    assert lines == [
        "nav:",
        "  - Home: index.md",
        "  - Tour: tour/index.md",
        "  - Blog: blog/",
        "# The authors file.",
        "authors_file: a.yml",
    ]


def test_append_to_list_rejects_a_non_list_key() -> None:
    """Appending under a scalar is a ConfigError naming the key."""
    with pytest.raises(ConfigError) as error:
        append_to_list("site:\n  title: T\n", "site.title", "x")

    assert error.value.key_path == "site.title"


def test_write_config_text_replaces_the_file_atomically(tmp_path: Path) -> None:
    """The write lands as one rename, leaving no temp file behind."""
    config_path = tmp_path / "bartleby.yml"
    config_path.write_text("site:\n  title: Old\n", encoding="utf-8")

    write_config_text(config_path, "site:\n  title: New\n")

    assert config_path.read_text(encoding="utf-8") == "site:\n  title: New\n"
    assert [entry.name for entry in tmp_path.iterdir()] == ["bartleby.yml"]


def test_write_config_text_refuses_a_read_only_file(tmp_path: Path) -> None:
    """A read-only bartleby.yml is a ConfigError naming the file, not a traceback."""
    config_path = tmp_path / "bartleby.yml"
    config_path.write_text("site:\n  title: Old\n", encoding="utf-8")
    config_path.chmod(0o444)
    try:
        with pytest.raises(ConfigError) as error:
            write_config_text(config_path, "site:\n  title: New\n")
    finally:
        config_path.chmod(0o644)

    assert str(error.value).startswith(str(config_path))
    assert "fix:" in str(error.value)
    assert config_path.read_text(encoding="utf-8") == "site:\n  title: Old\n"


def test_write_config_text_reports_an_unwritable_directory(tmp_path: Path) -> None:
    """A directory the temp file cannot be created in is a ConfigError naming the file."""
    locked = tmp_path / "locked"
    locked.mkdir()
    config_path = locked / "bartleby.yml"
    locked.chmod(0o555)
    try:
        with pytest.raises(ConfigError) as error:
            write_config_text(config_path, "site:\n  title: New\n")
    finally:
        locked.chmod(0o755)

    assert "bartleby.yml" in str(error.value)
    assert "fix:" in str(error.value)


def test_render_full_config_leaves_nav_and_color_mode_unset() -> None:
    """Auto-nav and the no-preference color mode are the defaults, so they render as null."""
    parsed = yaml.safe_load(render_full_config(CONFIG_SCHEMA))

    assert parsed["nav"] is None
    assert parsed["theme"]["color_mode"]["default"] is None


def test_set_key_new_key_keeps_the_next_comment_above_its_key() -> None:
    """A key added at the end of a mapping lands above the blank line and comment below it."""
    lines = set_key(SAMPLE, "site.description", "notes").splitlines()

    assert lines.index("  description: notes") < lines.index("# Theme choice.")
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
