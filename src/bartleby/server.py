# ABOUTME: Development server with live reload, file watching, and dirty builds.
# Wraps the synchronous build pipeline with HTTP/WS serving and watchdog change detection.

from __future__ import annotations

import asyncio
import contextlib
import http.server
import json
import os
import socketserver
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from websockets.asyncio.server import ServerConnection, broadcast
from websockets.asyncio.server import serve as serve_websocket

from bartleby.build import BuildError, build, format_page_error
from bartleby.config import load_config
from bartleby.plugins import PluginCollection, discover_hooks, discover_plugins

if TYPE_CHECKING:
    from collections.abc import Callable

    from watchdog.events import FileSystemEvent
    from watchdog.observers.api import BaseObserver
    from websockets.asyncio.server import Server as WebSocketServer

    from bartleby.build import PageError
    from bartleby.config import BartlebyConfig


_CONTENT_PREFIXES: tuple[str, ...] = ("content/",)
_TEMPLATE_PREFIXES: tuple[str, ...] = ("templates/", "overrides/", "theme/")
_CONFIG_FILES: tuple[str, ...] = ("bartleby.yml", ".authors.yml")

# Every root or file the dev server watches, per spec's Development Server
# section. Entries ending in ``/`` are directory roots; the rest are exact files.
WATCHED_PATHS: tuple[str, ...] = (
    "content/",
    "templates/",
    "overrides/",
    "static/",
    "hooks/",
    "data/",
    "shortcodes/",
    "partials/",
    ".authors.yml",
    "bartleby.yml",
)

# The single source of truth for the reload endpoint's route. Both the browser
# snippet below and the WebSocket handler that serves it are built from this
# constant so the route is never hardcoded twice.
RELOAD_WS_PATH = "/__bartleby_reload"

# Injected into served pages so the browser reconnects and reloads on rebuild.
# It is added only by :func:`inject_reload_snippet` in serve mode, never by the
# build pipeline, so ``bartleby build`` output stays free of dev-only markup.
RELOAD_SNIPPET = (
    "<script>(function(){"
    "var ws=new WebSocket('ws://'+location.host+'" + RELOAD_WS_PATH + "');"
    "ws.onmessage=function(){location.reload();};"
    "})();</script>"
)


def is_watched(rel_path: str) -> bool:
    """Return whether ``rel_path`` falls under any watched root or file.

    :param rel_path: A project-relative path (POSIX or Windows separators).
    :returns: ``True`` when a change to the path should trigger a rebuild.
    """
    normalised = rel_path.replace("\\", "/")
    for entry in WATCHED_PATHS:
        if entry.endswith("/"):
            if normalised == entry.rstrip("/") or normalised.startswith(entry):
                return True
        elif normalised == entry:
            return True
    return False


def classify_change(rel_path: str) -> str:
    """Classify a changed path into ``content``, ``template``, ``config``, or ``other``."""
    normalised = rel_path.replace("\\", "/")
    if normalised in _CONFIG_FILES:
        return "config"
    for prefix in _CONFIG_FILES:
        if normalised.startswith(prefix):
            return "config"
    for prefix in _TEMPLATE_PREFIXES:
        if normalised.startswith(prefix):
            return "template"
    for prefix in _CONTENT_PREFIXES:
        if normalised.startswith(prefix):
            return "content"
    return "other"


def should_trigger_full_rebuild(kind: str, *, dirty: bool) -> bool:
    """Decide whether ``kind`` of change forces a full rebuild."""
    if not dirty:
        return True
    return kind in {"config", "template"}


def inject_reload_snippet(html: str) -> str:
    """Insert the live-reload snippet just before ``</body>`` (or append it).

    :param html: The rendered page HTML served by the dev server.
    :returns: The HTML with the reload snippet added. Serve-mode only.
    """
    marker = "</body>"
    if marker in html:
        return html.replace(marker, RELOAD_SNIPPET + marker, 1)
    return html + RELOAD_SNIPPET


class _ProjectChangeHandler(FileSystemEventHandler):
    """Translate watchdog filesystem events into project-relative change paths.

    Every non-directory event (create, modify, move, delete) under the
    watched root is forwarded to ``on_change``. This handler makes no
    decision about whether a path matters; :meth:`DevServer.dispatch_change`
    (via :func:`is_watched`) is the single place that decides.
    """

    def __init__(self, project_dir: Path, on_change: Callable[[str], None]) -> None:
        super().__init__()
        self._project_dir = project_dir
        self._on_change = on_change

    def on_any_event(self, event: FileSystemEvent) -> None:
        """Forward one non-directory event as a project-relative POSIX path."""
        if event.is_directory:
            return
        changed_path = Path(os.fsdecode(event.src_path))
        try:
            rel_path = changed_path.relative_to(self._project_dir).as_posix()
        except ValueError:
            return
        self._on_change(rel_path)


