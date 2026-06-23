# ABOUTME: Plugin system — base classes, hook dispatch, and hooks/ directory discovery.
# Provides BasePlugin (16 hooks), PluginCollection (priority-ordered dispatch), and discover_hooks.

from __future__ import annotations

import importlib.metadata
import inspect
import sys
from collections.abc import Callable
from types import ModuleType
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from pathlib import Path

PLUGIN_ENTRY_POINT_GROUP = "bartleby.plugins"

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
        """Dispatch an event through its registered handlers in priority order.

        Each handler receives the threaded ``item`` as its first positional
        argument plus ``kwargs``; a non-``None`` return replaces ``item`` for the
        next handler and is returned at the end. ``None`` returns preserve it.
        """
        handlers = self.events.get(name, [])
        current = item
        for handler in handlers:
            result = handler(current, **kwargs)
            if result is not None:
                current = result
        return current

    def run_query(self, name: str, **kwargs: Any) -> Any:
        """Dispatch a query event whose handlers take no threaded value.

        Used for ``on_page_read_source(page, config)``, where each handler is
        offered the chance to produce a value (the page source). Handlers run in
        priority-then-registration order; the first non-``None`` return wins and
        short-circuits the rest. Returns ``None`` when no handler supplies one.
        """
        for handler in self.events.get(name, []):
            result = handler(**kwargs)
            if result is not None:
                return result
        return None

    def run_lifecycle(self, name: str, **kwargs: Any) -> None:
        """Dispatch a no-threaded-value lifecycle event (e.g. ``on_shutdown``).

        Handlers run in the same priority-then-registration order as
        :meth:`run_event` but receive no threaded item, matching the spec
        signature of argument-free lifecycle hooks. Return values are ignored.
        """
        for handler in self.events.get(name, []):
            handler(**kwargs)

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

    # Put hooks/ on sys.path so a hook can import an underscore-prefixed sibling
    # helper module (which discovery itself skips) instead of being forced to
    # install shared logic as a separate package.
    hooks_path = str(hooks_dir)
    if hooks_path not in sys.path:
        sys.path.insert(0, hooks_path)

    for path in sorted(hooks_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module = _load_hook_module(path)
        _register_module_handlers(collection, module)
    return collection


def _load_hook_module(path: Path) -> ModuleType:
    """Execute a ``hooks/*.py`` file fresh into a new module each call.

    The source is read and compiled directly rather than going through
    ``SourceFileLoader``, whose mtime-keyed bytecode cache would otherwise serve
    a stale version when a hook is edited within the same second the dev server
    last loaded it. Re-reading guarantees an edited hook re-registers on the
    next rebuild.

    :param path: The hook file to load.
    :returns: A fresh module with the file's top-level definitions.
    """
    module = ModuleType(f"_bartleby_hook_{path.stem}")
    module.__file__ = str(path)
    source = path.read_text(encoding="utf-8")
    code = compile(source, str(path), "exec")
    exec(code, module.__dict__)  # noqa: S102 — trusted project-local hook code
    return module


def discover_plugins(disabled: set[str]) -> PluginCollection:
    """Discover installed plugin packages via the ``bartleby.plugins`` entry-point group.

    Each entry point names a module; its module-level ``on_<event>`` functions
    are registered exactly like a ``hooks/*.py`` file. Entry points are processed
    in alphabetical name order so installed plugins keep a deterministic relative
    order at equal priority. A name present in ``disabled`` is skipped.

    :param disabled: Plugin (entry-point) names to skip, from the ``plugins:``
        config section's ``<name>: false`` entries.
    :returns: A PluginCollection populated from every enabled entry-point module.
    """
    collection = PluginCollection()
    entry_points = importlib.metadata.entry_points(group=PLUGIN_ENTRY_POINT_GROUP)
    for entry_point in sorted(entry_points, key=lambda ep: ep.name):
        if entry_point.name in disabled:
            continue
        module = entry_point.load()
        _register_module_handlers(collection, module)
    return collection


def _register_module_handlers(collection: PluginCollection, module: ModuleType) -> None:
    """Register every module-level ``on_<event>`` function in ``module`` onto ``collection``."""
    for attr_name, attr_value in inspect.getmembers(module, inspect.isfunction):
        if attr_name in KNOWN_EVENTS:
            collection.register(attr_name, attr_value)


def _priority_of(handler: EventHandler) -> int:
    """Return the ``__event_priority__`` of ``handler`` or ``0`` when absent."""
    return getattr(handler, "__event_priority__", 0)
