# ABOUTME: Plugin system — base classes, hook dispatch, and plugin discovery.
# Step 10 provides only the dispatch infrastructure; full plugins land in Step 21.

from __future__ import annotations

from collections.abc import Callable
from typing import Any

EventHandler = Callable[..., Any]


class PluginCollection:
    """Holds registered event handlers and dispatches build hooks.

    Step 10 introduces this so the build pipeline has live ``run_event``
    call sites even before any plugins exist. Each registered event maps
    to a list of callables; with no plugins registered the dispatch is a
    pass-through that returns the input ``item`` unchanged.
    """

    def __init__(self) -> None:
        self.events: dict[str, list[EventHandler]] = {}

    def register(self, name: str, handler: EventHandler) -> None:
        """Register ``handler`` to be called when ``name`` fires."""
        self.events.setdefault(name, []).append(handler)

    def run_event(self, name: str, item: Any, **kwargs: Any) -> Any:
        """Dispatch an event; return either the original or a handler's replacement.

        :param name: Event name (e.g. ``"on_page_markdown"``).
        :param item: The value being passed through the hook chain.
        :param kwargs: Additional context the handlers may read.
        :returns: ``item`` unchanged when no handler is registered, otherwise
            the value of the last handler that returned non-``None``.
        """
        handlers = self.events.get(name, [])
        current = item
        for handler in handlers:
            result = handler(current, **kwargs)
            if result is not None:
                current = result
        return current
