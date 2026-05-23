# ABOUTME: Tests for the internal hook system and hooks/*.py discovery.
# Covers BasePlugin, run_event semantics, priority ordering, and hooks/ glob loading.

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from bartleby.plugins import (
    BasePlugin,
    PluginCollection,
    discover_hooks,
    event_priority,
)


def test_base_plugin_hooks_are_noop() -> None:
    """Every BasePlugin hook method returns ``None`` by default."""
    plugin = BasePlugin()
    assert plugin.on_config(None) is None  # type: ignore[arg-type]
    assert plugin.on_pre_build(None) is None  # type: ignore[arg-type]
    assert plugin.on_post_build(None) is None  # type: ignore[arg-type]
    assert plugin.on_page_markdown("md", None, None) is None  # type: ignore[arg-type]


def test_plugin_collection_register_and_run() -> None:
    """Registering a handler against an event makes ``run_event`` call it."""
    collection = PluginCollection()
    calls: list[object] = []

    def handler(item: str, **_: object) -> str:
        calls.append(item)
        return item + "!"

    collection.register("on_config", handler)
    result = collection.run_event("on_config", "hi")
    assert calls == ["hi"]
    assert result == "hi!"


def test_run_event_none_keeps_value() -> None:
    """A handler returning ``None`` leaves the item unchanged."""
    collection = PluginCollection()

    def handler(item: str, **_: object) -> None:
        return None

    collection.register("on_config", handler)
    assert collection.run_event("on_config", "original") == "original"


def test_run_event_new_value_replaces() -> None:
    """A non-``None`` return replaces the threaded value."""
    collection = PluginCollection()
    collection.register("on_config", lambda item, **_: "replaced")
    assert collection.run_event("on_config", "original") == "replaced"


def test_event_priority_ordering() -> None:
    """Handlers with higher ``event_priority`` are called first."""
    collection = PluginCollection()
    order: list[str] = []

    @event_priority(50)
    def high(item: str, **_: object) -> str:
        order.append("high")
        return item

    @event_priority(10)
    def low(item: str, **_: object) -> str:
        order.append("low")
        return item

    collection.register("on_config", low)
    collection.register("on_config", high)
    collection.run_event("on_config", "x")
    assert order == ["high", "low"]


def test_event_priority_default() -> None:
    """Handlers without an ``@event_priority`` decorator default to priority 0."""
    collection = PluginCollection()
    order: list[str] = []

    def first(item: str, **_: object) -> str:
        order.append("first")
        return item

    @event_priority(1)
    def prioritised(item: str, **_: object) -> str:
        order.append("prioritised")
        return item

    collection.register("on_config", first)
    collection.register("on_config", prioritised)
    collection.run_event("on_config", "x")
    assert order == ["prioritised", "first"]


def test_multiple_handlers_chain() -> None:
    """Three handlers modifying the same event compose left-to-right by priority."""
    collection = PluginCollection()
    collection.register("on_page_markdown", lambda item, **_: item + "1")
    collection.register("on_page_markdown", lambda item, **_: item + "2")
    collection.register("on_page_markdown", lambda item, **_: item + "3")
    result = collection.run_event("on_page_markdown", "x")
    # Order is registration order at priority 0; all increment.
    assert result == "x123"


def test_discover_hooks_directory() -> None:
    """``discover_hooks`` glob-loads every ``hooks/*.py`` and registers on_* functions."""
    project_dir = Path(__file__).parent / "fixtures" / "hooks_site"
    collection = discover_hooks(project_dir)
    assert "on_page_markdown" in collection.events
    assert "on_env" in collection.events
    assert len(collection.events["on_page_markdown"]) == 1


def test_discover_hooks_module_level_only() -> None:
    """Functions named ``on_<event>`` are registered; private/helper names are not."""
    project_dir = Path(__file__).parent / "fixtures" / "hooks_site"
    collection = discover_hooks(project_dir)
    # No "_helper" or arbitrary helpers got picked up — only on_* names map to events.
    for event_name in collection.events:
        assert event_name.startswith("on_")


def test_discover_hooks_missing_directory_is_ok(tmp_path: Path) -> None:
    """A site without a ``hooks/`` directory returns an empty PluginCollection."""
    collection = discover_hooks(tmp_path)
    assert collection.events == {}


def test_no_entry_point_discovery() -> None:
    """``discover_hooks`` must never call ``importlib.metadata.entry_points``."""
    project_dir = Path(__file__).parent / "fixtures" / "hooks_site"
    with patch("importlib.metadata.entry_points") as mock_ep:
        discover_hooks(project_dir)
    mock_ep.assert_not_called()


def test_event_priority_works_on_methods() -> None:
    """``@event_priority`` decorates instance methods just as well as plain functions."""

    class Plugin(BasePlugin):
        @event_priority(99)
        def on_config(self, config: object) -> object:
            return config

    method = Plugin().on_config
    assert getattr(method, "__event_priority__", 0) == 99
