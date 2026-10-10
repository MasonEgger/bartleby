# ABOUTME: Tests for the shared error-message formatter.
# Pins the "source: key path: message (fix: hint)" contract every structured error follows.

from __future__ import annotations

from pathlib import Path

from bartleby.errors import format_error


def test_format_error_orders_source_key_path_message_and_hint() -> None:
    """Every part present renders as ``source: key: message (fix: hint)``."""
    text = format_error(
        "required field is missing",
        source=Path("/site/bartleby.yml"),
        key_path="site.url",
        hint="add `url:` under `site:`",
    )
    assert text == (
        "/site/bartleby.yml: site.url: required field is missing (fix: add `url:` under `site:`)"
    )


def test_format_error_message_only() -> None:
    """With no location and no hint the message passes through unchanged."""
    assert format_error("something broke") == "something broke"


def test_format_error_skips_missing_parts() -> None:
    """A source without a key path, or a key path without a hint, drops only that part."""
    assert format_error("bad", source="a.yml") == "a.yml: bad"
    assert format_error("bad", key_path="theme") == "theme: bad"
    assert format_error("bad", hint="fix it") == "bad (fix: fix it)"