def _start_watcher(project_dir: Path, on_change: Callable[[str], None]) -> BaseObserver:
    """Start a watchdog Observer over the whole project tree.

    :param project_dir: The project root (the directory containing
        ``bartleby.yml``), watched recursively.
    :param on_change: Called with each changed path's project-relative POSIX
        path; the caller decides whether the path is actually watched.
    :returns: The started observer. Call ``.stop()`` then ``.join()`` on it to
        shut down cleanly.
    """
    observer = Observer()
    handler = _ProjectChangeHandler(project_dir, on_change)
    observer.schedule(handler, str(project_dir), recursive=True)
    observer.start()
    return observer


class _ReloadHub:
    """Serves the ``/__bartleby_reload`` WebSocket endpoint on its own event loop.

    :meth:`DevServer.run` also runs a synchronous ``TCPServer.serve_forever()``
    and a watchdog observer thread. Since ``websockets`` is asyncio-based, this
    hub runs its own event loop on a dedicated daemon thread so all three can
    run at once. :meth:`broadcast_reload` and :meth:`stop` are safe to call
    from any thread; they hand work to the hub's loop via
    ``call_soon_threadsafe`` / ``run_coroutine_threadsafe``.
    """

    def __init__(self) -> None:
        self.port: int | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._server: WebSocketServer | None = None
        self._clients: set[ServerConnection] = set()
        self._bind_error: BaseException | None = None

    def start(self, host: str) -> None:
        """Start the WebSocket server on an ephemeral port and block until bound.

        :param host: The interface to bind, matching the HTTP server's host.
        :raises RuntimeError: The bind never completed within the timeout, or
            :func:`~websockets.asyncio.server.serve` raised while binding
            (for example the port was already in use). Raising here, instead
            of leaving :attr:`port` as ``None``, stops :meth:`DevServer.run`
            from silently serving pages whose reload snippet points at a
            WebSocket channel that never came up.
        """
        bound = threading.Event()

        def run_loop() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            try:
                loop.run_until_complete(self._bind(host, bound))
            except BaseException as exc:
                self._bind_error = exc
                bound.set()
                loop.close()
                return
            loop.run_forever()
            loop.close()

        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()
        if not bound.wait(timeout=10):
            raise RuntimeError("reload WebSocket channel did not bind within 10s")
        if self._bind_error is not None:
            raise RuntimeError("reload WebSocket channel failed to bind") from self._bind_error

    async def _bind(self, host: str, bound: threading.Event) -> None:
        self._server = await serve_websocket(self._handle_client, host, 0)
        sock = self._server.sockets[0]
        self.port = sock.getsockname()[1]
        bound.set()

    async def _handle_client(self, connection: ServerConnection) -> None:
        request = connection.request
        if request is not None and request.path != RELOAD_WS_PATH:
            await connection.close()
            return
        self._clients.add(connection)
        try:
            await connection.wait_closed()
        finally:
            self._clients.discard(connection)

    def broadcast_reload(self) -> None:
        """Push a reload signal to every connected client.

        A no-op when the hub has not started yet or has no clients. The
        client snapshot is taken on the loop thread (via
        ``call_soon_threadsafe``), not on the caller's thread, because
        ``self._clients`` is also mutated by :meth:`_handle_client` on the
        loop thread; snapshotting here on the watchdog thread would race
        with that mutation and could raise ``RuntimeError: Set changed size
        during iteration``.
        """
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(self._broadcast_to_current_clients)

    def _broadcast_to_current_clients(self) -> None:
        """Snapshot ``self._clients`` and broadcast, all on the loop thread."""
        broadcast(list(self._clients), "reload")

    def stop(self) -> None:
        """Shut down the WebSocket server, then its event loop and thread."""
        if self._loop is None or self._thread is None:
            return

        async def _close() -> None:
            if self._server is not None:
                self._server.close()
                await self._server.wait_closed()

        future = asyncio.run_coroutine_threadsafe(_close(), self._loop)
        future.result(timeout=10)
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=10)


