# ABOUTME: Development server with live reload, file watching, and full rebuilds on change.
# Serves the built site and reload socket from one Starlette app on uvicorn, watching for changes.

"""Bartleby's development server.

One Starlette app, run in-process by uvicorn, serves both the built site and
the live-reload WebSocket on the same port (after sphinx-autobuild's design).
The page's reload snippet therefore connects to ``location.host`` and needs
no second port. Because uvicorn is async, an idle connection a browser opened
ahead of time cannot hold up other requests.

The build stays synchronous. A watchdog observer thread runs each rebuild
(one at a time, since the observer dispatches on a single thread), then hands
the reload broadcast to the server's event loop. The event filter is
unchanged: :func:`is_watched` and :func:`classify_change` decide what matters.

HTML is served through a small :class:`~starlette.staticfiles.StaticFiles`
subclass that rewrites each ``.html`` response with the reload snippet. That
keeps StaticFiles' directory ``index.html`` handling, its ``404.html``
fallback, and its content types, so nothing here reimplements file serving.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import socket
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import uvicorn
from starlette.applications import Starlette
from starlette.responses import FileResponse, HTMLResponse
from starlette.routing import Mount, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect
from watchdog.events import (
    EVENT_TYPE_CREATED,
    EVENT_TYPE_DELETED,
    EVENT_TYPE_MODIFIED,
    EVENT_TYPE_MOVED,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from bartleby.agent_surface import AgentSurfaceError
from bartleby.authors import AuthorError
from bartleby.build import BuildError, PageError, build, format_page_error
from bartleby.cli import LABELED_ERRORS
from bartleby.config import ConfigError, load_config
from bartleby.content import ContentError
from bartleby.output import BuildOutput, ServeStartOutput, render
from bartleby.plugins import PluginCollection, discover_hooks, discover_plugins
from bartleby.theme_loader import ThemeError

if TYPE_CHECKING:
    import concurrent.futures
    from collections.abc import Callable

    from starlette.responses import Response
    from starlette.types import Scope
    from watchdog.events import FileSystemEvent
    from watchdog.observers.api import BaseObserver

    from bartleby.build import BuildResult
    from bartleby.config import BartlebyConfig


logger = logging.getLogger(__name__)


class ServeBindError(OSError):
    """Raised when the dev server cannot bind its listening socket.

    Only the bind raises this; an ``OSError`` from the build is left alone so it
    is never mistaken for a port problem.

    :ivar host: The host the bind was attempted on.
    :ivar port: The port the bind was attempted on.
    :ivar reason: The operating system's reason, such as ``Address already in use``.
    """

    def __init__(self, host: str, port: int, reason: str) -> None:
        super().__init__(f"cannot bind {host}:{port} ({reason})")
        self.host = host
        self.port = port
        self.reason = reason


# What a rebuild reports as page errors instead of raising: a bad value plus every
# labeled author-facing error the CLI reports.
_REPORTED_ERRORS: tuple[type[Exception], ...] = (ValueError, *LABELED_ERRORS)

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
# snippet below and the WebSocket route that serves it are built from this
# constant so the route is never hardcoded twice.
RELOAD_WS_PATH = "/__bartleby_reload"


def reload_snippet() -> str:
    """Return the script that reloads the page when the reload channel signals.

    The WebSocket route lives on the same app and port as the pages, so the
    script connects to ``location.host`` (which also works from another
    machine on the network). It is added only by :func:`inject_reload_snippet`
    in serve mode, never by the build pipeline, so ``bartleby build`` output
    stays free of dev-only markup.

    :returns: A ``<script>`` element as a string.
    """
    return (
        "<script>(function(){"
        "var scheme=location.protocol==='https:'?'wss://':'ws://';"
        f"var ws=new WebSocket(scheme+location.host+'{RELOAD_WS_PATH}');"
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


def inject_reload_snippet(html: str) -> str:
    """Insert the live-reload snippet just before ``</body>`` (or append it).

    :param html: The rendered page HTML served by the dev server.
    :returns: The HTML with the reload snippet added. Serve-mode only.
    """
    snippet = reload_snippet()
    marker = "</body>"
    if marker in html:
        return html.replace(marker, snippet + marker, 1)
    return html + snippet


# Watchdog event types that mean a file's contents or existence changed.
_CHANGE_EVENT_TYPES = frozenset(
    {EVENT_TYPE_CREATED, EVENT_TYPE_MODIFIED, EVENT_TYPE_MOVED, EVENT_TYPE_DELETED}
)


class _ProjectChangeHandler(FileSystemEventHandler):
    """Translate watchdog filesystem events into project-relative change paths.

    Every non-directory create, modify, move, or delete under the watched
    root is forwarded to ``on_change``; a move forwards both of its paths.
    Opens and closes are dropped, since a rebuild reads every file and would
    otherwise trigger the next rebuild. This handler makes no decision about
    whether a path matters; :meth:`DevServer.dispatch_change` (via
    :func:`is_watched`) is the single place that decides.
    """

    def __init__(self, project_dir: Path, on_change: Callable[[str], None]) -> None:
        super().__init__()
        self._project_dir = project_dir
        self._on_change = on_change

    def on_any_event(self, event: FileSystemEvent) -> None:
        """Forward the paths of one content-changing event as project-relative POSIX paths."""
        if event.is_directory or event.event_type not in _CHANGE_EVENT_TYPES:
            return
        for raw_path in (event.src_path, event.dest_path):
            if not raw_path:
                continue
            changed_path = Path(os.fsdecode(raw_path))
            try:
                rel_path = changed_path.relative_to(self._project_dir).as_posix()
            except ValueError:
                continue
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


class _ReloadChannel:
    """The set of connected reload sockets, owned by the server's event loop.

    The WebSocket endpoint adds and removes sockets on the loop thread.
    :meth:`broadcast_reload` is called from the watchdog thread and hands the
    send to the loop with ``run_coroutine_threadsafe``, so the client set is
    only ever read or changed on the loop thread.
    """

    def __init__(self) -> None:
        self.loop: asyncio.AbstractEventLoop | None = None
        self._clients: set[WebSocket] = set()

    async def endpoint(self, websocket: WebSocket) -> None:
        """Hold one browser's reload socket open until it disconnects."""
        await websocket.accept()
        self._clients.add(websocket)
        try:
            with contextlib.suppress(WebSocketDisconnect):
                while True:
                    await websocket.receive_text()
        finally:
            self._clients.discard(websocket)

    def broadcast_reload(self) -> None:
        """Push a reload signal to every connected client, from any thread.

        A no-op before the server's loop is running or after it has stopped.
        """
        loop = self.loop
        if loop is None:
            return
        future = asyncio.run_coroutine_threadsafe(self._send_reload(), loop)
        future.add_done_callback(self._log_failed_broadcast)

    @staticmethod
    def _log_failed_broadcast(future: concurrent.futures.Future[None]) -> None:
        """Log a broadcast that raised; a cancelled one (loop shutdown) is not an error."""
        if not future.cancelled() and (error := future.exception()) is not None:
            logger.error("reload broadcast failed", exc_info=error)

    async def _send_reload(self) -> None:
        """Send ``reload`` to a snapshot of the clients; a dead socket is skipped."""
        for client in list(self._clients):
            with contextlib.suppress(WebSocketDisconnect, RuntimeError):
                await client.send_text("reload")


