# ABOUTME: Tests for the markdown rendering pipeline configuration and output.
# Covers default extensions, ordering (fence before superfences), and config overrides.

from __future__ import annotations

import warnings
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Literal

import markdown
import markwright
import pytest
from markwright import ConfigWarning, config_from_mapping, selected_extensions

from bartleby import markdown_pipeline
from bartleby.config import (
    AIConfig,
    BartlebyConfig,
    ConfigError,
    DevServerConfig,
    SiteConfig,
    ThemeConfig,
)
from bartleby.markdown_pipeline import (
    RenderedContent,
    create_markdown_renderer,
    html_to_plain_text,
    render_markdown,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


def _config(
    *,
    markdown_extensions: list[dict[str, object] | str] | None = None,
    markwright: dict[str, object] | None = None,
) -> BartlebyConfig:
    """A minimal BartlebyConfig for renderer tests."""
    return BartlebyConfig(
        site=SiteConfig(title="t", url="u"),
        nav=None,
        theme=ThemeConfig(),
        authors_file=".authors.yml",
        content_types={},
        taxonomies={},
        exclude_patterns=[],
        markdown_extensions=markdown_extensions or [],
        plugins=[],
        extra_css=[],
        extra_js=[],
        ai=AIConfig(),
        dev_server=DevServerConfig(),
        config_dir=Path("/tmp"),
        markwright=markwright or {},
    )


def test_basic_markdown_renders() -> None:
    """Headings and paragraphs render to the expected HTML tags."""
    renderer = create_markdown_renderer(_config())
    result = render_markdown("# Hello\n\nWorld", renderer)
    assert "<h1" in result.html
    assert "Hello" in result.html
    assert "<p>World</p>" in result.html


def test_fenced_code_block() -> None:
    """A fenced ``python`` block produces a highlighted ``<code>`` element."""
    source = "```python\nprint('hi')\n```\n"
    renderer = create_markdown_renderer(_config())
    html = render_markdown(source, renderer).html
    assert "<code" in html
    assert "print" in html


def test_admonition_renders() -> None:
    """``!!! note`` renders the admonition extension's HTML wrapper."""
    source = '!!! note "Heads up"\n    Important.\n'
    renderer = create_markdown_renderer(_config())
    html = render_markdown(source, renderer).html
    assert "admonition" in html
    assert "Important" in html


def test_table_renders() -> None:
    """A pipe-delimited markdown table produces a ``<table>``."""
    source = "| h1 | h2 |\n| -- | -- |\n| a  | b  |\n"
    renderer = create_markdown_renderer(_config())
    html = render_markdown(source, renderer).html
    assert "<table" in html
    assert "<th" in html


def test_toc_extracted() -> None:
    """``render_markdown`` exposes TOC tokens for the heading hierarchy."""
    source = "# H1\n\n## H2\n\n### H3\n"
    renderer = create_markdown_renderer(_config())
    result = render_markdown(source, renderer)
    assert len(result.toc_tokens) >= 1
    assert result.toc_tokens[0]["name"] == "H1"


def test_markwright_highlight() -> None:
    """markwright's ``<^>text<^>`` inline highlight renders as ``<mark>``."""
    source = "Some <^>highlighted<^> text.\n"
    renderer = create_markdown_renderer(_config())
    html = render_markdown(source, renderer).html
    assert "<mark>highlighted</mark>" in html


def test_pymdownx_tasklist() -> None:
    """pymdownx.tasklist renders ``- [x]`` items with an ``<input>`` checkbox."""
    source = "- [x] done\n- [ ] todo\n"
    renderer = create_markdown_renderer(_config())
    html = render_markdown(source, renderer).html
    assert "<input" in html
    assert "checkbox" in html


_TABS_SOURCE = '=== "Python"\n\n    one\n\n=== "Bash"\n\n    two\n'


def test_tabs_render_in_the_alternate_style_the_themes_style() -> None:
    """Tabs carry the ``tabbed-alternate`` class and a ``.tabbed-labels`` row."""
    renderer = create_markdown_renderer(_config())
    html = render_markdown(_TABS_SOURCE, renderer).html
    assert 'class="tabbed-set tabbed-alternate"' in html
    assert '<div class="tabbed-labels">' in html


def test_tabs_option_override_wins_over_the_bundled_alternate_style() -> None:
    """A ``markdown_extensions`` entry for ``pymdownx.tabbed`` replaces the bundled option."""
    overrides: list[dict[str, object] | str] = [
        {"name": "pymdownx.tabbed", "config": {"alternate_style": False}}
    ]
    renderer = create_markdown_renderer(_config(markdown_extensions=overrides))
    html = render_markdown(_TABS_SOURCE, renderer).html
    assert "tabbed-alternate" not in html


def test_extension_ordering_fence_before_superfences() -> None:
    """A markwright fence directive survives superfences processing in the same block."""
    source = "```python\n[label script.py]\nprint('hi')\n```\n"
    renderer = create_markdown_renderer(_config())
    html = render_markdown(source, renderer).html
    assert "print" in html
    # The fence preprocessor extracts [label ...] before superfences runs;
    # the postprocessor injects it back. Either way the literal `[label ...]`
    # bracket text should not be left visible in the rendered output.
    assert "[label script.py]" not in html


def test_renderer_reusable() -> None:
    """The same renderer instance handles multiple documents back-to-back."""
    renderer = create_markdown_renderer(_config())
    first = render_markdown("# First", renderer).html
    second = render_markdown("# Second", renderer).html
    assert "First" in first
    assert "Second" in second
    assert "First" not in second


def test_render_returns_rendered_content() -> None:
    """``render_markdown`` returns a :class:`RenderedContent` with html and toc_tokens."""
    renderer = create_markdown_renderer(_config())
    result = render_markdown("# Title", renderer)
    assert isinstance(result, RenderedContent)
    assert isinstance(result.html, str)
    assert isinstance(result.toc_tokens, list)


def test_config_override_applied() -> None:
    """User-provided extension config (e.g., snippets base_path) reaches Python-Markdown."""
    overrides: list[dict[str, object] | str] = [
        {"name": "pymdownx.snippets", "config": {"base_path": ["/tmp"]}}
    ]
    renderer = create_markdown_renderer(_config(markdown_extensions=overrides))
    html = render_markdown("hello", renderer).html
    assert "hello" in html


def test_html_to_plain_text_drops_tags_and_collapses_whitespace() -> None:
    """Tags vanish, entities decode, and runs of whitespace become single spaces."""
    html = (
        "<p>Run <code>bartleby build</code>\n  and read "
        "<a href='/x/'>the&nbsp;docs</a> &amp; more.</p>"
    )
    assert html_to_plain_text(html) == "Run bartleby build and read the docs & more."


_MARKWRIGHT_EXTENSIONS = (
    "fence",
    "highlight",
    "youtube",
    "codepen",
    "twitter",
    "instagram",
    "slideshow",
    "image_compare",
)


class _RecordingMarkdown(markdown.Markdown):
    """A Markdown that remembers the extension names it was built with."""

    built_with: ClassVar[list[list[str]]] = []

    def __init__(
        self,
        *,
        extensions: list[str],
        extension_configs: dict[str, dict[str, object]],
        output_format: Literal["html"],
    ) -> None:
        type(self).built_with.append(extensions)
        super().__init__(
            extensions=extensions, extension_configs=extension_configs, output_format=output_format
        )


@pytest.fixture
def loaded_extensions(monkeypatch: pytest.MonkeyPatch) -> Callable[[BartlebyConfig], list[str]]:
    """Factory: the dotted extension names `create_markdown_renderer` loads for a config."""
    monkeypatch.setattr(markdown, "Markdown", _RecordingMarkdown)
    _RecordingMarkdown.built_with.clear()

    def _loaded(config: BartlebyConfig) -> list[str]:
        create_markdown_renderer(config)
        return _RecordingMarkdown.built_with[-1]

    return _loaded


def test_no_markwright_section_loads_markwright_default_extensions(
    loaded_extensions: Callable[[BartlebyConfig], list[str]],
) -> None:
    """An absent section loads exactly what markwright selects from an empty config."""
    selected = selected_extensions(config_from_mapping({}, "bartleby.yml: markwright"))
    assert sorted(selected) == sorted(_MARKWRIGHT_EXTENSIONS)

    loaded = loaded_extensions(_config())
    assert {name for name in loaded if name.startswith("markwright.")} == {
        f"markwright.{name}" for name in selected
    }


def test_markwright_disable_drops_the_extension(
    loaded_extensions: Callable[[BartlebyConfig], list[str]],
) -> None:
    """`markwright: {disable: [youtube]}` leaves youtube out and keeps the rest."""
    loaded = set(loaded_extensions(_config(markwright={"disable": ["youtube"]})))
    assert "markwright.youtube" not in loaded
    assert {f"markwright.{name}" for name in _MARKWRIGHT_EXTENSIONS if name != "youtube"} <= loaded


def test_markwright_extensions_load_before_pymdownx(
    loaded_extensions: Callable[[BartlebyConfig], list[str]],
) -> None:
    """markwright.fence precedes superfences, so its preprocessor extracts directives first."""
    loaded = loaded_extensions(_config())
    assert loaded.index("markwright.fence") < loaded.index("pymdownx.superfences")


def test_invalid_markwright_option_raises_a_sourced_config_error() -> None:
    """Markwright's own validation error comes back labelled with bartleby.yml and the key."""
    with pytest.raises(ConfigError) as exc_info:
        create_markdown_renderer(_config(markwright={"youtube": {"bogus": 1}}))
    error = exc_info.value
    assert error.source == "bartleby.yml"
    assert error.key_path == "markwright"
    assert error.hint
    assert str(error).startswith("bartleby.yml: markwright: [youtube] unknown option 'bogus'")


def test_markwright_option_error_for_a_bad_value_is_translated() -> None:
    """A bad option value (markwright's OptionError) also surfaces as a Bartleby ConfigError."""
    with pytest.raises(ConfigError, match="'load' must be one of"):
        create_markdown_renderer(_config(markwright={"youtube": {"load": "sometimes"}}))


def test_section_goes_to_config_from_mapping_and_options_reach_the_extensions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The section reaches config_from_mapping as written; its option tables reach Markdown."""
    section: dict[str, object] = {"youtube": {"load": "click"}}
    seen_tables: list[Mapping[str, object]] = []

    def record_table(table: Mapping[str, object], source: str) -> markwright.Config:
        seen_tables.append(table)
        return config_from_mapping(table, source)

    monkeypatch.setattr(markdown_pipeline, "config_from_mapping", record_table)

    renderer = create_markdown_renderer(_config(markwright=section))
    html = render_markdown("[youtube dQw4w9WgXcQ]", renderer).html

    assert seen_tables == [section]
    # `load: click` only takes effect when extension_configs reaches the youtube extension.
    assert 'data-mw-load="click"' in html
    assert "<template" in html


def test_markwright_embeds_load_eagerly_without_a_section() -> None:
    """Bartleby sets no `load` default, so markwright's own eager mode applies."""
    html = render_markdown("[youtube dQw4w9WgXcQ]", create_markdown_renderer(_config())).html
    assert "<template" not in html
    assert "<iframe" in html


def test_markwright_config_warning_goes_to_the_bartleby_log(
    loaded_extensions: Callable[[BartlebyConfig], list[str]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An empty `enable` turns markwright off; its ConfigWarning is logged, not swallowed."""
    with caplog.at_level("WARNING", logger="bartleby"):
        loaded = loaded_extensions(_config(markwright={"enable": []}))
    assert not any(name.startswith("markwright.") for name in loaded)
    assert [
        record.getMessage()
        for record in caplog.records
        if "no markwright extensions selected" in record.getMessage()
    ]


def test_option_validation_warning_is_logged_once_and_never_raw(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A ConfigWarning raised in validation and at init logs once, never as a raw warning."""
    section: dict[str, object] = {"fence": {"allowed_environments": []}}
    with (
        warnings.catch_warnings(record=True) as raw,
        caplog.at_level("WARNING", logger="bartleby"),
    ):
        warnings.simplefilter("always")
        create_markdown_renderer(_config(markwright=section))
    assert [warning for warning in raw if issubclass(warning.category, ConfigWarning)] == []
    logged = [record.getMessage() for record in caplog.records if record.name == "bartleby"]
    assert len(logged) == 1
    assert "allowed_environments" in logged[0]


def test_markdown_extensions_still_configure_non_markwright_extensions(
    loaded_extensions: Callable[[BartlebyConfig], list[str]],
) -> None:
    """The `markdown_extensions` list keeps working beside a `markwright:` section."""
    overrides: list[dict[str, object] | str] = [
        {"name": "pymdownx.snippets", "config": {"base_path": ["/tmp"]}}
    ]
    loaded = loaded_extensions(
        _config(markdown_extensions=overrides, markwright={"disable": ["youtube"]})
    )
    assert "pymdownx.snippets" in loaded
