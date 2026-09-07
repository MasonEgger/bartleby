# ABOUTME: Tests for the hybrid Tailwind pipeline — binary resolver and CSS preference.
# Covers PATH/cache/download resolution, checksum-abort, and compiled-CSS preference.

from __future__ import annotations

import hashlib
import json
import re
import stat
from typing import TYPE_CHECKING

import pytest

import bartleby.theme_compile as theme_compile
from bartleby.theme_compile import (
    PINNED_TAILWIND_VERSION,
    ThemeCompileError,
    ThemeCompileResult,
    active_theme_css,
    resolve_tailwind_binary,
    tailwind_asset_name,
)

if TYPE_CHECKING:
    from pathlib import Path


def _make_executable(path: Path) -> None:
    """Create a fake binary file and mark it executable."""
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def test_resolver_prefers_binary_on_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A ``tailwindcss`` binary on PATH wins over cache and download."""
    path_dir = tmp_path / "bin"
    path_dir.mkdir()
    on_path = path_dir / "tailwindcss"
    _make_executable(on_path)
    monkeypatch.setenv("PATH", str(path_dir))
    cache_dir = tmp_path / "cache"

    binary, origin = resolve_tailwind_binary(cache_dir=cache_dir)

    assert binary == on_path
    assert origin == "path"


def test_resolver_uses_cached_binary_when_not_on_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With nothing on PATH, a previously cached binary is reused (no download)."""
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cached = cache_dir / f"tailwindcss-{PINNED_TAILWIND_VERSION}"
    _make_executable(cached)

    binary, origin = resolve_tailwind_binary(cache_dir=cache_dir)

    assert binary == cached
    assert origin == "cached"


def test_resolver_does_not_download_implicitly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no PATH binary and no cache, resolution aborts unless download is allowed."""
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    cache_dir = tmp_path / "cache"

    with pytest.raises(ThemeCompileError):
        resolve_tailwind_binary(cache_dir=cache_dir, allow_download=False)


def test_resolver_downloads_when_allowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When download is allowed and PATH/cache miss, the binary is fetched and cached."""
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    cache_dir = tmp_path / "cache"
    payload = b"fake-tailwind-binary"
    digest = hashlib.sha256(payload).hexdigest()

    def fake_fetch(url: str) -> bytes:
        return payload

    binary, origin = resolve_tailwind_binary(
        cache_dir=cache_dir,
        allow_download=True,
        expected_sha256=digest,
        fetch=fake_fetch,
    )

    assert origin == "downloaded"
    assert binary.exists()
    assert binary.read_bytes() == payload
    assert binary.stat().st_mode & stat.S_IXUSR


def test_download_checksum_mismatch_aborts_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A SHA-256 mismatch raises and leaves no partial binary in the cache."""
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    cache_dir = tmp_path / "cache"

    def fake_fetch(url: str) -> bytes:
        return b"corrupted-payload"

    with pytest.raises(ThemeCompileError):
        resolve_tailwind_binary(
            cache_dir=cache_dir,
            allow_download=True,
            expected_sha256="0" * 64,
            fetch=fake_fetch,
        )

    cached = cache_dir / f"tailwindcss-{PINNED_TAILWIND_VERSION}"
    assert not cached.exists(), "partial binary left behind after checksum failure"
    # No stray temp files either.
    assert not any(cache_dir.glob("*.tmp")) if cache_dir.exists() else True


def test_refresh_forces_redownload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``refresh=True`` ignores a cached binary and re-downloads."""
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cached = cache_dir / f"tailwindcss-{PINNED_TAILWIND_VERSION}"
    cached.write_bytes(b"stale")
    cached.chmod(cached.stat().st_mode | stat.S_IXUSR)

    payload = b"fresh-binary"
    digest = hashlib.sha256(payload).hexdigest()

    binary, origin = resolve_tailwind_binary(
        cache_dir=cache_dir,
        allow_download=True,
        refresh=True,
        expected_sha256=digest,
        fetch=lambda url: payload,
    )

    assert origin == "downloaded"
    assert binary.read_bytes() == payload