class _ReloadInjectingFiles(StaticFiles):
    """Static files that add the reload snippet to every HTML response.

    A custom subclass beats a response middleware here: StaticFiles already
    decides which file answers (directory ``index.html``, the theme's
    ``404.html``, content types), and this only rewrites the ``.html`` ones.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        """Serve ``path`` as StaticFiles would, with the snippet injected into HTML."""
        response = await super().get_response(path, scope)
        if isinstance(response, FileResponse) and Path(response.path).suffix == ".html":
            html = await asyncio.to_thread(Path(response.path).read_text, encoding="utf-8")
            return HTMLResponse(inject_reload_snippet(html), status_code=response.status_code)
        return response


def build_app(site_dir: Path, channel: _ReloadChannel) -> Starlette:
    """Return the dev server's ASGI app: the reload WebSocket plus the built site.

    :param site_dir: The built output directory to serve.
    :param channel: The reload channel whose endpoint is mounted at
        :data:`RELOAD_WS_PATH`.
    :returns: A Starlette app serving pages and the reload socket on one port.
    """
    return Starlette(
        routes=[
            WebSocketRoute(RELOAD_WS_PATH, channel.endpoint),
            Mount("/", app=_ReloadInjectingFiles(directory=site_dir, html=True)),
        ]
    )


class DevServer:
    """Bartleby's development server harness.

    The uvicorn server is started by :meth:`run`; for tests
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
        events: bool = False,
        overrides: list[str] | None = None,
    ) -> None:
        self.config_path = config_path
        self.overrides = overrides
        self.host = host
        self.port = port
        self.events = events
        # Set by :meth:`run`; stay ``None`` outside serve mode (the synchronous
        # helpers used by tests and by ``bartleby build`` never touch them).
        self._channel: _ReloadChannel | None = None
        self._uvicorn: uvicorn.Server | None = None

    def build_once(self) -> BuildResult:
        """Run a full build with drafts included.

        :returns: The finished build's summary.
        """
        return build(self.config_path, include_drafts=True, overrides=self.overrides)

    def rebuild(self) -> list[PageError]:
        """Run a full rebuild, retaining the last good output on failure.

        Each call re-runs :func:`bartleby.build.build`, which re-discovers
        config and ``hooks/*.py`` from scratch, so editing a hook file takes
        effect on the next rebuild without restarting the process. A failed
        build (page render errors or metadata validation) leaves the existing
        ``site/`` untouched and the collected errors are returned instead of
        raising, so the server keeps serving the previous good build. The labeled
        author-facing errors (:data:`bartleby.cli.LABELED_ERRORS`) are returned the same way.

        :returns: The collected page errors, or an empty list on success.
        """
        try:
            build(self.config_path, include_drafts=True, overrides=self.overrides)
        except BuildError as exc:
            return list(exc.errors)
        except _REPORTED_ERRORS as exc:
            # Broken front matter, config, authors, or theme in the middle of a
            # serve must be reported, not kill the watcher thread.
            # ``str(exc)`` already leads with the error's own source, so report that
            # source (relative to the project, like a ContentError path) as the path
            # and strip it from the message rather than print it twice.
            message = str(exc)
            source: Path | str | None = None
            if isinstance(exc, ContentError) and exc.source_path:
                source = exc.source_path
            elif isinstance(exc, ConfigError | AuthorError | ThemeError) and exc.source:
                source = exc.source
                message = message.removeprefix(f"{source}: ")
            elif isinstance(exc, AgentSurfaceError):
                source = f"content/{exc.source_path}"
                message = message.removeprefix(f"{source}: ")
            if source is None:
                file_path = str(self.config_path)
            elif isinstance(source, Path):
                file_path = os.path.relpath(source, self.config_path.parent)
            else:
                file_path = source
            return [PageError(file_path=file_path, message=message)]
        return []

    def maybe_recompile_theme(self) -> str:
        """Recompile theme CSS when the Tailwind binary is already cached.

        When the standalone binary is on ``PATH`` or in the cache, the theme is
        recompiled so override edits take effect on reload. When no binary is
        available, a one-line hint is printed instead of downloading mid-serve.

        :returns: ``"recompiled"`` when CSS was rebuilt, ``"hint"`` when only a
            hint was printed.
        """
        from bartleby.theme_compile import (
            ThemeCompileError,
            compile_theme_css,
            default_cache_dir,
            resolve_tailwind_binary,
        )
        from bartleby.theme_loader import select_theme

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

        config = load_config(self.config_path, self.overrides)
        theme = select_theme(config.theme, project_dir)
        compile_theme_css(project_dir, theme, config.theme.tokens, cache_dir=cache_dir)
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
            config = load_config(self.config_path, self.overrides)
        plugins = PluginCollection()
        plugins.merge(discover_plugins(config.disabled_plugins))
        plugins.merge(discover_hooks(config.config_dir))
        plugins.run_event("on_serve", server, config=config)

    def handle_change(self, rel_path: str) -> None:
        """React to a single file change by re-running the appropriate build."""
        kind = classify_change(rel_path)
        if kind == "other":
            return
        # Every watched change runs a full build; incremental builds are a non-goal.
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
        if not errors and self._channel is not None:
            self._channel.broadcast_reload()

    def run(self, *, ready: Callable[[int], None] | None = None) -> None:
        """Serve the site and reload socket on one port until stopped or interrupted.

        A watchdog Observer watches the whole project tree; every change is
        routed through :meth:`dispatch_change`, so only paths under
        :data:`WATCHED_PATHS` trigger a rebuild (see :meth:`_on_watched_change`).
        :meth:`rebuild` retains the last good build on a failed rebuild, so a
        watcher-triggered failure keeps serving the previous good output.

        The listening socket is bound here, before the initial build and before
        uvicorn starts, so a port already in use raises :class:`ServeBindError` and port ``0``
        resolves to a concrete port before anything is printed.

        :param ready: Optional callback fired once the socket is listening and
            the watcher is running, receiving the bound port. Tests use it to
            learn the ephemeral port; in normal CLI use it is ``None``.
        """
        channel = _ReloadChannel()
        try:
            # Bind first so a busy port fails before the initial build runs.
            try:
                listener = socket.create_server((self.host, self.port))
            except OSError as exc:
                raise ServeBindError(self.host, self.port, exc.strerror or str(exc)) from exc
            with listener, contextlib.suppress(KeyboardInterrupt):
                built = self.build_once()
                config = load_config(self.config_path, self.overrides)
                site_dir = self.config_path.parent / config.output_dir
                uvicorn_server = uvicorn.Server(
                    uvicorn.Config(
                        build_app(site_dir, channel), log_config=None, log_level="warning"
                    )
                )
                self._channel = channel
                self._uvicorn = uvicorn_server
                asyncio.run(self._serve(uvicorn_server, channel, listener, config, built, ready))
        finally:
            self._channel = None
            self._uvicorn = None

    def stop(self) -> None:
        """Ask a running :meth:`run` to shut down; safe to call from another thread."""
        if self._uvicorn is not None:
            self._uvicorn.should_exit = True

    async def _serve(
        self,
        uvicorn_server: uvicorn.Server,
        channel: _ReloadChannel,
        listener: socket.socket,
        config: BartlebyConfig,
        built: BuildResult,
        ready: Callable[[int], None] | None,
    ) -> None:
        """Run uvicorn on ``listener`` with the project watcher alive around it.

        Once the watcher is running, prints the startup summary (build counts, the
        bound URL, how to stop): one ``ready`` JSON object line under ``--events``,
        text otherwise.
        """
        channel.loop = asyncio.get_running_loop()
        observer = _start_watcher(self.config_path.parent, self._on_watched_change)
        try:
            self.dispatch_on_serve(uvicorn_server, config=config)
            port = listener.getsockname()[1]
            startup = ServeStartOutput(
                url=f"http://{self.host}:{port}/", build=BuildOutput.from_result(built)
            )
            if self.events:
                self.emit_event(startup.to_dict())
            else:
                print(render(startup, "text"), flush=True)
            if ready is not None:
                ready(port)
            await uvicorn_server.serve(sockets=[listener])
        finally:
            observer.stop()
            # Join off the loop: a rebuild in flight may still broadcast to it.
            await asyncio.to_thread(observer.join)
            channel.loop = None
