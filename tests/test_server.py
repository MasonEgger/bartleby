# ABOUTME: Tests for the development server core helpers.
# Covers the rebuild dispatcher, change classification, config plumbing, and the
# Starlette and uvicorn server (HTTP and reload WebSocket on one port).

from __future__ import annotations

import contextlib
import json
import logging
import shutil
import socket
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from starlette.routing import Mount, WebSocketRoute
from watchdog.events import (
    DirDeletedEvent,
    DirModifiedEvent,
    DirMovedEvent,
    FileClosedEvent,
    FileClosedNoWriteEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileOpenedEvent,
)
from websockets.exceptions import ConnectionClosed

from bartleby.server import (
    RELOAD_WS_PATH,
    WATCHED_PATHS,
    DevServer,
    ServeBindError,
    _ProjectChangeHandler,
    _ReloadChannel,
    _ReloadInjectingFiles,
    build_app,
    classify_change,
    inject_reload_snippet,
    is_watched,
    reload_snippet,
)
from tests.server_helpers import start_running_server, stop_running_server

if TYPE_CHECKING:
    from collections.abc import Callable

    from watchdog.events import FileSystemEvent

    from bartleby.build import PageError


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Copy the fixture site into a temp dir so server tests can run builds."""
    destination = tmp_path / "project"
    shutil.copytree(Path(__file__).parent / "fixtures" / "site", destination)
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


def test_content_change_runs_a_full_rebuild(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every watched kind of change, content included, runs the full build."""
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    builds: list[str] = []
    monkeypatch.setattr(server, "build_once", lambda: builds.append("build"))
    for rel_path in ("content/blog/posts/first-post.md", "templates/base.html", "bartleby.yml"):
        server.handle_change(rel_path)
    assert builds == ["build", "build", "build"]


def test_devserver_initial_build(project: Path) -> None:
    """Constructing a DevServer triggers an initial build of the site."""
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    server.build_once()
    assert (project / "site" / "index.html").exists()


def test_devserver_rebuilds_on_change(project: Path) -> None:
    """``handle_change`` re-runs the build and updates the rendered HTML."""
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    server.build_once()
    index = project / "content" / "index.md"
    index.write_text("---\ntitle: Home\n---\n\nUpdated body marker.\n", encoding="utf-8")
    server.handle_change("content/index.md")
    rendered = (project / "site" / "index.html").read_text()
    assert "Updated body marker." in rendered


def test_devserver_includes_drafts(project: Path) -> None:
    """The dev server build pipeline always includes draft pages."""
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
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
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
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
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
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
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
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


@pytest.mark.parametrize("event_class", [FileOpenedEvent, FileClosedEvent, FileClosedNoWriteEvent])
def test_watcher_ignores_events_that_change_nothing(
    tmp_path: Path, event_class: type[FileSystemEvent]
) -> None:
    """Opening or closing a file is not a change.

    Regression guard: watchdog 6 on Linux reports opens and closes, and every
    rebuild reads every file, so forwarding them kept the server rebuilding
    (and every browser tab reloading) forever after the first edit.
    """
    changes: list[str] = []
    handler = _ProjectChangeHandler(tmp_path, changes.append)
    handler.dispatch(event_class(str(tmp_path / "content" / "index.md")))
    assert changes == []


def test_watcher_forwards_a_modified_file(tmp_path: Path) -> None:
    """A write is forwarded as a project-relative path."""
    changes: list[str] = []
    handler = _ProjectChangeHandler(tmp_path, changes.append)
    handler.dispatch(FileModifiedEvent(str(tmp_path / "content" / "index.md")))
    assert changes == ["content/index.md"]


def test_watcher_forwards_the_destination_of_a_move(tmp_path: Path) -> None:
    """Editors that save by renaming a temp file over the original report the original."""
    changes: list[str] = []
    handler = _ProjectChangeHandler(tmp_path, changes.append)
    handler.dispatch(
        FileMovedEvent(
            str(tmp_path / "content" / ".index.md.swp"), str(tmp_path / "content" / "index.md")
        )
    )
    assert "content/index.md" in changes


