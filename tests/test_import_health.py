# ABOUTME: Import-health gate: every bartleby module must import cleanly, and
# check_external_url must degrade to False on every network failure it documents.

from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING
from urllib.error import URLError

import bartleby
from bartleby.linting import check_external_url

if TYPE_CHECKING:
    import pytest


def _bartleby_module_names() -> list[str]:
    """Return the dotted name of every module under the ``bartleby`` package."""
    return [
        module_info.name
        for module_info in pkgutil.walk_packages(bartleby.__path__, prefix=f"{bartleby.__name__}.")
    ]


def test_every_bartleby_module_imports_cleanly() -> None:
    """Every module under ``src/bartleby`` imports without raising.

    A module-level syntax or import error anywhere in the package leaves the
    whole CLI dead (``cli.py`` imports most of the package at module level),
    so this walks the package and imports each module directly rather than
    relying on some other module happening to import it first.
    """
    module_names = _bartleby_module_names()
    assert module_names, "expected to discover at least one bartleby submodule"
    for module_name in module_names:
        importlib.import_module(module_name)


def test_check_external_url_returns_false_on_url_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A ``URLError`` from the probe is treated as an unreachable URL."""
    monkeypatch.setattr(
        "bartleby.linting.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(URLError("unreachable")),
    )
    assert check_external_url("https://example.com") is False


def test_check_external_url_returns_false_on_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A ``ValueError`` from the probe (e.g. a malformed URL) is treated as unreachable."""
    monkeypatch.setattr(
        "bartleby.linting.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("bad url")),
    )
    assert check_external_url("https://example.com") is False


def test_check_external_url_returns_false_on_os_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """An ``OSError`` from the probe (e.g. a connection failure) is treated as unreachable."""
    monkeypatch.setattr(
        "bartleby.linting.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("connection refused")),
    )
    assert check_external_url("https://example.com") is False
