# ABOUTME: Plugin system — base classes, hook dispatch, and hooks/ directory discovery.
# Provides BasePlugin (16 hooks), PluginCollection (priority-ordered dispatch), and discover_hooks.

from __future__ import annotations

import importlib.util
import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from pathlib import Path

EventHandler = Callable[..., Any]

KNOWN_EVENTS: tuple[str, ...] = (
    "on_startup",
    "on_shutdown",
    "on_config",
    "on_pre_build",
    "on_files",
    "on_nav",
    "on_env",
    "on_pre_page",
    "on_page_read_source",
    "on_page_markdown",
    "on_page_content",
    "on_page_context",
    "on_post_page",
    "on_post_build",
    "on_build_error",
    "on_serve",
    "on_pages",
)


F = TypeVar("F", bound=Callable[..., Any])


def event_priority(priority: int) -> Callable[[F], F]:
    """Decorator that tags a handler with an integer priority (higher runs first)."""

    def decorator(func: F) -> F:
        func.__event_priority__ = priority  # type: ignore[attr-defined]
        return func

    return decorator


class BasePlugin:
    """Internal base class for Bartleby's own feature modules.

    User-facing extensions live in ``hooks/*.py`` and use module-level
    ``on_<event>`` functions, not BasePlugin subclasses. This class is kept
    internal so future Bartleby refactors can group related handlers into
    a single object.
    """

    def on_startup(self, command: str) -> None: ...  # noqa: D401
    def on_shutdown(self) -> None: ...
    def on_config(self, config: object) -> object | None: ...
    def on_pre_build(self, config: object) -> None: ...
    def on_files(self, files: object, config: object) -> object | None: ...
    def on_nav(self, nav: object, config: object) -> object | None: ...
    def on_env(self, env: object, config: object) -> object | None: ...
    def on_pre_page(self, page: object, config: object) -> object | None: ...
    def on_page_read_source(self, page: object, config: object) -> object | None: ...
    def on_page_markdown(
        self, markdown: object, page: object, config: object
    ) -> object | None: ...
    def on_page_content(self, html: object, page: object, config: object) -> object | None: ...
    def on_page_context(self, context: object, page: object, config: object) -> object | None: ...
    def on_post_page(self, output: object, page: object, config: object) -> object | None: ...
    def on_post_build(self, config: object) -> None: ...
    def on_build_error(self, error: object) -> None: ...
    def on_serve(self, server: object, config: object) -> None: ...


class PluginCollection:
    """Holds registered event handlers and dispatches build hooks."""

    def __init__(self) -> None:
        self.events: dict[str, list[EventHandler]] = {}

    def register(self, name: str, handler: EventHandler) -> None:
        """Register ``handler`` for event ``name``, ordered by ``@event_priority``."""
        self.events.setdefault(name, []).append(handler)
        # Keep the list ordered by priority (descending) for each registration.
        self.events[name].sort(key=lambda fn: -_priority_of(fn))

    def run_event(self, name: str, item: Any, **kwargs: Any) -> Any:
        """Dispatch an event through its registered handlers in priority order."""
        handlers = self.events.get(name, [])
        current = item
        for handler in handlers:
            result = handler(current, **kwargs)
            if result is not None:
                current = result
        return current

    def merge(self, other: PluginCollection) -> None:
        """Fold another PluginCollection's handlers into this one."""
        for name, handlers in other.events.items():
            for handler in handlers:
                self.register(name, handler)


def discover_hooks(project_dir: Path) -> PluginCollection:
    """Glob-load ``project_dir/hooks/*.py`` and register module-level ``on_<event>`` handlers.

    :param project_dir: The user's project directory.
    :returns: A PluginCollection populated from the loaded modules. Returns
        an empty collection when ``hooks/`` does not exist.
    """
    collection = PluginCollection()
    hooks_dir = project_dir / "hooks"
    if not hooks_dir.exists() or not hooks_dir.is_dir():
        return collection

    for path in sorted(hooks_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module_name = f"_bartleby_hook_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for attr_name, attr_value in inspect.getmembers(module, inspect.isfunction):
            if attr_name in KNOWN_EVENTS:
                collection.register(attr_name, attr_value)
    return collection


def _priority_of(handler: EventHandler) -> int:
    """Return the ``__event_priority__`` of ``handler`` or ``0`` when absent."""
    return getattr(handler, "__event_priority__", 0)
