# ABOUTME: Tests for the development server core helpers.
# Network IO (HTTP + WebSocket) is intentionally not exercised in tests —
# instead we cover the rebuild dispatcher, change classification, and config plumbing.

from __future__ import annotations

import json
import shutil
import threading
import urllib.request
from typing import TYPE_CHECKING

import pytest

from bartleby.server import (
    RELOAD_SNIPPET,
    WATCHED_PATHS,
    DevServer,
    classify_change,
    inject_reload_snippet,
    is_watched,
    should_trigger_full_rebuild,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Copy the fixture site into a temp dir so server tests can run builds."""
    source = tmp_path.parent / "fixtures-source"
    if source.exists():
        shutil.rmtree(source)
    fixture = (
        tmp_path.parent.parent
        if False  # placeholder branch to silence unused-import linters
        else tmp_path
    )
    del fixture
    from pathlib import Path as _Path

    site_src = _Path(__file__).parent / "fixtures" / "site"
    destination = tmp_path / "project"
    shutil.copytree(site_src, destination)
    return destination


def test_classify_change_content() -> None:
    """Changes under ``content/`` classify as ``content``."""
    assert classify_change("content/blog/posts/a.md") == "content"


def test_classify_change_config() -> None:
    """A change to ``bartleby.yml`` classifies as ``config``."""
    assert classify_change("bartleby.yml") == "config"


def test_classify_change_template() -> None:
    """Changes under ``templates/`` or ``overrides/`` classify as ``template``."""
    assert classify_change("templates/blog/post.html") == "template"
    assert classify_change("overrides/base.html") == "template"


def test_classify_change_unknown() -> None:
    """Unrecognised paths classify as ``other``."""
    assert classify_change("random/file.txt") == "other"


def test_should_trigger_full_rebuild_for_config() -> None:
    """Config changes always force a full rebuild regardless of mode."""
    assert should_trigger_full_rebuild("config", dirty=True) is True
    assert should_trigger_full_rebuild("config", dirty=False) is True


def test_should_trigger_full_rebuild_for_template() -> None:
    """Template changes force a full rebuild even when dirty mode is on."""
    assert should_trigger_full_rebuild("template", dirty=True) is True


def test_dirty_mode_skips_full_rebuild_for_content() -> None:
    """In dirty mode, content-only changes do NOT trigger a full rebuild."""
    assert should_trigger_full_rebuild("content", dirty=True) is False


def test_devserver_initial_build(project: Path) -> None:
    """Constructing a DevServer triggers an initial build of the site."""
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0, dirty=False)
    server.build_once()
    assert (project / "site" / "index.html").exists()


def test_devserver_rebuilds_on_change(project: Path) -> None:
    """``handle_change`` re-runs the build and updates the rendered HTML."""
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0, dirty=False)
    server.build_once()
    index = project / "content" / "index.md"
    index.write_text("---\ntitle: Home\n---\n\nUpdated body marker.\n", encoding="utf-8")
    server.handle_change("content/index.md")
    rendered = (project / "site" / "index.html").read_text()
    assert "Updated body marker." in rendered


def test_devserver_includes_drafts(project: Path) -> None:
    """The dev server build pipeline always includes draft pages."""
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0, dirty=False)
    server.build_once()
    assert (project / "site" / "blog" / "posts" / "draft-post" / "index.html").exists()


# --- Step 10: live reload watcher, last-good-build, hook reload --------------


def test_all_spec_watched_paths_trigger_rebuild() -> None:
    """A change under every spec-listed watched path is recognised as watched.

    The spec's Development Server section lists ten watched roots/files:
    ``content/``, ``templates/``, ``overrides/``, ``static/``, ``hooks/``,
    ``data/``, ``shortcodes/``, ``partials/``, ``.authors.yml``, and
    ``bartleby.yml``. A change under any of them must be watched.
    """
    samples = [
        "content/index.md",
        "templates/blog/post.html",
        "overrides/base.html",
        "static/css/custom.css",
        "hooks/marker.py",
        "data/menu.yml",
        "shortcodes/note.html",
        "partials/footer.html",
        ".authors.yml",
        "bartleby.yml",
    ]
    for rel_path in samples:
        assert is_watched(rel_path), rel_path
    # Every documented root is reflected in the exported watch list.
    assert len(WATCHED_PATHS) == 10


def test_unwatched_path_does_not_trigger_rebuild() -> None:
    """A path outside the watched roots is not watched."""
    assert is_watched("site/index.html") is False
    assert is_watched("README.md") is False


def test_dispatch_change_fires_rebuild_only_for_watched_paths(project: Path) -> None:
    """``dispatch_change`` invokes the rebuild callback only on watched paths."""
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0, dirty=False)
    fired: list[str] = []
    server.dispatch_change("content/index.md", rebuild=lambda: fired.append("rebuilt"))
    server.dispatch_change("site/index.html", rebuild=lambda: fired.append("rebuilt"))
    assert fired == ["rebuilt"]


def test_rebuild_reregisters_hooks(project: Path) -> None:
    """Editing a hook file takes effect on the next rebuild without a restart."""
    hooks_dir = project / "hooks"
    hooks_dir.mkdir()
    hook = hooks_dir / "marker.py"
    hook.write_text(
        "def on_post_page(html, **_):\n    return html + '<!--MARK-ONE-->'\n",
        encoding="utf-8",
    )
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0, dirty=False)
    errors = server.rebuild()
    assert errors == []
    rendered = (project / "site" / "index.html").read_text()
    assert "<!--MARK-ONE-->" in rendered

    # Edit the hook; the next rebuild must re-register the changed handler.
    hook.write_text(
        "def on_post_page(html, **_):\n    return html + '<!--MARK-TWO-->'\n",
        encoding="utf-8",
    )
    server.rebuild()
    rendered = (project / "site" / "index.html").read_text()
    assert "<!--MARK-TWO-->" in rendered
    assert "<!--MARK-ONE-->" not in rendered


def test_failed_rebuild_keeps_last_good_build(project: Path) -> None:
    """A failed rebuild leaves the previous good output reachable and returns errors."""
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0, dirty=False)
    assert server.rebuild() == []
    good_html = (project / "site" / "index.html").read_text()

    # Introduce a page that fails metadata validation (unknown taxonomy term
    # type via a bad author reference), forcing the rebuild to raise.
    broken = project / "content" / "blog" / "posts" / "broken.md"
    broken.write_text(
        "---\ntitle: Broken\ndate: 2026-01-01\nauthors: [does-not-exist]\n---\n\nBody.\n",
        encoding="utf-8",
    )
    errors = server.rebuild()
    assert errors, "a failed rebuild must surface the collected errors"
    # The last good build is still served.
    assert (project / "site" / "index.html").read_text() == good_html


def test_reload_snippet_injected_only_in_serve_mode(project: Path) -> None:
    """The reload snippet is injected on serve but never in ``bartleby build`` output."""
    page = "<html><head></head><body><p>Hi</p></body></html>"
    served = inject_reload_snippet(page)
    assert RELOAD_SNIPPET in served
    assert "</body>" in served

    # A plain build must not contain the snippet anywhere in its output.
    from bartleby.build import build

    build(project / "bartleby.yml", include_drafts=True)
    rendered = (project / "site" / "index.html").read_text()
    assert RELOAD_SNIPPET not in rendered


def test_events_stream_emits_one_json_object_per_line(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--events`` emits one parseable JSON object per line for change + rebuild."""
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0, dirty=False)
    server.rebuild_with_events("content/index.md")
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    events = [json.loads(line) for line in lines]
    assert events[0] == {"type": "change", "path": "content/index.md"}
    assert events[-1] == {"type": "rebuild", "status": "ok"}


