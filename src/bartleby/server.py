# ABOUTME: Development server with live reload, file watching, and dirty builds.
# Wraps the synchronous build pipeline with HTTP/WS serving and watchdog change detection.

from __future__ import annotations

import contextlib
import http.server
import json
import socketserver
import sys
from typing import TYPE_CHECKING

from bartleby.build import BuildError, build, format_page_error
from bartleby.config import load_config
from bartleby.plugins import PluginCollection, discover_hooks, discover_plugins

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

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

# Injected into served pages so the browser reconnects and reloads on rebuild.
# It is added only by :func:`inject_reload_snippet` in serve mode, never by the
# build pipeline, so ``bartleby build`` output stays free of dev-only markup.
RELOAD_SNIPPET = (
    "<script>(function(){"
    "var ws=new WebSocket('ws://'+location.host+'/__bartleby_reload');"
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

    def run(self, *, ready: Callable[[socketserver.TCPServer], None] | None = None) -> None:
        """Start the HTTP server, serving the built site until interrupted.

        :param ready: Optional callback fired once the socket is bound and
            listening, receiving the live ``TCPServer``. Tests use it to learn
            the ephemeral port and to call :meth:`~socketserver.BaseServer.shutdown`
            from another thread; in normal CLI use it is ``None``.
        """
        self.build_once()
        config = load_config(self.config_path)
        site_dir = self.config_path.parent / config.output_dir
        handler = _site_request_handler(site_dir)
        with socketserver.TCPServer((self.host, self.port), handler) as httpd:
            self.dispatch_on_serve(httpd, config=config)
            print(f"Serving at http://{self.host}:{httpd.server_address[1]}/")
            if ready is not None:
                ready(httpd)
            with contextlib.suppress(KeyboardInterrupt):
                httpd.serve_forever()


def _site_request_handler(site_dir: Path) -> type[http.server.SimpleHTTPRequestHandler]:
    """Return a request handler class serving files from ``site_dir``."""

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, directory=str(site_dir), **kwargs)  # type: ignore[arg-type]

    return Handler
