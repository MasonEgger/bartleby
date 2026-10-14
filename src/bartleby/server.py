# ABOUTME: Development server with live reload, file watching, and full rebuilds on change.
# Serves the built site and reload socket from one Starlette app on uvicorn, watching for changes.

"""Bartleby's development server.

One Starlette app, run in-process by uvicorn, serves both the built site and
the live-reload WebSocket on the same port (after sphinx-autobuild's design).
The page's reload snippet therefore connects to ``location.host`` and needs
no second port. Because uvicorn is async, an idle connection a browser opened
ahead of time cannot hold up other requests.

The build stays synchronous. The watchdog observer thread only queues the
paths that change; one worker thread drains the queue after a short quiet
window and runs a single rebuild per burst (an editor's save is several
events), then hands the reload broadcast to the server's event loop. The
event filter is unchanged: :func:`is_watched` and :func:`classify_change`
decide what matters, and the resolved theme's directories count too.

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
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import uvicorn
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
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
from bartleby.theme_loader import ThemeError, select_theme
from bartleby.themes import bundled_theme_root

if TYPE_CHECKING:
    import concurrent.futures
    from collections.abc import Callable, Sequence

    from starlette.responses import Response
    from starlette.types import Scope
    from watchdog.events import FileSystemEvent
    from watchdog.observers.api import BaseObserver

    from bartleby.build import BuildResult
    from bartleby.config import BartlebyConfig
    from bartleby.theme_loader import ResolvedTheme


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
_TEMPLATE_PREFIXES: tuple[str, ...] = ("templates/", "overrides/")
_STATIC_PREFIXES: tuple[str, ...] = ("static/",)
_CONFIG_FILES: tuple[str, ...] = ("bartleby.yml", ".authors.yml")

# Every root or file the dev server watches, per spec's Development Server
# section. Entries ending in ``/`` are directory roots; the rest are exact files.
# The resolved theme's directories are watched as well; they come from config,
# so :class:`DevServer` adds them per project.
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

# How long the change queue stays quiet before one rebuild runs for the burst.
DEFAULT_QUIET_WINDOW = 0.1


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


def is_watched(rel_path: str, theme_dirs: Sequence[str] = ()) -> bool:
    """Return whether ``rel_path`` falls under any watched root, file, or theme directory.

    :param rel_path: A project-relative path (POSIX or Windows separators), or
        an absolute POSIX path for a theme directory outside the project.
    :param theme_dirs: The resolved theme's directories as ``/``-terminated
        prefixes in the same form (see :meth:`DevServer.watch_theme`).
    :returns: ``True`` when a change to the path should trigger a rebuild.
    """
    normalised = rel_path.replace("\\", "/")
    for entry in (*WATCHED_PATHS, *theme_dirs):
        if entry.endswith("/"):
            if normalised == entry.rstrip("/") or normalised.startswith(entry):
                return True
        elif normalised == entry:
            return True
    return False


def classify_change(rel_path: str, theme_dirs: Sequence[str] = ()) -> str:
    """Classify a changed path as ``content``, ``template``, ``static``, ``config``, or ``other``.

    A theme file is a ``static`` change under the theme's ``static/`` tree and a
    ``template`` change anywhere else in the theme (its manifest included).

    :param rel_path: The changed path, in the form :func:`is_watched` takes.
    :param theme_dirs: The resolved theme's directories as ``/``-terminated prefixes.
    """
    normalised = rel_path.replace("\\", "/")
    for theme_dir in theme_dirs:
        if normalised.startswith(theme_dir):
            inside_theme = normalised.removeprefix(theme_dir)
            return "static" if inside_theme.startswith(_STATIC_PREFIXES) else "template"
    if normalised in _CONFIG_FILES or normalised.startswith(_CONFIG_FILES):
        return "config"
    if normalised.startswith(_TEMPLATE_PREFIXES):
        return "template"
    if normalised.startswith(_CONTENT_PREFIXES):
        return "content"
    if normalised.startswith(_STATIC_PREFIXES):
        return "static"
    return "other"


def inject_reload_snippet(html: bytes) -> bytes:
    """Insert the live-reload snippet just before ``</body>`` (or append it).

    The page is handled as bytes so a file in any encoding is served as it
    was written; only the ASCII ``</body>`` marker is searched for.

    :param html: The rendered page served by the dev server.
    :returns: The page with the reload snippet added. Serve-mode only.
    """
    snippet = reload_snippet().encode("ascii")
    marker = b"</body>"
    if marker in html:
        return html.replace(marker, snippet + marker, 1)
    return html + snippet


def url_host(host: str) -> str:
    """Return ``host`` as it appears in a URL: an IPv6 address goes in brackets."""
    return f"[{host}]" if ":" in host else host


def theme_watch_roots(theme: ResolvedTheme) -> list[Path]:
    """The directories of a resolved theme chain worth watching: every non-bundled layer.

    :param theme: The resolved chain.
    :returns: The resolved roots of the path and package layers, leaf-first.
    """
    bundled = bundled_theme_root("base").parent.resolve()
    return [
        layer.root.resolve()
        for layer in theme.chain
        if not layer.root.resolve().is_relative_to(bundled)
    ]


# Watchdog event types that mean a file's contents or existence changed.
_CHANGE_EVENT_TYPES = frozenset(
    {EVENT_TYPE_CREATED, EVENT_TYPE_MODIFIED, EVENT_TYPE_MOVED, EVENT_TYPE_DELETED}
)
# For a directory only a delete or a move matters: a whole tree left the
# project in one event. A directory's own modify event only mirrors a file event.
_DIRECTORY_EVENT_TYPES = frozenset({EVENT_TYPE_MOVED, EVENT_TYPE_DELETED})


class _ProjectChangeHandler(FileSystemEventHandler):
    """Translate watchdog filesystem events into change paths under one watched root.

    Every file create, modify, move, or delete under the root is forwarded to
    ``on_change``, and so is a directory delete or move; a move forwards both
    of its paths. Opens and closes are dropped, since a rebuild reads every
    file and would otherwise trigger the next rebuild. This handler makes no
    decision about whether a path matters; :meth:`DevServer.dispatch_change`
    (via :func:`is_watched`) is the single place that decides.
    """

    def __init__(self, root: Path, on_change: Callable[[str], None], prefix: str = "") -> None:
        """Watch ``root`` and report each change as ``prefix`` plus the root-relative path.

        :param root: The directory the observer watches with this handler.
        :param on_change: Receives each changed path as ``prefix`` plus the
            root-relative POSIX path.
        :param prefix: Empty for the project root; a theme directory outside
            the project passes its own ``/``-terminated POSIX path.
        """
        super().__init__()
        self._root = root
        self._on_change = on_change
        self._prefix = prefix

    def on_any_event(self, event: FileSystemEvent) -> None:
        """Forward the paths of one content-changing event."""
        relevant = _DIRECTORY_EVENT_TYPES if event.is_directory else _CHANGE_EVENT_TYPES
        if event.event_type not in relevant:
            return
        for raw_path in (event.src_path, event.dest_path):
            if not raw_path:
                continue
            changed_path = Path(os.fsdecode(raw_path))
            try:
                rel_path = changed_path.relative_to(self._root).as_posix()
            except ValueError:
                continue
            self._on_change(self._prefix + rel_path)


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
    :meth:`broadcast_reload` is called from the rebuild worker thread and hands
    the send to the loop with ``run_coroutine_threadsafe``, so the client set
    is only ever read or changed on the loop thread.
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
        """Serve ``path`` as StaticFiles would, with the snippet injected into HTML.

        The page is read as bytes, so its encoding does not matter. A page that
        vanished between StaticFiles' stat and the read (a swap in progress) is a 404.
        """
        response = await super().get_response(path, scope)
        if not (isinstance(response, FileResponse) and Path(response.path).suffix == ".html"):
            return response
        try:
            html = await asyncio.to_thread(Path(response.path).read_bytes)
        except OSError as exc:
            raise HTTPException(status_code=404) from exc
        return HTMLResponse(inject_reload_snippet(html), status_code=response.status_code)

    def serve_from(self, directory: Path) -> bool:
        """Point this app at ``directory``; returns whether that is a change.

        :param directory: The output directory the latest build wrote.
        """
        if Path(str(self.directory)).resolve() == directory.resolve():
            return False
        self.directory = directory
        self.all_directories = self.get_directories(directory, self.packages)
        return True


def build_app(files: StaticFiles, channel: _ReloadChannel) -> Starlette:
    """Return the dev server's ASGI app: the reload WebSocket plus the built site.

    :param files: The static app serving the built output directory.
    :param channel: The reload channel whose endpoint is mounted at
        :data:`RELOAD_WS_PATH`.
    :returns: A Starlette app serving pages and the reload socket on one port.
    """
    return Starlette(
        routes=[
            WebSocketRoute(RELOAD_WS_PATH, channel.endpoint),
            Mount("/", app=files),
        ]
    )


def _bind(host: str, port: int) -> socket.socket:
    """Bind the listening socket, in the address family ``host`` resolves to.

    An IPv4 address is preferred when the host has both, so ``localhost`` keeps
    binding ``127.0.0.1``; a host with only an IPv6 address (``::1``) binds that.

    :raises ServeBindError: When the host does not resolve or the port is busy.
    """
    try:
        resolved = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        families = [family for family, *_rest in resolved]
        family = socket.AF_INET if socket.AF_INET in families else families[0]
        return socket.create_server((host, port), family=family)
    except OSError as exc:
        raise ServeBindError(host, port, exc.strerror or str(exc)) from exc


class DevServer:
    """Bartleby's development server harness.

    The uvicorn server is started by :meth:`run`; for tests
    we use the synchronous helpers (:meth:`build_once`, :meth:`rebuild`,
    :meth:`dispatch_change`) which exercise the rebuild path without touching
    the network.

    :ivar quiet_window: Seconds the change queue must stay quiet before the
        worker runs one rebuild for everything queued.
    :ivar last_result: The most recent successful build's summary.
    """

    def __init__(
        self,
        config_path: Path,
        *,
        host: str,
        port: int,
        events: bool = False,
        overrides: list[str] | None = None,
        quiet_window: float = DEFAULT_QUIET_WINDOW,
    ) -> None:
        self.config_path = config_path
        self.overrides = overrides
        self.host = host
        self.port = port
        self.events = events
        self.quiet_window = quiet_window
        self.last_result: BuildResult | None = None
        # Set by :meth:`run`; stay ``None`` outside serve mode (the synchronous
        # helpers used by tests and by ``bartleby build`` never touch them).
        self._channel: _ReloadChannel | None = None
        self._uvicorn: uvicorn.Server | None = None
        self._files: _ReloadInjectingFiles | None = None
        self._observer: BaseObserver | None = None
        # The change queue: the observer thread appends, the worker drains.
        self._pending: list[str] = []
        self._pending_lock = threading.Lock()
        self._wake = threading.Event()
        self._stop_worker = threading.Event()
        # The resolved theme's directories as watched prefixes (see :meth:`watch_theme`).
        self._theme_dirs: tuple[str, ...] = ()
        self._outside_theme_roots: set[Path] = set()

    def build_once(self) -> BuildResult:
        """Run a full build with drafts included.

        :returns: The finished build's summary.
        """
        result = build(self.config_path, include_drafts=True, overrides=self.overrides)
        self.last_result = result
        return result

    def rebuild(self) -> list[PageError]:
        """Run a full rebuild, retaining the last good output on failure.

        Each call re-runs :func:`bartleby.build.build`, which re-discovers
        config and ``hooks/*.py`` from scratch, so editing a hook file takes
        effect on the next rebuild without restarting the process. A failed
        build (page render errors or metadata validation) leaves the existing
        ``site/`` untouched and the collected errors are returned instead of
        raising, so the server keeps serving the previous good build. The labeled
        author-facing errors (:data:`bartleby.cli.LABELED_ERRORS`) are returned the
        same way, and so is any other exception (a hook that fails to import, a
        config file missing mid-save), reported with its type and message.

        :returns: The collected page errors, or an empty list on success.
        """
        try:
            self.build_once()
        except BuildError as exc:
            return list(exc.errors)
        except _REPORTED_ERRORS as exc:
            return [self._labeled_page_error(exc)]
        except Exception as exc:
            # Anything else is a defect in the project, not in Bartleby, and
            # must be reported rather than kill the rebuild worker.
            logger.debug("rebuild failed", exc_info=exc)
            source = getattr(exc, "filename", None)
            file_path = source if isinstance(source, str) else str(self.config_path)
            return [
                PageError(
                    file_path=os.path.relpath(file_path, self.config_path.parent),
                    message=f"{type(exc).__name__}: {exc}",
                )
            ]
        return []

    def _labeled_page_error(self, exc: Exception) -> PageError:
        """Turn a labeled author-facing error into one page error.

        ``str(exc)`` already leads with the error's own source, so report that
        source (relative to the project, like a ContentError path) as the path
        and strip it from the message rather than print it twice.
        """
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
        return PageError(file_path=file_path, message=message)

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
        if is_watched(rel_path, self._theme_dirs):
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
        kind = classify_change(rel_path, self._theme_dirs)
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
        """Rebuild for one watched change and emit structured ``--events`` output.

        :param rel_path: The watched path that triggered the rebuild.
        :returns: The collected page errors, or an empty list on success.
        """
        return self._rebuild_for([rel_path], events=True)

    def _rebuild_for(self, rel_paths: Sequence[str], *, events: bool) -> list[PageError]:
        """Rebuild once for a burst of watched changes and report the outcome.

        Under ``events`` this emits a ``change`` event per path, then either a
        ``rebuild`` event carrying the output directory or an ``error`` event
        listing the collected failures. In text mode each error goes to stderr
        as ``error: <path>: <message>`` and a success prints one summary line.

        :param rel_paths: The watched paths that changed, in order, without repeats.
        :param events: Whether to report as JSON events or as text.
        :returns: The collected page errors, or an empty list on success.
        """
        if events:
            for rel_path in rel_paths:
                self.emit_event({"type": "change", "path": rel_path})

        errors = self.rebuild()
        if errors:
            if events:
                lines = [format_page_error(error) for error in errors]
                self.emit_event({"type": "error", "errors": lines})
            else:
                for error in errors:
                    print(f"error: {format_page_error(error)}", file=sys.stderr, flush=True)
            return errors

        # A rebuild that collected no errors stored its result; narrow for the type checker.
        if (result := self.last_result) is not None:
            self._follow_output_dir(result, events=events)
            self.watch_theme(result.config)
            if events:
                self.emit_event(
                    {"type": "rebuild", "status": "ok", "output_dir": result.output_dir}
                )
            else:
                duration_ms = round(result.duration_seconds * 1000)
                print(f"Rebuilt {result.page_count} pages in {duration_ms} ms", flush=True)
        return errors

    def _follow_output_dir(self, result: BuildResult, *, events: bool) -> None:
        """Serve from the output directory the latest build wrote, if it moved.

        ``output_dir`` can change in ``bartleby.yml`` while serving; the static
        app follows it so pages and reloads never point at a stale tree.
        """
        if self._files is None:
            return
        site_dir = self.config_path.parent / result.config.output_dir
        if self._files.serve_from(site_dir) and not events:
            print(f"Output directory changed to {result.output_dir}", flush=True)

    def watch_theme(self, config: BartlebyConfig) -> None:
        """Watch the directories of the theme ``config`` selects.

        A theme directory under the project is covered by the project observer
        and only needs its prefix recorded; one outside the project gets its
        own scheduled watch. Bundled themes are not watched.

        :param config: The config the latest build ran with.
        """
        project_dir = self.config_path.parent.resolve()
        prefixes: list[str] = []
        for root in theme_watch_roots(select_theme(config.theme, self.config_path.parent)):
            if root.is_relative_to(project_dir):
                prefixes.append(f"{root.relative_to(project_dir).as_posix()}/")
                continue
            prefix = f"{root.as_posix()}/"
            prefixes.append(prefix)
            if self._observer is not None and root not in self._outside_theme_roots:
                handler = _ProjectChangeHandler(root, self._on_watched_change, prefix)
                self._observer.schedule(handler, str(root), recursive=True)
                self._outside_theme_roots.add(root)
        self._theme_dirs = tuple(prefixes)

    def _on_watched_change(self, rel_path: str) -> None:
        """Queue one filesystem change when :meth:`dispatch_change` says it is watched.

        :param rel_path: The project-relative POSIX path that changed, or the
            absolute path of a file in a theme directory outside the project.
        """
        self.dispatch_change(rel_path, rebuild=lambda: self._enqueue(rel_path))

    def _enqueue(self, rel_path: str) -> None:
        """Add a watched change to the queue and wake the rebuild worker."""
        with self._pending_lock:
            if rel_path not in self._pending:
                self._pending.append(rel_path)
        self._wake.set()

    def _drain_changes(self) -> None:
        """Run one rebuild per burst of queued changes until :meth:`stop` is called.

        A burst ends once the queue has been quiet for :attr:`quiet_window`
        seconds, so an editor's probe, rename, write, and unlink are one
        rebuild and one reload.
        """
        while True:
            self._wake.wait()
            if self._stop_worker.is_set():
                return
            while True:
                self._wake.clear()
                if not self._wake.wait(timeout=self.quiet_window):
                    break
            with self._pending_lock:
                rel_paths = list(self._pending)
                self._pending.clear()
            if self._stop_worker.is_set():
                return
            errors = self._rebuild_for(rel_paths, events=self.events)
            if not errors and self._channel is not None:
                self._channel.broadcast_reload()

    def run(self, *, ready: Callable[[int], None] | None = None) -> None:
        """Serve the site and reload socket on one port until stopped or interrupted.

        A watchdog Observer watches the whole project tree; every change is
        routed through :meth:`dispatch_change`, so only paths under
        :data:`WATCHED_PATHS` or the theme's directories reach the rebuild
        queue (see :meth:`_on_watched_change`). :meth:`rebuild` retains the
        last good build on a failed rebuild, so a watcher-triggered failure
        keeps serving the previous good output.

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
            listener = _bind(self.host, self.port)
            with listener, contextlib.suppress(KeyboardInterrupt):
                built = self.build_once()
                site_dir = self.config_path.parent / built.config.output_dir
                files = _ReloadInjectingFiles(directory=site_dir, html=True)
                uvicorn_server = uvicorn.Server(
                    uvicorn.Config(build_app(files, channel), log_config=None, log_level="warning")
                )
                self._channel = channel
                self._uvicorn = uvicorn_server
                self._files = files
                asyncio.run(self._serve(uvicorn_server, channel, listener, built, ready))
        finally:
            self._channel = None
            self._uvicorn = None
            self._files = None

    def stop(self) -> None:
        """Ask a running :meth:`run` to shut down; safe to call from another thread."""
        if self._uvicorn is not None:
            self._uvicorn.should_exit = True

    async def _serve(
        self,
        uvicorn_server: uvicorn.Server,
        channel: _ReloadChannel,
        listener: socket.socket,
        built: BuildResult,
        ready: Callable[[int], None] | None,
    ) -> None:
        """Run uvicorn on ``listener`` with the project watcher and rebuild worker alive.

        Once the watcher is running, prints the startup summary (build counts, the
        bound URL, how to stop): one ``ready`` JSON object line under ``--events``,
        text otherwise.
        """
        channel.loop = asyncio.get_running_loop()
        self._stop_worker.clear()
        self._observer = _start_watcher(self.config_path.parent, self._on_watched_change)
        self.watch_theme(built.config)
        worker = threading.Thread(target=self._drain_changes, name="bartleby-rebuild", daemon=True)
        worker.start()
        try:
            self.dispatch_on_serve(uvicorn_server, config=built.config)
            port = listener.getsockname()[1]
            startup = ServeStartOutput(
                url=f"http://{url_host(self.host)}:{port}/", build=BuildOutput.from_result(built)
            )
            if self.events:
                self.emit_event(startup.to_dict())
            else:
                print(render(startup, "text"), flush=True)
            if ready is not None:
                ready(port)
            await uvicorn_server.serve(sockets=[listener])
        finally:
            self._observer.stop()
            self._stop_worker.set()
            self._wake.set()
            # Join off the loop: a rebuild in flight may still broadcast to it.
            await asyncio.to_thread(self._observer.join)
            await asyncio.to_thread(worker.join)
            self._observer = None
            self._outside_theme_roots.clear()
            channel.loop = None