class DevServer:
    """Bartleby's development server harness.

    The HTTP and WebSocket servers are started by :meth:`run`; for tests
    we use the synchronous helpers (:meth:`build_once`, :meth:`rebuild`,
    :meth:`dispatch_change`) which exercise the rebuild path without touching
    the network.
    """

    def __init__(
        self,
        config_path: Path,
        *,
        host: str,
        port: int,
        dirty: bool,
        events: bool = False,
    ) -> None:
        self.config_path = config_path
        self.host = host
        self.port = port
        self.dirty = dirty
        self.events = events
        # Set by :meth:`run` once the reload WebSocket channel is bound; stays
        # ``None`` outside serve mode (the synchronous helpers used by tests
        # and by ``bartleby build`` never touch the reload channel).
        self.reload_ws_port: int | None = None
        self._reload_hub: _ReloadHub | None = None

    def build_once(self) -> None:
        """Run a full build with drafts included."""
        build(self.config_path, include_drafts=True)

    def rebuild(self) -> list[PageError]:
        """Run a full rebuild, retaining the last good output on failure.

        Each call re-runs :func:`bartleby.build.build`, which re-discovers
        config and ``hooks/*.py`` from scratch, so editing a hook file takes
        effect on the next rebuild without restarting the process. A failed
        build (page render errors or metadata validation) leaves the existing
        ``site/`` untouched and the collected errors are returned instead of
        raising, so the server keeps serving the previous good build.

        :returns: The collected page errors, or an empty list on success.
        """
        try:
            build(self.config_path, include_drafts=True)
        except BuildError as exc:
            return list(exc.errors)
        except ValueError as exc:
            from bartleby.build import PageError as _PageError

            return [_PageError(file_path=str(self.config_path), message=str(exc))]
        return []

    def maybe_recompile_theme(self) -> str:
        """Recompile theme CSS when the Tailwind binary is already cached.

        When the standalone binary is on ``PATH`` or in the cache, the theme is
        recompiled so override edits take effect on reload. When no binary is
        available, a one-line hint is printed instead of downloading mid-serve.

        :returns: ``"recompiled"`` when CSS was rebuilt, ``"hint"`` when only a
            hint was printed.
        """
        from bartleby.theme import get_theme_templates_dir
        from bartleby.theme_compile import (
            ThemeCompileError,
            compile_theme_css,
            default_cache_dir,
            resolve_tailwind_binary,
        )

        project_dir = self.config_path.parent
        cache_dir = default_cache_dir()
        try:
            resolve_tailwind_binary(cache_dir=cache_dir, allow_download=False)
        except ThemeCompileError:
            print(
                "theme override changed but no Tailwind binary is cached; "
                "run `bartleby theme compile` to refresh the CSS"
            )
            return "hint"

        compile_theme_css(project_dir, get_theme_templates_dir(), cache_dir=cache_dir)
        return "recompiled"

    def dispatch_change(self, rel_path: str, *, rebuild: Callable[[], object]) -> None:
        """Invoke ``rebuild`` only when ``rel_path`` is a watched path.

        :param rel_path: The project-relative path that changed.
        :param rebuild: Callback fired once for a watched change.
        """
        if is_watched(rel_path):
            rebuild()

    def dispatch_on_serve(self, server: object, *, config: BartlebyConfig | None = None) -> None:
        """Fire the ``on_serve`` hook so plugins can react to the dev server.

        The project's ``hooks/`` directory is discovered and any ``on_serve``
        handlers run with the live server object and resolved config, matching
        the spec signature ``on_serve(server, config)``.

        :param server: The live server object passed through to the hook.
        :param config: A previously loaded config to reuse. When omitted,
            ``bartleby.yml`` is loaded fresh.
        """
        if config is None:
            config = load_config(self.config_path)
        plugins = PluginCollection()
        plugins.merge(discover_plugins(config.disabled_plugins))
        plugins.merge(discover_hooks(config.config_dir))
        plugins.run_event("on_serve", server, config=config)

    def handle_change(self, rel_path: str) -> None:
        """React to a single file change by re-running the appropriate build."""
        kind = classify_change(rel_path)
        if kind == "other":
            return
        # Both full and dirty modes currently run a full build; incremental
        # rebuilds are a deferred optimization.
        self.build_once()

    def emit_event(self, event: dict[str, object]) -> None:
        """Write one JSON event object per line to stdout for ``--events`` mode.

        :param event: A mapping with at least a ``type`` key.
        """
        sys.stdout.write(json.dumps(event) + "\n")
        sys.stdout.flush()

    def rebuild_with_events(self, rel_path: str) -> list[PageError]:
        """Rebuild for a watched change and emit structured ``--events`` output.

        Emits a ``change`` event for the path, then either a ``rebuild`` event
        with the page count or an ``error`` event listing the collected
        failures.

        :param rel_path: The watched path that triggered the rebuild.
        :returns: The collected page errors, or an empty list on success.
        """
        self.emit_event({"type": "change", "path": rel_path})
        errors = self.rebuild()
        if errors:
            self.emit_event(
                {
                    "type": "error",
                    "errors": [format_page_error(error) for error in errors],
                }
            )
        else:
            self.emit_event({"type": "rebuild", "status": "ok"})
        return errors

    def _on_watched_change(self, rel_path: str) -> None:
        """Route one filesystem change through :meth:`dispatch_change`.

        :meth:`dispatch_change` (via :func:`is_watched`) is the single
        decision point for whether ``rel_path`` triggers a rebuild; this
        method only picks which rebuild callback to use.

        :param rel_path: The project-relative POSIX path that changed.
        """
        if self.events:

            def emit_and_rebuild() -> list[PageError]:
                return self.rebuild_with_events(rel_path)

            self.dispatch_change(
                rel_path, rebuild=lambda: self._rebuild_and_broadcast(emit_and_rebuild)
            )
        else:
            self.dispatch_change(
                rel_path, rebuild=lambda: self._rebuild_and_broadcast(self.rebuild)
            )

    def _rebuild_and_broadcast(self, perform_rebuild: Callable[[], list[PageError]]) -> None:
        """Run ``perform_rebuild`` and push a reload signal only on success.

        A failed rebuild keeps serving the last good build (see
        :meth:`rebuild`), so it must not falsely tell the browser to reload.

        :param perform_rebuild: Either :meth:`rebuild` or
            :meth:`rebuild_with_events` bound to the current watched path.
        """
        errors = perform_rebuild()
        if not errors and self._reload_hub is not None:
            self._reload_hub.broadcast_reload()

    def run(self, *, ready: Callable[[socketserver.TCPServer], None] | None = None) -> None:
        """Start the HTTP server and file watcher, serving until interrupted.

        A watchdog Observer watches the whole project tree; every change is
        routed through :meth:`dispatch_change`, so only paths under
        :data:`WATCHED_PATHS` trigger a rebuild (see :meth:`_on_watched_change`).
        :meth:`rebuild` retains the last good build on a failed rebuild, so a
        watcher-triggered failure keeps serving the previous good output.

        :param ready: Optional callback fired once the socket is bound and
            listening, receiving the live ``TCPServer``. Tests use it to learn
            the ephemeral port and to call :meth:`~socketserver.BaseServer.shutdown`
            from another thread; in normal CLI use it is ``None``.
        """
        self.build_once()
        config = load_config(self.config_path)
        project_dir = self.config_path.parent
        site_dir = project_dir / config.output_dir
        handler = _site_request_handler(site_dir, inject_reload=True)
        reload_hub = _ReloadHub()
        reload_hub.start(self.host)
        self._reload_hub = reload_hub
        self.reload_ws_port = reload_hub.port
        observer = _start_watcher(project_dir, self._on_watched_change)
        try:
            with socketserver.TCPServer((self.host, self.port), handler) as httpd:
                self.dispatch_on_serve(httpd, config=config)
                print(f"Serving at http://{self.host}:{httpd.server_address[1]}/")
                if ready is not None:
                    ready(httpd)
                with contextlib.suppress(KeyboardInterrupt):
                    httpd.serve_forever()
        finally:
            observer.stop()
            observer.join()
            reload_hub.stop()
            self._reload_hub = None


