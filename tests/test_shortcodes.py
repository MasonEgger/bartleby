# ABOUTME: Tests for shortcode parsing and rendering.
# Covers block + inline shortcodes, args, include, unknown shortcodes, and passthrough.

from __future__ import annotations

from pathlib import Path

import jinja2
import pytest

from bartleby.shortcodes import ShortcodeError, process_shortcodes

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "templates"


@pytest.fixture
def env() -> jinja2.Environment:
    """A Jinja2 environment with the test template fixtures on the search path."""
    loader = jinja2.FileSystemLoader([str(FIXTURE_ROOT)])
    return jinja2.Environment(loader=loader, autoescape=False)


def test_block_shortcode(env: jinja2.Environment) -> None:
    """``[% note %]...[% /note %]`` renders via ``shortcodes/note.html``."""
    source = "[% note %]\nImportant\n[% /note %]\n"
    out = process_shortcodes(source, {"build": {"bartleby_version": "0.1.0"}}, env)
    assert '<div class="shortcode-note">' in out
    assert "Important" in out


def test_inline_shortcode(env: jinja2.Environment) -> None:
    """``[% version %]`` (no closing tag) renders inline."""
    source = "Built with Bartleby [% version %]\n"
    out = process_shortcodes(source, {"build": {"bartleby_version": "0.1.0"}}, env)
    assert "0.1.0" in out


def test_shortcode_with_args(env: jinja2.Environment) -> None:
    """``key="value"`` pairs after the name are exposed in the template context."""
    source = '[% callout type="warning" title="Careful" %]text[% /callout %]'
    out = process_shortcodes(source, {}, env)
    assert 'class="callout callout-warning"' in out
    assert "<h3>Careful</h3>" in out
    assert "text" in out


def test_unknown_shortcode_raises(env: jinja2.Environment) -> None:
    """A shortcode whose template file is missing raises :class:`ShortcodeError`."""
    source = "[% nonexistent %]"
    with pytest.raises(ShortcodeError) as exc:
        process_shortcodes(source, {}, env)
    assert "nonexistent" in str(exc.value)


def test_shortcode_has_page_context(env: jinja2.Environment) -> None:
    """The supplied context is passed straight through to the template."""
    source = "[% version %]"
    out = process_shortcodes(source, {"build": {"bartleby_version": "9.9.9"}}, env)
    assert "9.9.9" in out


def test_no_shortcodes_passthrough(env: jinja2.Environment) -> None:
    """Markdown without any ``[% %]`` markers comes back unchanged."""
    source = "# Heading\n\nJust regular markdown.\n"
    out = process_shortcodes(source, {}, env)
    assert out == source
