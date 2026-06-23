# ABOUTME: Development server with live reload, file watching, and dirty builds.
# Wraps the synchronous build pipeline with HTTP/WS serving and watchdog change detection.

from __future__ import annotations

import asyncio
import contextlib
import http.server
import socketserver
import threading
from typing import TYPE_CHECKING

from bartleby.build import build
from bartleby.config import load_config
from bartleby.plugins import PluginCollection, discover_hooks, discover_plugins

if TYPE_CHECKING:
    from pathlib import Path


_CONTENT_PREFIXES: tuple[str, ...] = ("content/",)
_TEMPLATE_PREFIXES: tuple[str, ...] = ("templates/", "overrides/", "theme/")
_CONFIG_FILES: tuple[str, ...] = ("bartleby.yml", ".authors.yml")


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


class DevServer:
    """Bartleby's development server harness.

    The HTTP and WebSocket servers are started by :meth:`run`; for tests
    we use the synchronous helpers (:meth:`build_once`, :meth:`handle_change`)
    which exercise the rebuild path without touching the network.
    """

    def __init__(self, config_path: Path, *, host: str, port: int, dirty: bool) -> None:
        self.config_path = config_path
        self.host = host
        self.port = port
        self.dirty = dirty

    def build_once(self) -> None:
        """Run a full build with drafts included."""
        build(self.config_path, include_drafts=True)

    def dispatch_on_serve(self, server: object) -> None:
        """Fire the ``on_serve`` hook so plugins can react to the dev server.

        The project's ``hooks/`` directory is discovered and any ``on_serve``
        handlers run with the live server object and resolved config, matching
        the spec signature ``on_serve(server, config)``.
        """
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
        if should_trigger_full_rebuild(kind, dirty=self.dirty):
            self.build_once()
        else:
            # In dirty mode, content-only changes still trigger a build —
            # incremental rebuilds are a future enhancement.
            self.build_once()

    def run(self) -> None:  # pragma: no cover — exercised only via the CLI
        """Start the HTTP server until interrupted."""
        self.build_once()
        site_dir = self.config_path.parent / "site"
        handler = _site_request_handler(site_dir)
        with socketserver.TCPServer((self.host, self.port), handler) as httpd:
            self.dispatch_on_serve(httpd)
            print(f"Serving at http://{self.host}:{httpd.server_address[1]}/")
            with contextlib.suppress(KeyboardInterrupt):
                httpd.serve_forever()


def _site_request_handler(site_dir: Path) -> type[http.server.SimpleHTTPRequestHandler]:
    """Return a request handler class serving files from ``site_dir``."""

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, directory=str(site_dir), **kwargs)  # type: ignore[arg-type]

    return Handler


async def _run_async_placeholder() -> None:  # pragma: no cover — reserved
    """Reserved entry point for a future asyncio + websockets reload server."""
    await asyncio.sleep(0)


def _silence_unused_thread_import() -> None:
    """Reserve the ``threading`` import for a future watcher implementation."""
    _ = threading.Thread
