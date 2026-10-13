# ABOUTME: Tests for the `bartleby config` command group: show, get, set, and schema.
# Covers source tagging, parsed values, write-safety of `config set`, and the schema listing.

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from bartleby.cli import main
from bartleby.config_schema import CONFIG_SCHEMA

SAMPLE = """\
# The site block.
site:
  title: Old
  url: https://example.com
"""


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A tmp_path project holding the sample ``bartleby.yml``; the cwd is moved into it."""
    (tmp_path / "bartleby.yml").write_text(SAMPLE, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _json_payload(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    """Parse the last stdout line as the command's JSON object."""
    line = [text for text in capsys.readouterr().out.splitlines() if text.strip()][-1]
    payload: dict[str, object] = json.loads(line)
    return payload


def _show_rows(capsys: pytest.CaptureFixture[str], *extra: str) -> dict[str, dict[str, object]]:
    """Run ``config show --output json`` and index its rows by dotted path."""
    main(["config", "show", "--output", "json", *extra])
    rows = _json_payload(capsys)["values"]
    assert isinstance(rows, list)
    return {row["path"]: row for row in rows}


class TestShow:
    def test_text_tags_each_value_with_its_source(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["config", "show"])

        lines = capsys.readouterr().out.splitlines()
        title_line = next(line for line in lines if line.startswith("site.title"))
        port_line = next(line for line in lines if line.startswith("dev_server.port"))
        assert "Old" in title_line
        assert title_line.endswith("(file)")
        assert port_line.endswith("(default)")

    def test_set_override_reads_as_set(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rows = _show_rows(capsys, "--set", "dev_server.port=9100")

        assert rows["dev_server.port"]["value"] == 9100
        assert rows["dev_server.port"]["source"] == "--set"

    def test_json_is_sorted_by_path_with_three_keys_per_row(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["config", "show", "--output", "json"])

        payload = _json_payload(capsys)
        rows = payload["values"]
        assert isinstance(rows, list)
        paths = [row["path"] for row in rows]
        assert paths == sorted(paths)
        assert all(set(row) == {"path", "value", "source"} for row in rows)
        assert payload["status"] == "success"

    def test_json_is_byte_stable(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        main(["config", "show", "--output", "json"])
        first = capsys.readouterr().out
        main(["config", "show", "--output", "json"])

        assert capsys.readouterr().out == first

    def test_reports_the_parsed_value_not_the_raw_yaml(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (project / "bartleby.yml").write_text(
            SAMPLE + '  feed:\n    limit: "25"\n', encoding="utf-8"
        )

        rows = _show_rows(capsys)

        assert rows["site.feed.limit"]["value"] == 25
        assert rows["site.feed.limit"]["source"] == "file"

    def test_skips_a_null_or_empty_section_that_defaults_fill_beneath(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (project / "bartleby.yml").write_text(SAMPLE + "  feed: {}\ntheme:\n", encoding="utf-8")

        rows = _show_rows(capsys)

        assert "site.feed" not in rows
        assert "theme" not in rows
        assert rows["site.feed.limit"]["source"] == "default"


class TestGet:
    def test_prints_exactly_the_resolved_value(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["config", "get", "site.title"])

        assert capsys.readouterr().out == "Old\n"

    def test_prints_a_non_string_value_as_json(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["config", "get", "dev_server.port"])

        assert capsys.readouterr().out == "8000\n"

    def test_json_carries_key_value_and_source(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["config", "get", "site.title", "--output", "json"])

        assert _json_payload(capsys) == {
            "status": "success",
            "key": "site.title",
            "value": "Old",
            "source": "file",
        }

    def test_honors_set_overrides(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        main(["config", "get", "site.title", "--set", "site.title=Over"])

        assert capsys.readouterr().out == "Over\n"

    def test_unknown_key_exits_nonzero_naming_the_key(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["config", "get", "site.nonsense"])

        assert exc.value.code != 0
        assert "site.nonsense" in capsys.readouterr().err


class TestDottedTokenNames:
    def test_path_past_a_parsed_scalar_keeps_the_raw_value(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (project / "bartleby.yml").write_text(
            SAMPLE + "theme:\n  tokens:\n    x: red\n    x.title: blue\n", encoding="utf-8"
        )

        rows = _show_rows(capsys)
        main(["config", "get", "theme.tokens.x.title"])

        assert rows["theme.tokens.x.title"]["value"] == "blue"
        assert capsys.readouterr().out == "blue\n"


class TestSet:
    def test_writes_the_value_and_keeps_the_comment_above_site(self, project: Path) -> None:
        main(["config", "set", "site.title", "X"])

        text = (project / "bartleby.yml").read_text(encoding="utf-8")
        assert text.startswith("# The site block.\nsite:")
        assert yaml.safe_load(text)["site"]["title"] == "X"

    def test_is_idempotent(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        main(["config", "set", "site.title", "X"])
        first = (project / "bartleby.yml").read_text(encoding="utf-8")
        capsys.readouterr()

        main(["config", "set", "site.title", "X", "--output", "json"])

        assert (project / "bartleby.yml").read_text(encoding="utf-8") == first
        assert _json_payload(capsys)["changed"] is False

    def test_value_is_typed_as_yaml(self, project: Path) -> None:
        main(["config", "set", "dev_server.port", "9000"])

        text = (project / "bartleby.yml").read_text(encoding="utf-8")
        assert yaml.safe_load(text)["dev_server"] == {"port": 9000}

    def test_rejects_an_invalid_value_without_writing(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["config", "set", "dev_server.port", "notaport"])

        assert exc.value.code == 1
        assert "dev_server.port" in capsys.readouterr().err
        assert (project / "bartleby.yml").read_text(encoding="utf-8") == SAMPLE

    def test_rejects_an_unknown_top_level_key_without_writing(self, project: Path) -> None:
        with pytest.raises(SystemExit):
            main(["config", "set", "sitee.title", "X"])

        assert (project / "bartleby.yml").read_text(encoding="utf-8") == SAMPLE

    @pytest.mark.parametrize(
        ("key", "suggestion"),
        [("dev_server.prot", "dev_server.port"), ("site.titel", "site.title")],
    )
    def test_rejects_an_unknown_nested_key_naming_the_closest_one(
        self, project: Path, capsys: pytest.CaptureFixture[str], key: str, suggestion: str
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["config", "set", key, "9000"])

        assert exc.value.code == 1
        error = capsys.readouterr().err
        assert f"{key}: unknown key" in error
        assert f"did you mean '{suggestion}'" in error
        assert (project / "bartleby.yml").read_text(encoding="utf-8") == SAMPLE

    @pytest.mark.parametrize("value", ["Yes", "Hello: World", "2026-01-01", "42"])
    def test_keeps_a_string_value_as_typed(
        self, project: Path, capsys: pytest.CaptureFixture[str], value: str
    ) -> None:
        """A string key is never YAML-typed: the text round-trips through set and get."""
        main(["config", "set", "site.title", value])
        capsys.readouterr()

        main(["config", "get", "site.title"])

        assert capsys.readouterr().out == f"{value}\n"
        assert yaml.safe_load((project / "bartleby.yml").read_text())["site"]["title"] == value

    def test_rejects_a_value_of_the_wrong_type_naming_the_expected_one(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["config", "set", "site.feed.enabled", "yes please"])

        assert exc.value.code == 1
        error = capsys.readouterr().err
        assert "site.feed.enabled: must be true or false" in error
        assert (project / "bartleby.yml").read_text(encoding="utf-8") == SAMPLE

    def test_empty_string_value_unsets_the_key_to_its_default(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["config", "set", "site.description", ""])
        capsys.readouterr()

        rows = _show_rows(capsys)

        assert rows["site.description"]["value"] == ""
        assert "None" not in (project / "bartleby.yml").read_text(encoding="utf-8")

    def test_keeps_yaml_typing_under_an_open_mapping(self, project: Path) -> None:
        main(["config", "set", "markwright.disable", "[twitter]"])

        text = (project / "bartleby.yml").read_text(encoding="utf-8")
        assert yaml.safe_load(text)["markwright"] == {"disable": ["twitter"]}

    def test_rejects_a_bad_markwright_section_without_writing(self, project: Path) -> None:
        """markwright validates at config-set time, so a build is never the first to fail."""
        with pytest.raises(SystemExit):
            main(["config", "set", "markwright.enable", "[nonexistent_ext]"])

        assert (project / "bartleby.yml").read_text(encoding="utf-8") == SAMPLE

    def test_date_value_under_an_open_mapping_prints_as_text(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A YAML date never reaches json.dumps as a date object."""
        main(["config", "set", "theme.tokens.release", "2026-01-01", "--output", "json"])

        assert _json_payload(capsys)["value"] == "2026-01-01"

    def test_duplicate_key_in_the_file_is_a_labeled_error(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (project / "bartleby.yml").write_text(SAMPLE + "  title: Twice\n", encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            main(["config", "set", "site.url", "https://x.test"])

        assert exc.value.code == 1
        error = capsys.readouterr().err
        assert "bartleby.yml" in error
        assert "duplicate" in error
        assert "line" in error

    def test_tab_indent_in_the_file_is_a_labeled_error(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (project / "bartleby.yml").write_text("site:\n\ttitle: T\n", encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            main(["config", "set", "site.url", "https://x.test"])

        assert exc.value.code == 1
        assert "bartleby.yml: invalid YAML at line 2" in capsys.readouterr().err

    def test_read_only_file_is_a_labeled_error(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config_path = project / "bartleby.yml"
        config_path.chmod(0o444)
        try:
            with pytest.raises(SystemExit) as exc:
                main(["config", "set", "site.title", "X"])
        finally:
            config_path.chmod(0o644)

        assert exc.value.code == 1
        assert "error [config_error] " in capsys.readouterr().err
        assert config_path.read_text(encoding="utf-8") == SAMPLE

    def test_config_pointing_at_a_directory_is_a_labeled_error(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["config", "set", "site.title", "X", "--config", "."])

        assert exc.value.code == 1
        assert "error [config_error] " in capsys.readouterr().err


class TestDottedTokenSet:
    def test_set_get_and_show_agree_on_a_dotted_token_name(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``theme.tokens.color.primary`` is one flat key, not nested mappings."""
        main(["config", "set", "theme.tokens.color.primary", "red"])
        capsys.readouterr()

        text = (project / "bartleby.yml").read_text(encoding="utf-8")
        assert yaml.safe_load(text)["theme"]["tokens"] == {"color.primary": "red"}

        main(["config", "get", "theme.tokens.color.primary"])
        assert capsys.readouterr().out == "red\n"

        rows = _show_rows(capsys)
        assert rows["theme.tokens.color.primary"] == {
            "path": "theme.tokens.color.primary",
            "value": "red",
            "source": "file",
        }

    def test_set_override_of_a_dotted_token_reads_back(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(
            [
                "config",
                "get",
                "theme.tokens.color.primary",
                "--set",
                "theme.tokens.color.primary=red",
            ]
        )

        assert capsys.readouterr().out == "red\n"


class TestSchema:
    def test_json_has_one_object_per_schema_field(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["config", "schema", "--output", "json"])

        fields = _json_payload(capsys)["fields"]
        assert isinstance(fields, list)
        assert [entry["path"] for entry in fields] == [entry.path for entry in CONFIG_SCHEMA]
        for entry in fields:
            assert {"path", "type", "default", "choices", "description"} <= set(entry)

    def test_json_carries_a_closed_set_and_a_default(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["config", "schema", "--output", "json"])

        fields = _json_payload(capsys)["fields"]
        assert isinstance(fields, list)
        port = next(entry for entry in fields if entry["path"] == "dev_server.port")
        assert port["type"] == "integer"
        assert port["default"] == 8000
        assert any(entry["choices"] for entry in fields)

    def test_text_lists_every_path(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["config", "schema"])

        out = capsys.readouterr().out
        assert all(entry.path in out for entry in CONFIG_SCHEMA)

    def test_runs_without_a_config_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)

        main(["config", "schema", "--output", "json"])

        assert "fields" in _json_payload(capsys)


class TestRoundTrip:
    def test_set_then_get_returns_the_value_and_show_marks_it_file(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["config", "set", "dev_server.port", "9100"])
        capsys.readouterr()

        main(["config", "get", "dev_server.port"])
        assert capsys.readouterr().out == "9100\n"

        rows = _show_rows(capsys)
        assert rows["dev_server.port"]["source"] == "file"
        assert rows["dev_server.port"]["value"] == 9100

    def test_show_values_are_json_serializable_for_the_full_fixture(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        full = Path(__file__).parent / "fixtures" / "configs" / "full.yml"

        main(["config", "show", "--config", str(full), "--output", "json"])

        assert _json_payload(capsys)["status"] == "success"