def test_reload_snippet_injected_only_in_serve_mode(project: Path) -> None:
    """The reload snippet is injected on serve but never in ``bartleby build`` output."""
    page = b"<html><head></head><body><p>Hi</p></body></html>"
    served = inject_reload_snippet(page)
    assert reload_snippet().encode() in served
    assert b"</body>" in served

    # A plain build must not contain the snippet anywhere in its output.
    from bartleby.build import build

    build(project / "bartleby.yml", include_drafts=True)
    rendered = (project / "site" / "index.html").read_text()
    assert RELOAD_WS_PATH not in rendered


def test_events_stream_emits_one_json_object_per_line(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--events`` emits one parseable JSON object per line for change + rebuild."""
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    server.rebuild_with_events("content/index.md")
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    events = [json.loads(line) for line in lines]
    assert events[0] == {"type": "change", "path": "content/index.md"}
    assert events[-1] == {"type": "rebuild", "status": "ok", "output_dir": "site/"}


def test_events_stream_emits_error_object_on_failed_rebuild(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failed rebuild emits an ``error`` event with the collected failures."""
    broken = project / "content" / "blog" / "posts" / "broken.md"
    broken.write_text(
        "---\ntitle: Broken\ndate: 2026-01-01\nauthors: [does-not-exist]\n---\n\nBody.\n",
        encoding="utf-8",
    )
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    server.rebuild_with_events("content/blog/posts/broken.md")
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    events = [json.loads(line) for line in lines]
    error_events = [event for event in events if event["type"] == "error"]
    assert error_events
    assert error_events[0]["errors"]


def test_events_stream_error_for_broken_config_has_one_relative_path_and_the_hint(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A broken ``bartleby.yml`` reports one relative path prefix and keeps the fix hint."""
    (project / "bartleby.yml").write_text("site: [unclosed\n", encoding="utf-8")
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    server.rebuild_with_events("bartleby.yml")
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    error_events = [event for event in map(json.loads, lines) if event["type"] == "error"]
    assert error_events
    (line,) = error_events[0]["errors"]
    assert line.startswith("bartleby.yml: ")
    assert line.count("bartleby.yml") == 1
    assert str(project) not in line
    assert "(fix: " in line


def _fetch(port: int, path: str = "/") -> str:
    """GET ``path`` from the local server on ``port`` and return the decoded body."""
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10) as response:
        return response.read().decode("utf-8")


def _run_and_fetch_root(project: Path) -> str:
    """Start ``DevServer.run`` in a worker thread, fetch ``/``, then shut down.

    :param project: The project directory to serve.
    :returns: The decoded response body for a GET to ``/``.
    """
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    worker, port = start_running_server(server)
    try:
        body = _fetch(port)
    finally:
        stop_running_server(server, worker)
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

    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    assert server.maybe_recompile_theme() == "hint"
    assert "bartleby theme compile" in capsys.readouterr().out


# --- Step 13: wire the watchdog observer into run() -------------------------


def test_run_rebuilds_on_watched_content_change(project: Path) -> None:
    """Editing a watched content file while ``run()`` is active rebuilds the site.

    The new content becomes visible over HTTP within a bounded wait, driven by
    a real watchdog observer rather than a direct call to a rebuild method.
    """
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    worker, port = start_running_server(server)
    try:
        (project / "content" / "index.md").write_text(
            "---\ntitle: Home\n---\n\nWatcher rebuild marker.\n", encoding="utf-8"
        )
        deadline = time.monotonic() + 10
        body = ""
        last_error: OSError | None = None
        while time.monotonic() < deadline:
            try:
                body = _fetch(port)
            except OSError as error:
                # The first fetch can land before the rebuild finished. Keep polling.
                last_error = error
            else:
                if "Watcher rebuild marker." in body:
                    break
            time.sleep(0.1)
        assert "Watcher rebuild marker." in body, f"last error: {last_error!r}"
    finally:
        stop_running_server(server, worker)


def test_run_ignores_changes_outside_watched_paths(project: Path) -> None:
    """A change to an unwatched path does not trigger a rebuild while ``run()`` is active.

    The watcher pipeline is instrumented by wrapping ``server.rebuild`` so the
    test observes the rebuild callback directly rather than sleeping blind
    against ambiguous HTTP content.
    """
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    calls: list[list[PageError]] = []
    original_rebuild = server.rebuild

    def counting_rebuild() -> list[PageError]:
        result = original_rebuild()
        calls.append(result)
        return result

    server.rebuild = counting_rebuild  # type: ignore[method-assign]

    worker, port = start_running_server(server)
    try:
        # A file inside the output dir, and a project-root README, are both
        # outside WATCHED_PATHS.
        (project / "site" / "index.html").write_text("tampered", encoding="utf-8")
        (project / "README.md").write_text("not watched\n", encoding="utf-8")
        time.sleep(1.0)
        assert calls == [], "an unwatched path change must not trigger a rebuild"

        # Prove the watcher pipeline is alive: a watched change still fires one.
        (project / "content" / "index.md").write_text(
            "---\ntitle: Home\n---\n\nWatched after all.\n", encoding="utf-8"
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not calls:
            time.sleep(0.05)
        assert calls, "the watcher pipeline appears dead"
    finally:
        stop_running_server(server, worker)


# --- Step 14: serve the reload snippet and the WebSocket channel -----------


def test_run_serves_html_with_reload_snippet(project: Path) -> None:
    """HTML served by ``run()`` carries the live-reload snippet (serve mode only)."""
    body = _run_and_fetch_root(project)
    assert RELOAD_WS_PATH in body


def test_reload_snippet_targets_the_serving_port() -> None:
    """The snippet connects to ``location.host`` on the reload path, with no separate port."""
    snippet = reload_snippet()
    assert "location.host+" in snippet
    assert "location.hostname" not in snippet
    assert RELOAD_WS_PATH in snippet


def test_app_mounts_the_reload_socket_beside_the_site(project: Path) -> None:
    """One app carries both the reload WebSocket route and the static site mount."""
    app = build_app(_ReloadInjectingFiles(directory=project, html=True), _ReloadChannel())
    paths = {route.path for route in app.routes if isinstance(route, WebSocketRoute)}
    assert paths == {RELOAD_WS_PATH}
    assert any(isinstance(route, Mount) and route.path == "" for route in app.routes)


def test_served_html_carries_the_snippet_on_the_serving_port(project: Path) -> None:
    """Served HTML holds the snippet that targets the page's own host and port.

    Regression guard: the snippet once pointed at a separate hub port, so a
    page behind a proxy or forwarded port never reached the reload channel.
    """
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    worker, port = start_running_server(server)
    try:
        body = _fetch(port)
    finally:
        stop_running_server(server, worker)
    assert reload_snippet() in body


def test_run_serves_static_assets_directory_indexes_and_the_404_page(project: Path) -> None:
    """Assets keep their content type, directories resolve to index.html, misses get 404."""
    (project / "static").mkdir(exist_ok=True)
    (project / "static" / "probe.css").write_text("body{color:red}\n", encoding="utf-8")
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    worker, port = start_running_server(server)
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/probe.css", timeout=10) as css:
            assert css.headers.get_content_type() == "text/css"
            assert RELOAD_WS_PATH not in css.read().decode("utf-8")
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/blog/", timeout=10) as listing:
            assert listing.headers.get_content_type() == "text/html"
        with pytest.raises(urllib.error.HTTPError) as missing:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/no/such/page/", timeout=10)
        assert missing.value.code == 404
    finally:
        stop_running_server(server, worker)


def test_idle_connection_does_not_stall_other_requests(project: Path) -> None:
    """A connection that never sends a request must not block pages for anyone else.

    Browsers (mobile Safari especially) open speculative connections and leave
    them idle; a single-threaded server waits on that socket and every other
    request hangs.
    """
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    worker, port = start_running_server(server)
    try:
        with (
            socket.create_connection(("127.0.0.1", port), timeout=10),
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as response,
        ):
            assert response.status == 200
    finally:
        stop_running_server(server, worker)


def test_cli_build_output_is_snippet_free(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``bartleby build`` through the real CLI entry point never emits the reload snippet."""
    from bartleby.cli import main

    monkeypatch.chdir(project)
    main(["build"])
    rendered = (project / "site" / "index.html").read_text(encoding="utf-8")
    assert RELOAD_WS_PATH not in rendered


def test_reload_round_trip_on_one_port(project: Path) -> None:
    """A page and the reload socket share a port, and a content edit signals a reload."""
    from websockets.sync.client import connect

    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    worker, port = start_running_server(server)
    try:
        assert "Welcome" in _fetch(port)
        with connect(f"ws://127.0.0.1:{port}{RELOAD_WS_PATH}", open_timeout=10) as client:
            (project / "content" / "index.md").write_text(
                "---\ntitle: Home\n---\n\nReload broadcast marker.\n", encoding="utf-8"
            )
            message = client.recv(timeout=10)
            assert message == "reload"
        assert "Reload broadcast marker." in _fetch(port)
    finally:
        stop_running_server(server, worker)


def test_broadcast_survives_concurrent_client_churn(
    project: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Broadcasting from the watcher thread while sockets connect and drop never errors.

    The client set belongs to the server's event loop, so a broadcast from
    another thread must hand off to that loop instead of touching the set.
    Hammering connects and drops against repeated broadcasts must leave the
    server alive and answering requests, and no broadcast may fail (a failure
    surfaces as an error log from the broadcast's done-callback).
    """
    from websockets.sync.client import connect

    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    worker, port = start_running_server(server)
    channel = server._channel
    assert channel is not None
    stop = threading.Event()

    def churn_clients() -> None:
        while not stop.is_set():
            with (
                contextlib.suppress(OSError, ConnectionClosed),
                connect(f"ws://127.0.0.1:{port}{RELOAD_WS_PATH}", open_timeout=2),
            ):
                pass

    def broadcast_repeatedly() -> None:
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            channel.broadcast_reload()
        stop.set()

    try:
        churners = [threading.Thread(target=churn_clients) for _ in range(4)]
        for churner in churners:
            churner.start()
        broadcaster = threading.Thread(target=broadcast_repeatedly)
        broadcaster.start()
        broadcaster.join(timeout=10)
        for churner in churners:
            churner.join(timeout=10)
        assert "Welcome" in _fetch(port)
    finally:
        stop_running_server(server, worker)
    assert not [record for record in caplog.records if record.levelno >= logging.ERROR]


def test_run_raises_when_the_port_is_in_use(project: Path) -> None:
    """A bound port fails loudly with ``ServeBindError`` instead of serving nothing."""
    with socket.create_server(("127.0.0.1", 0)) as occupied:
        port = occupied.getsockname()[1]
        server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=port)
        with pytest.raises(ServeBindError) as excinfo:
            server.run()
    assert excinfo.value.port == port


def test_run_survives_broken_front_matter_and_rebuilds_on_the_fix(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Broken front matter reports an error, keeps the last page, and the next edit rebuilds."""
    from websockets.sync.client import connect

    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0, events=True)
    worker, port = start_running_server(server)
    page = project / "content" / "index.md"
    try:
        good_body = _fetch(port)

        # An unterminated flow sequence is invalid YAML, which raises ContentError.
        page.write_text("---\ntitle: [unclosed\n---\n\nBody.\n", encoding="utf-8")
        deadline = time.monotonic() + 10
        events_seen = ""
        while time.monotonic() < deadline and '"type": "error"' not in events_seen:
            events_seen += capsys.readouterr().out
            time.sleep(0.05)
        assert '"type": "error"' in events_seen, "the broken page never produced an error event"
        assert _fetch(port) == good_body

        # The watcher must still be alive: a valid edit rebuilds and broadcasts a reload.
        with connect(f"ws://127.0.0.1:{port}{RELOAD_WS_PATH}", open_timeout=10) as client:
            page.write_text(
                "---\ntitle: Home\n---\n\nRecovered after broken front matter.\n",
                encoding="utf-8",
            )
            assert client.recv(timeout=10) == "reload"
        assert "Recovered after broken front matter." in _fetch(port)
    finally:
        stop_running_server(server, worker)


def test_run_retains_last_good_build_after_watcher_triggered_failure(project: Path) -> None:
    """A failed watcher-triggered rebuild keeps serving the last good build."""
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    calls: list[list[PageError]] = []
    original_rebuild = server.rebuild

    def counting_rebuild() -> list[PageError]:
        result = original_rebuild()
        calls.append(result)
        return result

    server.rebuild = counting_rebuild  # type: ignore[method-assign]

    worker, port = start_running_server(server)
    try:
        good_body = _fetch(port)

        # A page that fails metadata validation (unknown author reference)
        # forces the watcher-triggered rebuild to collect errors.
        broken = project / "content" / "blog" / "posts" / "broken.md"
        broken.write_text(
            "---\ntitle: Broken\ndate: 2026-01-01\nauthors: [does-not-exist]\n---\n\nBody.\n",
            encoding="utf-8",
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not calls:
            time.sleep(0.05)
        assert calls, "the watcher never attempted a rebuild for the broken page"
        assert calls[-1], "the rebuild attempt should have collected errors"

        assert _fetch(port) == good_body
    finally:
        stop_running_server(server, worker)


# --- Rebuild reporting, coalescing, theme watching, and output handling ------


def _events_until(capsys: pytest.CaptureFixture[str], marker: str, timeout: float = 10) -> str:
    """Collect stdout until ``marker`` appears in it or ``timeout`` seconds pass."""
    deadline = time.monotonic() + timeout
    seen = ""
    while time.monotonic() < deadline and marker not in seen:
        seen += capsys.readouterr().out
        time.sleep(0.05)
    return seen


def _wait_for(condition: Callable[[], bool], timeout: float = 10) -> bool:
    """Poll ``condition`` until it holds or ``timeout`` seconds pass."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.05)
    return condition()


def _count_rebuilds(server: DevServer) -> list[list[PageError]]:
    """Wrap ``server.rebuild`` so a test can count the rebuilds the watcher ran."""
    calls: list[list[PageError]] = []
    original_rebuild = server.rebuild

    def counting_rebuild() -> list[PageError]:
        result = original_rebuild()
        calls.append(result)
        return result

    server.rebuild = counting_rebuild  # type: ignore[method-assign]
    return calls


def test_rebuild_reports_a_hook_syntax_error_as_a_page_error(project: Path) -> None:
    """An exception outside the labeled set becomes a page error naming its type."""
    hooks_dir = project / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "broken.py").write_text("def on_post_page(html, **_)\n    return html\n")
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)

    errors = server.rebuild()

    assert len(errors) == 1
    assert "SyntaxError" in errors[0].message
    assert errors[0].file_path == "hooks/broken.py"


def test_run_survives_a_hook_syntax_error_and_rebuilds_on_the_fix(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A hook that fails to import is an ``error`` event, and the fixed hook rebuilds."""
    from websockets.sync.client import connect

    hooks_dir = project / "hooks"
    hooks_dir.mkdir()
    hook = hooks_dir / "marker.py"
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0, events=True)
    worker, port = start_running_server(server)
    try:
        hook.write_text("def on_post_page(html, **_)\n    return html\n", encoding="utf-8")
        events_seen = _events_until(capsys, '"type": "error"')
        assert "SyntaxError" in events_seen
        assert "Welcome" in _fetch(port)

        with connect(f"ws://127.0.0.1:{port}{RELOAD_WS_PATH}", open_timeout=10) as client:
            hook.write_text(
                "def on_post_page(html, **_):\n    return html + '<!--HOOK-FIXED-->'\n",
                encoding="utf-8",
            )
            assert client.recv(timeout=10) == "reload"
        assert "<!--HOOK-FIXED-->" in _fetch(port)
    finally:
        stop_running_server(server, worker)


def test_run_survives_a_briefly_missing_config(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A config file that vanishes mid-save is an ``error`` event; its return rebuilds."""
    config_path = project / "bartleby.yml"
    config_text = config_path.read_text(encoding="utf-8")
    server = DevServer(config_path, host="127.0.0.1", port=0, events=True)
    worker, port = start_running_server(server)
    try:
        config_path.unlink()
        events_seen = _events_until(capsys, '"type": "error"')
        assert "bartleby.yml" in events_seen
        assert "Welcome" in _fetch(port)

        config_path.write_text(config_text, encoding="utf-8")
        events_seen = _events_until(capsys, '"type": "rebuild"')
        assert '"type": "rebuild"' in events_seen
    finally:
        stop_running_server(server, worker)


def test_run_prints_rebuild_outcomes_in_text_mode(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without ``--events``, a failed rebuild prints its errors and a good one prints a summary."""
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    worker, _port = start_running_server(server)
    page = project / "content" / "index.md"
    try:
        page.write_text("---\ntitle: [unclosed\n---\n\nBody.\n", encoding="utf-8")
        deadline = time.monotonic() + 10
        stderr_seen = ""
        while time.monotonic() < deadline and "error: " not in stderr_seen:
            stderr_seen += capsys.readouterr().err
            time.sleep(0.05)
        assert stderr_seen.startswith("error: index.md: ")
        assert "fix:" in stderr_seen

        page.write_text("---\ntitle: Home\n---\n\nFixed again.\n", encoding="utf-8")
        stdout_seen = _events_until(capsys, "Rebuilt ")
        assert "Rebuilt " in stdout_seen
        assert " pages in " in stdout_seen
        assert " ms" in stdout_seen
    finally:
        stop_running_server(server, worker)


def test_served_html_that_is_not_utf8_still_gets_the_snippet(project: Path) -> None:
    """A Latin-1 page is served as its bytes with the snippet, not a 500."""
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    worker, port = start_running_server(server)
    try:
        (project / "site" / "latin.html").write_bytes(b"<html><body>caf\xe9</body></html>")
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/latin.html", timeout=10) as page:
            assert page.status == 200
            body = page.read()
        assert b"caf\xe9" in body
        assert reload_snippet().encode() in body
    finally:
        stop_running_server(server, worker)


def test_html_removed_between_stat_and_read_is_a_404(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A page that vanishes mid-swap after StaticFiles found it is a 404, not a 500."""
    real_read_bytes = Path.read_bytes

    def vanish_then_read(path: Path) -> bytes:
        if path.name == "index.html":
            path.unlink(missing_ok=True)
        return real_read_bytes(path)

    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    worker, port = start_running_server(server)
    try:
        monkeypatch.setattr(Path, "read_bytes", vanish_then_read)
        with pytest.raises(urllib.error.HTTPError) as missing:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=10)
        assert missing.value.code == 404
    finally:
        monkeypatch.undo()
        stop_running_server(server, worker)


def _ipv6_loopback_available() -> bool:
    try:
        with socket.socket(socket.AF_INET6) as probe:
            probe.bind(("::1", 0))
    except OSError:
        return False
    return True


@pytest.mark.skipif(not _ipv6_loopback_available(), reason="no IPv6 loopback on this host")
def test_run_binds_an_ipv6_host_and_prints_it_in_brackets(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--host ::1`` binds an IPv6 socket and the printed URL is ``http://[::1]:PORT/``."""
    server = DevServer(project / "bartleby.yml", host="::1", port=0, events=True)
    worker, port = start_running_server(server)
    try:
        ready = json.loads(_events_until(capsys, '"type": "ready"').splitlines()[0])
        assert ready["url"] == f"http://[::1]:{port}/"
        with urllib.request.urlopen(f"http://[::1]:{port}/", timeout=10) as response:
            assert "Welcome" in response.read().decode("utf-8")
    finally:
        stop_running_server(server, worker)


def test_a_burst_of_writes_rebuilds_once(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Five writes inside the quiet window are one rebuild and one ``rebuild`` event."""
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0, events=True)
    calls = _count_rebuilds(server)
    worker, _port = start_running_server(server)
    try:
        page = project / "content" / "index.md"
        for index in range(5):
            page.write_text(f"---\ntitle: Home\n---\n\nBurst {index}.\n", encoding="utf-8")
        assert _wait_for(lambda: bool(calls)), "the burst never rebuilt"
        time.sleep(server.quiet_window * 5 + 1.0)
        assert len(calls) == 1, f"a burst of writes ran {len(calls)} rebuilds"
        events = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line]
        assert [event["type"] for event in events].count("rebuild") == 1
        assert [event["path"] for event in events if event["type"] == "change"] == [
            "content/index.md"
        ]
    finally:
        stop_running_server(server, worker)


def _write_path_theme(theme_dir: Path) -> Path:
    """Create a theme that extends scrivener with its own footer partial; return the partial."""
    partial = theme_dir / "templates" / "partials" / "footer.html"
    partial.parent.mkdir(parents=True)
    (theme_dir / "theme.yml").write_text("name: own\nextends: scrivener\n", encoding="utf-8")
    partial.write_text("<footer>own footer</footer>\n", encoding="utf-8")
    return partial


@pytest.mark.parametrize("location", ["inside", "outside"])
def test_run_rebuilds_when_a_path_theme_template_changes(
    project: Path, tmp_path: Path, location: str
) -> None:
    """Editing a template of a ``theme.path`` theme, in or out of the project, rebuilds."""
    theme_dir = project / "themes" / "own" if location == "inside" else tmp_path / "own-theme"
    partial = _write_path_theme(theme_dir)
    config_path = project / "bartleby.yml"
    theme_path = "themes/own" if location == "inside" else str(theme_dir)
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + f"\ntheme:\n  path: {theme_path!r}\n",
        encoding="utf-8",
    )
    server = DevServer(config_path, host="127.0.0.1", port=0)
    worker, port = start_running_server(server)
    try:
        assert "own footer" in _fetch(port)
        partial.write_text("<footer>edited footer</footer>\n", encoding="utf-8")
        assert _wait_for(lambda: "edited footer" in _fetch(port)), "the theme edit never rebuilt"
    finally:
        stop_running_server(server, worker)


def test_theme_files_classify_as_template_or_static_changes() -> None:
    """A theme's files are template changes, except its ``static/`` tree, which is static."""
    theme_dirs = ("themes/own/", "/elsewhere/own-theme/")
    assert classify_change("themes/own/templates/page.html", theme_dirs) == "template"
    assert classify_change("themes/own/theme.yml", theme_dirs) == "template"
    assert classify_change("themes/own/static/css/main.css", theme_dirs) == "static"
    assert classify_change("/elsewhere/own-theme/templates/page.html", theme_dirs) == "template"
    assert classify_change("static/css/custom.css") == "static"
    assert classify_change("theme/page.html") == "other"


def test_run_follows_an_output_dir_change(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Changing ``output_dir`` while serving moves both the rebuilds and the serving."""
    config_path = project / "bartleby.yml"
    server = DevServer(config_path, host="127.0.0.1", port=0, events=True)
    worker, port = start_running_server(server)
    try:
        assert "Welcome" in _fetch(port)
        config_path.write_text(
            config_path.read_text(encoding="utf-8") + "\noutput_dir: public\n", encoding="utf-8"
        )
        events_seen = _events_until(capsys, '"output_dir": "public/"')
        rebuilt = [json.loads(line) for line in events_seen.splitlines() if '"rebuild"' in line]
        assert rebuilt and rebuilt[-1]["output_dir"] == "public/"
        assert (project / "public" / "index.html").is_file()

        shutil.rmtree(project / "site")
        assert "Welcome" in _fetch(port)
    finally:
        stop_running_server(server, worker)


def test_run_prints_the_output_dir_change_in_text_mode(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """In text mode one line says where the output moved to."""
    config_path = project / "bartleby.yml"
    server = DevServer(config_path, host="127.0.0.1", port=0)
    worker, _port = start_running_server(server)
    try:
        config_path.write_text(
            config_path.read_text(encoding="utf-8") + "\noutput_dir: public\n", encoding="utf-8"
        )
        assert "public/" in _events_until(capsys, "Output directory changed")
    finally:
        stop_running_server(server, worker)


def test_run_rebuilds_when_a_content_directory_moves_out(project: Path, tmp_path: Path) -> None:
    """Moving a content directory out of the project is one directory event, and it rebuilds."""
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0)
    calls = _count_rebuilds(server)
    worker, _port = start_running_server(server)
    try:
        shutil.move(project / "content" / "blog", tmp_path / "elsewhere")
        assert _wait_for(lambda: bool(calls)), "the directory move never rebuilt"
    finally:
        stop_running_server(server, worker)


def test_watcher_forwards_directory_deletes_and_moves_only(tmp_path: Path) -> None:
    """A directory delete or move is a change; a directory modify is noise."""
    changes: list[str] = []
    handler = _ProjectChangeHandler(tmp_path, changes.append)
    handler.dispatch(DirDeletedEvent(str(tmp_path / "content" / "articles")))
    handler.dispatch(
        DirMovedEvent(str(tmp_path / "content" / "guides"), str(tmp_path.parent / "guides"))
    )
    handler.dispatch(DirModifiedEvent(str(tmp_path / "content")))
    assert changes == ["content/articles", "content/guides"]
