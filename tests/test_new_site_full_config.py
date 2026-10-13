# ABOUTME: Tests for `bartleby new site --full-config`, the complete annotated bartleby.yml.
# Covers schema coverage, a clean load, per-option comments, the starter base, and a build.

from __future__ import annotations

import json
import logging
import warnings
from typing import TYPE_CHECKING

import pytest
import yaml

from bartleby.cli import main
from bartleby.config import load_config
from bartleby.config_schema import CONFIG_SCHEMA
from tests.config_helpers import uncomment_examples

if TYPE_CHECKING:
    from pathlib import Path


def _key_paths(node: object, prefix: tuple[str, ...] = ()) -> set[tuple[str, ...]]:
    """Return the path of every mapping key under ``node``, inner keys included."""
    if not isinstance(node, dict):
        return set()
    paths: set[tuple[str, ...]] = set()
    for key, value in node.items():
        path = (*prefix, str(key))
        paths.add(path)
        paths |= _key_paths(value, path)
    return paths


def _matches(schema_path: str, file_path: tuple[str, ...]) -> bool:
    """Whether ``file_path`` leads ``schema_path``, with ``<name>`` matching any name."""
    parts = schema_path.split(".")[: len(file_path)]
    return len(parts) == len(file_path) and all(
        part.startswith("<") or part == actual
        for part, actual in zip(parts, file_path, strict=True)
    )


def _schema_path_for(file_path: tuple[str, ...]) -> str | None:
    """Return the schema path a file key path instantiates, or None for an unknown option."""
    for field in CONFIG_SCHEMA:
        if len(field.path.split(".")) == len(file_path) and _matches(field.path, file_path):
            return field.path
    return None


def _is_section(file_path: tuple[str, ...]) -> bool:
    """Whether the schema lists only deeper paths under ``file_path`` (a section)."""
    return any(
        len(field.path.split(".")) > len(file_path) and _matches(field.path, file_path)
        for field in CONFIG_SCHEMA
    )


def _schema_paths_in(config_path: Path) -> set[str]:
    """Return the schema paths a config file's options instantiate, each of which must map.

    The commented-out example blocks count, so the ``<name>`` paths are covered.
    """
    parsed = yaml.safe_load(uncomment_examples(config_path.read_text(encoding="utf-8")))
    mapped = {
        file_path: _schema_path_for(file_path)
        for file_path in _key_paths(parsed)
        if not _is_section(file_path)
    }
    unknown = [file_path for file_path, schema_path in mapped.items() if schema_path is None]
    assert unknown == []
    return {schema_path for schema_path in mapped.values() if schema_path is not None}


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run each test from an empty temp directory."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_full_config_covers_every_schema_path(workdir: Path) -> None:
    """The generated file has a key for every path in CONFIG_SCHEMA."""
    main(["new", "site", "full", "--full-config"])
    present = _schema_paths_in(workdir / "full" / "bartleby.yml")
    missing = {field.path for field in CONFIG_SCHEMA} - present
    assert missing == set()


def test_full_config_loads_with_no_error_and_no_warning(
    workdir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """The full config loads through load_config and emits neither warnings nor log records."""
    main(["new", "site", "full", "--full-config"])
    with warnings.catch_warnings(), caplog.at_level(logging.WARNING):
        warnings.simplefilter("error")
        load_config(workdir / "full" / "bartleby.yml")
    assert caplog.records == []


def test_full_config_gives_each_option_a_description_comment(workdir: Path) -> None:
    """Each option's description appears as a comment line in the file."""
    main(["new", "site", "full", "--full-config"])
    comments = {
        line.strip().lstrip("# ")
        for line in (workdir / "full" / "bartleby.yml").read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("#")
    }
    undescribed = [
        field.path
        for field in CONFIG_SCHEMA
        if not any(comment.startswith(field.description) for comment in comments)
    ]
    assert undescribed == []


def test_minimal_config_is_a_strict_subset_of_the_full_config(workdir: Path) -> None:
    """Without the flag the minimal config is written, and it uses only a part of the schema."""
    main(["new", "site", "minimal"])
    main(["new", "site", "full", "--full-config"])
    minimal = _schema_paths_in(workdir / "minimal" / "bartleby.yml")
    full = _schema_paths_in(workdir / "full" / "bartleby.yml")
    assert minimal < full


def test_full_config_site_builds(workdir: Path) -> None:
    """A site scaffolded with --full-config builds."""
    main(["new", "site", "full", "--full-config"])
    main(["build", "--config", str(workdir / "full" / "bartleby.yml")])
    assert (workdir / "full" / "site" / "index.html").is_file()


def test_full_config_keeps_the_starter_site_name_nav_and_features(workdir: Path) -> None:
    """The starter's values are the base: its name, its nav, and its six theme features."""
    main(["new", "site", "minimal"])
    main(["new", "site", "full", "--full-config"])
    minimal = yaml.safe_load((workdir / "minimal" / "bartleby.yml").read_text(encoding="utf-8"))
    full = yaml.safe_load((workdir / "full" / "bartleby.yml").read_text(encoding="utf-8"))

    assert full["site"]["title"] == "full"
    assert full["nav"] == minimal["nav"]
    assert full["theme"]["features"] == minimal["theme"]["features"]
    assert len(full["theme"]["features"]) == 6


def test_full_config_defines_no_live_example_blocks(workdir: Path) -> None:
    """content_types, taxonomies, and metadata examples are comments, not keys."""
    main(["new", "site", "full", "--full-config"])
    text = (workdir / "full" / "bartleby.yml").read_text(encoding="utf-8")
    parsed = yaml.safe_load(text)

    assert "content_types" not in parsed
    assert "taxonomies" not in parsed
    assert "# content_types:" in text
    assert "#   example:" in text
    assert load_config(workdir / "full" / "bartleby.yml").content_types == {}


def _built_files(site: Path) -> dict[str, str]:
    return {
        str(path.relative_to(site)): path.read_text(encoding="utf-8")
        for path in sorted(site.rglob("*"))
        if path.is_file() and path.suffix in (".html", ".json", ".txt", ".xml")
    }


def test_full_config_site_builds_the_same_pages_as_the_minimal_scaffold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both scaffolds of the same name build the same files, byte for byte."""
    for flavor, flags in (("minimal", []), ("full", ["--full-config"])):
        workdir = tmp_path / flavor
        workdir.mkdir()
        monkeypatch.chdir(workdir)
        main(["new", "site", "demo", *flags])
        main(["build", "--config", str(workdir / "demo" / "bartleby.yml")])

    minimal = _built_files(tmp_path / "minimal" / "demo" / "site")
    full = _built_files(tmp_path / "full" / "demo" / "site")
    assert sorted(full) == sorted(minimal)
    assert full["index.html"] == minimal["index.html"]
    assert "bartleby:search-open" in full["index.html"]
    assert "bartleby-color-mode" in full["index.html"]
    schema = json.loads(full["schema.json"])
    assert [entry["name"] for entry in schema["content_types"]] == []
    assert full["schema.json"] == minimal["schema.json"]
