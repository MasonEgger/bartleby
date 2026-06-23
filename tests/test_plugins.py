# ABOUTME: Tests for the internal hook system and hooks/*.py discovery.
# Covers BasePlugin, run_event semantics, priority ordering, and hooks/ glob loading.

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from bartleby.plugins import (
    KNOWN_EVENTS,
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


# --- Step 8: every declared hook event fires at the right point ---------------

# The build-phase and per-page events Bartleby dispatches during a full build.
# Lifecycle events (on_startup/on_shutdown) and on_serve are driven from the CLI
# and dev server, so they are covered by their own tests below.
_BUILD_EVENTS: tuple[str, ...] = (
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
)

# Per-page events fire once per rendered page; build-phase events fire once total.
_PER_PAGE_EVENTS: frozenset[str] = frozenset(
    {
        "on_pre_page",
        "on_page_read_source",
        "on_page_markdown",
        "on_page_content",
        "on_page_context",
        "on_post_page",
    }
)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Copy the sample fixture site into a temp dir so build can mutate ``site/``."""
    source = Path(__file__).parent / "fixtures" / "site"
    destination = tmp_path / "site_project"
    shutil.copytree(source, destination)
    return destination


def _install_recording_hook(project_dir: Path) -> Path:
    """Write a ``hooks/record.py`` that logs every build event call to JSON.

    Each handler appends ``{"event": name, "args": [<repr of positional args>]}``
    to a JSON-lines file next to ``bartleby.yml`` and returns ``None`` so it does
    not perturb the pipeline. Returns the path the records are written to.
    """
    hooks_dir = project_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    record_path = project_dir / "events.jsonl"
    handlers = "\n".join(
        f"def {event}(*args, **kwargs):\n    _record({event!r}, args, kwargs)\n    return None\n"
        for event in _BUILD_EVENTS
    )
    (hooks_dir / "record.py").write_text(
        "# ABOUTME: Test hook recording every build event for the dispatch test.\n"
        "# Writes one JSON object per call to events.jsonl for assertions.\n"
        "from __future__ import annotations\n"
        "import json\n"
        "from pathlib import Path\n"
        "\n"
        "RECORD = Path(__file__).parent.parent / 'events.jsonl'\n"
        "\n"
        "def _record(event, args, kwargs):\n"
        "    line = json.dumps({'event': event, 'argc': len(args),\n"
        "                       'kwargs': sorted(kwargs)})\n"
        "    with RECORD.open('a', encoding='utf-8') as handle:\n"
        "        handle.write(line + '\\n')\n"
        "\n" + handlers,
        encoding="utf-8",
    )
    return record_path


def _recorded_events(record_path: Path) -> list[str]:
    """Return the ``event`` name from each JSON line in order."""
    text = record_path.read_text(encoding="utf-8")
    return [json.loads(line)["event"] for line in text.splitlines() if line.strip()]


@pytest.mark.parametrize("event", _BUILD_EVENTS)
def test_build_dispatches_every_declared_event(project: Path, event: str) -> None:
    """Every declared build/per-page event fires at least once during a build."""
    from bartleby.build import build

    record_path = _install_recording_hook(project)
    build(project / "bartleby.yml")
    fired = _recorded_events(record_path)
    assert event in fired, f"{event} never dispatched during build"


def test_build_phase_events_fire_exactly_once(project: Path) -> None:
    """Build-phase (non-per-page) events fire exactly once per build."""
    from bartleby.build import build

    record_path = _install_recording_hook(project)
    build(project / "bartleby.yml")
    fired = _recorded_events(record_path)
    for event in _BUILD_EVENTS:
        if event in _PER_PAGE_EVENTS:
            continue
        assert fired.count(event) == 1, f"{event} fired {fired.count(event)} times, expected 1"


def test_per_page_events_fire_once_per_published_page(project: Path) -> None:
    """Per-page events fire once for each rendered page (content + generated)."""
    from bartleby.build import build

    record_path = _install_recording_hook(project)
    result = build(project / "bartleby.yml")
    fired = _recorded_events(record_path)
    for event in _PER_PAGE_EVENTS:
        assert fired.count(event) == result.page_count, (
            f"{event} fired {fired.count(event)} times, expected {result.page_count}"
        )


def test_on_page_read_source_replaces_source_when_returning_string(project: Path) -> None:
    """A non-``None`` return from on_page_read_source replaces the page source."""
    from bartleby.build import build

    hooks_dir = project / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    (hooks_dir / "source.py").write_text(
        "# ABOUTME: Test hook that overrides one page's source via on_page_read_source.\n"
        "# Returns replacement markdown so the build proves the return value is used.\n"
        "from __future__ import annotations\n"
        "\n"
        "MARKER = 'SOURCE_REPLACED_BY_HOOK'\n"
        "\n"
        "def on_page_read_source(page, config):\n"
        "    if page.title == 'First Post':\n"
        "        return f'# {MARKER}\\n'\n"
        "    return None\n",
        encoding="utf-8",
    )
    build(project / "bartleby.yml")
    rendered = (project / "site" / "blog" / "posts" / "first-post" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "SOURCE_REPLACED_BY_HOOK" in rendered


def test_on_page_content_modifies_rendered_html(project: Path) -> None:
    """A return from on_page_content replaces the rendered HTML downstream."""
    from bartleby.build import build

    hooks_dir = project / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    (hooks_dir / "content.py").write_text(
        "# ABOUTME: Test hook that appends a marker to rendered HTML.\n"
        "# Proves on_page_content's return value flows into the template render.\n"
        "from __future__ import annotations\n"
        "\n"
        "def on_page_content(html, page, config):\n"
        "    return html + '<!-- CONTENT_HOOK_RAN -->'\n",
        encoding="utf-8",
    )
    build(project / "bartleby.yml")
    rendered = (project / "site" / "blog" / "posts" / "first-post" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "CONTENT_HOOK_RAN" in rendered


def test_on_post_build_fires_after_output_written(project: Path) -> None:
    """on_post_build runs once, after the site/ output exists."""
    from bartleby.build import build

    hooks_dir = project / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    (hooks_dir / "postbuild.py").write_text(
        "# ABOUTME: Test hook asserting site/ is present when on_post_build fires.\n"
        "# Writes a sentinel only if the index page already exists on disk.\n"
        "from __future__ import annotations\n"
        "from pathlib import Path\n"
        "\n"
        "def on_post_build(config):\n"
        "    site = Path(config.config_dir) / 'site' / 'index.html'\n"
        "    sentinel = Path(config.config_dir) / 'postbuild_saw_output.txt'\n"
        "    sentinel.write_text('yes' if site.exists() else 'no', encoding='utf-8')\n",
        encoding="utf-8",
    )
    build(project / "bartleby.yml")
    sentinel = project / "postbuild_saw_output.txt"
    assert sentinel.exists()
    assert sentinel.read_text(encoding="utf-8") == "yes"


def test_on_startup_fires_once_with_command_name(project: Path) -> None:
    """on_startup runs once at build start, receiving the command name."""
    from bartleby.build import build

    hooks_dir = project / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    (hooks_dir / "startup.py").write_text(
        "# ABOUTME: Test hook recording the on_startup command argument.\n"
        "# Writes the received command name to startup.txt for assertion.\n"
        "from __future__ import annotations\n"
        "from pathlib import Path\n"
        "\n"
        "def on_startup(command):\n"
        "    Path(__file__).parent.parent.joinpath('startup.txt').write_text(\n"
        "        command, encoding='utf-8')\n",
        encoding="utf-8",
    )
    build(project / "bartleby.yml")
    assert (project / "startup.txt").read_text(encoding="utf-8") == "build"


def test_on_shutdown_fires_with_no_arguments(project: Path) -> None:
    """on_shutdown runs once at the end and takes no positional arguments."""
    from bartleby.build import build

    hooks_dir = project / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    (hooks_dir / "shutdown.py").write_text(
        "# ABOUTME: Test hook proving on_shutdown is called with no arguments.\n"
        "# A zero-arg signature must not raise; it writes a sentinel file.\n"
        "from __future__ import annotations\n"
        "from pathlib import Path\n"
        "\n"
        "def on_shutdown():\n"
        "    Path(__file__).parent.parent.joinpath('shutdown.txt').write_text(\n"
        "        'ran', encoding='utf-8')\n",
        encoding="utf-8",
    )
    build(project / "bartleby.yml")
    assert (project / "shutdown.txt").read_text(encoding="utf-8") == "ran"


def test_on_serve_fires_with_server_and_config(project: Path) -> None:
    """on_serve runs when the dev server dispatches it, with server and config."""
    from bartleby.server import DevServer

    hooks_dir = project / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    (hooks_dir / "serve.py").write_text(
        "# ABOUTME: Test hook recording that on_serve received a server and config.\n"
        "# Writes a sentinel only when both arguments are present.\n"
        "from __future__ import annotations\n"
        "from pathlib import Path\n"
        "\n"
        "def on_serve(server, config):\n"
        "    ok = server is not None and config is not None\n"
        "    Path(config.config_dir).joinpath('serve.txt').write_text(\n"
        "        'ok' if ok else 'bad', encoding='utf-8')\n",
        encoding="utf-8",
    )
    server = DevServer(project / "bartleby.yml", host="127.0.0.1", port=0, dirty=False)
    sentinel_server = object()
    server.dispatch_on_serve(sentinel_server)
    assert (project / "serve.txt").read_text(encoding="utf-8") == "ok"


def test_base_plugin_defines_a_method_for_every_known_event() -> None:
    """BasePlugin must define a callable method for every entry in KNOWN_EVENTS."""
    plugin = BasePlugin()
    for event in KNOWN_EVENTS:
        assert hasattr(plugin, event), f"BasePlugin missing method for {event}"
        assert callable(getattr(plugin, event))


def test_known_events_matches_spec_hook_set() -> None:
    """KNOWN_EVENTS is exactly the 16 hook events the spec declares.

    The spec lists 16 events; ``on_pages`` is an internal convenience that is not
    a public hook, so it must not leak into the declared event set.
    """
    expected = {
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
    }
    assert set(KNOWN_EVENTS) == expected


def test_priority_then_registration_ordering_for_arbitrary_event() -> None:
    """For any event, handlers run by priority desc, then registration order."""
    collection = PluginCollection()
    order: list[str] = []

    def first(item: object, **_: object) -> None:
        order.append("first")
        return None

    def second(item: object, **_: object) -> None:
        order.append("second")
        return None

    @event_priority(10)
    def prioritised(item: object, **_: object) -> None:
        order.append("prioritised")
        return None

    collection.register("on_files", first)
    collection.register("on_files", second)
    collection.register("on_files", prioritised)
    collection.run_event("on_files", object())
    assert order == ["prioritised", "first", "second"]
