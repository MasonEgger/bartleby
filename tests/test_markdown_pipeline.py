# ABOUTME: Tests for the markdown rendering pipeline configuration and output.
# Covers default extensions, ordering (fence before superfences), and config overrides.

from __future__ import annotations

from pathlib import Path

from bartleby.config import (
    AIConfig,
    BartlebyConfig,
    DevServerConfig,
    SiteConfig,
    ThemeConfig,
)
from bartleby.markdown_pipeline import (
    RenderedContent,
    create_markdown_renderer,
    render_markdown,
)


def _config(
    *,
    markdown_extensions: list[dict[str, object] | str] | None = None,
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


def test_do_markdown_highlight() -> None:
    """do-markdown's ``<^>text<^>`` inline highlight renders as ``<mark>``."""
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


def test_extension_ordering_fence_before_superfences() -> None:
    """A do-markdown fence directive survives superfences processing in the same block."""
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
