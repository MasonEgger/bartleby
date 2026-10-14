# ABOUTME: First-run output tests: what `new site` and `serve` print for a newcomer.
# Asserts on the real text and JSON a scaffolded site and a live dev server produce.

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from bartleby.cli import main
from bartleby.server import DevServer
from tests.server_helpers import start_running_server, stop_running_server

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

STOP_HINT = "Press Ctrl+C to stop"


def test_new_site_text_lists_created_entries_and_the_next_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The text names the directory, every top-level entry, and the exact next command."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "Created site at mysite/"
    entries = {line.strip() for line in lines[1:-1]}
    assert {"bartleby.yml", "README.md", "content/"} <= entries
    assert lines[-1] == "Next: cd mysite && bartleby serve"


def test_new_site_text_notes_blog_and_full_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--blog`` and ``--full-config`` each add a note to the created list."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite", "--blog", "--full-config"])
    text = capsys.readouterr().out
    assert "content/blog/" in text
    assert "--full-config" in text


def test_new_site_json_carries_entries_and_next_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--output json`` reports the same facts as structured fields."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite", "--blog", "--output", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["path"] == "mysite/"
    assert payload["config"] == "mysite/bartleby.yml"
    assert {"bartleby.yml", "README.md", "content/"} <= set(payload["created"])
    assert payload["next_command"] == "cd mysite && bartleby serve"
    assert payload["blog"] is True
    assert payload["full_config"] is False


def test_new_site_quotes_a_name_with_a_space_in_the_next_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A name with a space is quoted so the printed command works when pasted."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "my site"])
    lines = capsys.readouterr().out.splitlines()
    assert lines[-1] == "Next: cd 'my site' && bartleby serve"
    assert (tmp_path / "my site" / "bartleby.yml").is_file()


def test_new_site_trailing_slash_does_not_double_in_any_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``demo3/`` behaves like ``demo3`` in the text, the JSON path, and the config path."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "demo3/"])
    text = capsys.readouterr().out
    assert "//" not in text
    assert text.splitlines()[0] == "Created site at demo3/"
    assert text.splitlines()[-1] == "Next: cd demo3 && bartleby serve"

    main(["new", "site", "demo4/", "--output", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["path"] == "demo4/"
    assert payload["config"] == "demo4/bartleby.yml"
    assert payload["next_command"] == "cd demo4 && bartleby serve"
    assert (tmp_path / "demo4" / "bartleby.yml").is_file()


def test_serve_startup_prints_build_summary_url_and_stop_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A live server prints the real page count and its bound (not requested) port."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    capsys.readouterr()
    server = DevServer(tmp_path / "mysite" / "bartleby.yml", host="127.0.0.1", port=0)
    worker, port = start_running_server(server)
    try:
        lines = capsys.readouterr().out.splitlines()
    finally:
        stop_running_server(server, worker)
    assert lines[0].startswith("Built ")
    assert " pages (" in lines[0]
    assert lines[-2] == f"Serving at http://127.0.0.1:{port}/"
    assert lines[-1] == STOP_HINT


def test_serve_events_startup_is_one_ready_object(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """In ``--events`` mode the startup facts arrive as a single JSON ``ready`` line."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    capsys.readouterr()
    server = DevServer(tmp_path / "mysite" / "bartleby.yml", host="127.0.0.1", port=0, events=True)
    worker, port = start_running_server(server)
    try:
        lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    finally:
        stop_running_server(server, worker)
    (ready,) = (json.loads(line) for line in lines)
    assert ready["type"] == "ready"
    assert ready["url"] == f"http://127.0.0.1:{port}/"
    assert ready["pages"] > 0
    assert ready["stop_hint"] == STOP_HINT