def _site_request_handler(
    site_dir: Path, *, inject_reload: bool = False
) -> type[http.server.SimpleHTTPRequestHandler]:
    """Return a request handler class serving files from ``site_dir``.

    :param site_dir: The built output directory to serve.
    :param inject_reload: When ``True`` (serve mode only), HTML responses are
        rewritten through :func:`inject_reload_snippet` before being sent.
        ``bartleby build`` never sets this, so build output stays snippet-free.
    """

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, directory=str(site_dir), **kwargs)  # type: ignore[arg-type]

        def do_GET(self) -> None:
            if inject_reload and self._serve_html_with_reload_snippet():
                return
            super().do_GET()

        def _serve_html_with_reload_snippet(self) -> bool:
            """Serve the requested path with the reload snippet injected.

            :returns: ``True`` when this path was an HTML file and the
                response was already sent; ``False`` to fall back to the
                default static-file handling (non-HTML, missing, or a
                directory with no ``index.html``).
            """
            fs_path = Path(self.translate_path(self.path))
            if fs_path.is_dir():
                fs_path = fs_path / "index.html"
            if fs_path.suffix != ".html" or not fs_path.is_file():
                return False
            html = fs_path.read_text(encoding="utf-8")
            body = inject_reload_snippet(html).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return True

    return Handler
