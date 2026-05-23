# ABOUTME: Tests for CLI command parsing and execution.
# Covers new site, new post, build, validate, serve placeholder.

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from bartleby.cli import main
from bartleby.config import load_config

if TYPE_CHECKING:
    from pathlib import Path


def test_new_site_creates_structure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``bartleby new site mysite`` creates the standard project skeleton."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    site = tmp_path / "mysite"
    assert (site / "bartleby.yml").exists()
    assert (site / ".authors.yml").exists()
    assert (site / "content" / "index.md").exists()
    assert (site / "templates").is_dir()
    assert (site / "static").is_dir()
    assert (site / "hooks").is_dir()


def test_new_site_valid_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The scaffolded bartleby.yml loads cleanly through the config system."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    config = load_config(tmp_path / "mysite" / "bartleby.yml")
    assert config.site.title


def test_new_site_directory_exists_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Re-scaffolding into an existing site directory errors out."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mysite").mkdir()
    with pytest.raises(SystemExit):
        main(["new", "site", "mysite"])


def test_new_post_creates_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``bartleby new post 'Title' --type blog`` writes a slugified .md file."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")
    main(["new", "post", "My Cool Post", "--type", "blog"])
    target = tmp_path / "mysite" / "content" / "blog" / "posts" / "my-cool-post.md"
    assert target.exists()


def test_new_post_front_matter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A new post has title and date front matter at minimum."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")
    main(["new", "post", "Hello World", "--type", "blog"])
    body = (tmp_path / "mysite" / "content" / "blog" / "posts" / "hello-world.md").read_text()
    assert "title:" in body
    assert "date:" in body


def test_build_command_invokes_pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``bartleby build`` runs the full build and produces ``site/``."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")
    main(["build"])
    assert (tmp_path / "mysite" / "site" / "index.html").exists()


def test_validate_command_zero_exit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``bartleby validate`` exits 0 on a clean config."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")
    main(["validate"])


def test_parse_args_help_exits_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """``bartleby --help`` exits with SystemExit code 0."""
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_serve_command_constructs_devserver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``bartleby serve`` instantiates a DevServer with config-derived host/port."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")

    captured: dict[str, object] = {}

    class FakeDevServer:
        def __init__(self, *args: object, **kwargs: object) -> None:
            captured["args"] = args
            captured["kwargs"] = kwargs

        def run(self) -> None:
            captured["ran"] = True

    monkeypatch.setattr("bartleby.server.DevServer", FakeDevServer)
    main(["serve"])
    assert captured["ran"] is True