def test_events_stream_emits_error_object_on_failed_rebuild(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failed rebuild emits an ``error`` event with the collected failures."""
    broken = project / "content" / "blog" / "posts" / "broken.md"
    broken.write_text(
        "---\ntitle: Broken\ndate: 2026-01-01\nauthors: [does-not-exist]\n---\n\nBody.\n",
        encoding="utf-8",
    )
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0, dirty=False)
    server.rebuild_with_events("content/blog/posts/broken.md")
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    events = [json.loads(line) for line in lines]
    error_events = [event for event in events if event["type"] == "error"]
    assert error_events
    assert error_events[0]["errors"]


def _run_and_fetch_root(project: Path) -> str:
    """Start ``DevServer.run`` in a worker thread, fetch ``/``, then shut down.

    The server binds an ephemeral port. The ``ready`` callback fires once the
    socket is listening, handing back the live server so the caller can learn
    the bound port, issue a real request, and shut the server down cleanly.

    :param project: The project directory to serve.
    :returns: The decoded response body for a GET to ``/``.
    """
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0, dirty=False)
    bound: dict[str, object] = {}
    listening = threading.Event()

    def on_ready(httpd: object) -> None:
        bound["port"] = httpd.server_address[1]  # type: ignore[attr-defined]
        bound["httpd"] = httpd
        listening.set()

    worker = threading.Thread(target=lambda: server.run(ready=on_ready), daemon=True)
    worker.start()
    try:
        assert listening.wait(timeout=10), "server never started listening"
        port = bound["port"]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=10) as response:
            assert response.status == 200
            body = response.read().decode("utf-8")
    finally:
        bound["httpd"].shutdown()  # type: ignore[attr-defined]
        worker.join(timeout=10)
    assert not worker.is_alive()
    return body


def test_run_builds_and_serves_pages_over_http(project: Path) -> None:
    """``DevServer.run`` serves from ``site/`` when ``output_dir`` is unset (regression guard)."""
    body = _run_and_fetch_root(project)
    # The built index page was served, not a directory listing.
    assert "Welcome" in body
    # The build the server ran on startup wrote the output tree.
    assert (project / "site" / "index.html").exists()


def test_run_serves_configured_output_dir(project: Path) -> None:
    """With ``output_dir: public`` in bartleby.yml, ``run()`` serves from ``<project>/public/``."""
    config_path = project / "bartleby.yml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + "\noutput_dir: public\n",
        encoding="utf-8",
    )
    body = _run_and_fetch_root(project)
    # The built index page was served from public/, not a 404 or a stale/missing site/.
    assert "Welcome" in body
    assert (project / "public" / "index.html").exists()
    assert not (project / "site").exists()


def test_maybe_recompile_theme_prints_hint_when_no_binary_cached(
    project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With no cached Tailwind binary, the server prints a hint instead of downloading."""
    import bartleby.theme_compile as theme_compile

    empty_cache = tmp_path / "empty-cache"
    empty_cache.mkdir()
    monkeypatch.setattr(theme_compile, "default_cache_dir", lambda: empty_cache)
    # Ensure no tailwindcss leaks in from PATH for a deterministic miss.
    monkeypatch.setattr("shutil.which", lambda _name: None)

    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0, dirty=False)
    assert server.maybe_recompile_theme() == "hint"
    assert "bartleby theme compile" in capsys.readouterr().out