def test_release_sha256_covers_every_asset_name() -> None:
    """The pinned-release digest map has exactly one entry per platform asset."""
    expected_assets = {
        "tailwindcss-linux-x64",
        "tailwindcss-linux-arm64",
        "tailwindcss-macos-x64",
        "tailwindcss-macos-arm64",
        "tailwindcss-windows-x64.exe",
        "tailwindcss-windows-arm64.exe",
    }

    assert set(theme_compile._RELEASE_SHA256) == expected_assets


def test_release_sha256_values_are_hex_digests() -> None:
    """Every recorded digest is a 64-character lowercase hex SHA-256 string."""
    digest_pattern = re.compile(r"^[0-9a-f]{64}$")

    for asset, digest in theme_compile._RELEASE_SHA256.items():
        assert digest_pattern.match(digest), (
            f"{asset} digest {digest!r} is not a sha256 hex string"
        )


def test_download_binary_uses_release_map_when_no_digest_injected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no ``expected_sha256`` override, ``_download_binary`` falls back to the release map."""
    asset = tailwind_asset_name()
    payload = b"fake-tailwind-binary-from-release-map"
    digest = hashlib.sha256(payload).hexdigest()
    monkeypatch.setitem(theme_compile._RELEASE_SHA256, asset, digest)

    binary, origin = theme_compile._download_binary(
        cache_dir=tmp_path,
        expected_sha256=None,
        fetch=lambda url: payload,
    )

    assert origin == "downloaded"
    assert binary.exists()
    assert binary.read_bytes() == payload


def test_active_theme_css_prefers_compiled_when_newer(tmp_path: Path) -> None:
    """``.bartleby/theme.css`` wins when present and newer than the template tree."""
    project_dir = tmp_path / "project"
    templates_dir = project_dir / "templates"
    templates_dir.mkdir(parents=True)
    (templates_dir / "base.html").write_text("<html></html>", encoding="utf-8")

    compiled = project_dir / ".bartleby" / "theme.css"
    compiled.parent.mkdir(parents=True)
    compiled.write_text("/* compiled */", encoding="utf-8")
    # Make the compiled CSS clearly newer than the template tree.
    old = templates_dir.stat().st_mtime - 100
    import os

    os.utime(templates_dir / "base.html", (old, old))

    resolved = active_theme_css(project_dir)

    assert resolved == compiled


def test_active_theme_css_falls_back_when_absent(tmp_path: Path) -> None:
    """With no compiled CSS, the resolver returns None so the shipped CSS is used."""
    project_dir = tmp_path / "project"
    (project_dir / "templates").mkdir(parents=True)

    assert active_theme_css(project_dir) is None


def test_active_theme_css_ignores_stale_compiled(tmp_path: Path) -> None:
    """A compiled CSS older than the template tree is not preferred (stale)."""
    project_dir = tmp_path / "project"
    templates_dir = project_dir / "templates"
    templates_dir.mkdir(parents=True)

    compiled = project_dir / ".bartleby" / "theme.css"
    compiled.parent.mkdir(parents=True)
    compiled.write_text("/* compiled */", encoding="utf-8")

    # Template edited after compile.
    import os
    import time

    later = time.time() + 100
    template = templates_dir / "base.html"
    template.write_text("<html></html>", encoding="utf-8")
    os.utime(template, (later, later))

    assert active_theme_css(project_dir) is None


def test_result_json_shape() -> None:
    """ThemeCompileResult emits the documented JSON shape."""
    result = ThemeCompileResult(
        css_path=".bartleby/theme.css",
        binary="cached",
        duration_ms=410,
        classes_scanned=1842,
    )
    payload = json.loads(json.dumps(result.to_dict()))
    assert payload == {
        "status": "success",
        "css_path": ".bartleby/theme.css",
        "binary": "cached",
        "duration_ms": 410,
        "classes_scanned": 1842,
    }
    assert result.exit_code == 0
