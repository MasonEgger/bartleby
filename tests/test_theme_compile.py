# ABOUTME: Tests for the hybrid Tailwind pipeline — binary resolver and CSS preference.
# Covers PATH/cache/download resolution, checksum-abort, and compiled-CSS preference.

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path, PureWindowsPath

import pytest

import bartleby.theme_compile as theme_compile
from bartleby.theme_compile import (
    PINNED_TAILWIND_VERSION,
    ThemeCompileError,
    ThemeCompileResult,
    active_theme_css,
    compile_theme_css,
    css_import_line,
    default_cache_dir,
    resolve_tailwind_binary,
    tailwind_asset_name,
)
from bartleby.theme_loader import (
    ResolvedTheme,
    ThemeLayer,
    load_manifest,
    resolve_theme,
)


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


# --- compile_theme_css: chain-aware sources and token emission -----------------

THEMES = Path(__file__).parent / "fixtures" / "themes"


class _RecordedRun:
    """Stand-in for ``subprocess.run`` that records the command and writes the output."""

    def __init__(self) -> None:
        self.command: list[str] = []
        self.kwargs: dict[str, object] = {}

    def __call__(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.command = command
        self.kwargs = kwargs
        output = Path(command[command.index("--output") + 1])
        output.write_text(".a{color:red}", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


def _compile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    theme: ResolvedTheme,
    tokens: dict[str, str] | None = None,
) -> tuple[Path, _RecordedRun]:
    """Run ``compile_theme_css`` against a fake binary and a recording ``subprocess.run``."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _make_executable(bin_dir / "tailwindcss")
    monkeypatch.setenv("PATH", str(bin_dir))
    recorder = _RecordedRun()
    monkeypatch.setattr(theme_compile.subprocess, "run", recorder)
    project_dir = tmp_path / "project"
    project_dir.mkdir(exist_ok=True)
    compile_theme_css(project_dir, theme, tokens or {}, cache_dir=tmp_path / "cache")
    return project_dir, recorder


def _arg(command: list[str], flag: str) -> str:
    return command[command.index(flag) + 1]


def test_compile_falls_back_to_parent_sources_when_leaf_has_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A child without tailwind sources uses the parent's --config and --input."""
    theme = resolve_theme(project_dir=tmp_path, path=str(THEMES / "child"))

    project_dir, recorder = _compile(tmp_path, monkeypatch, theme)

    assert _arg(recorder.command, "--config") == str(THEMES / "parent" / "tailwind.config.js")
    wrapper = project_dir / ".bartleby" / "input.css"
    assert _arg(recorder.command, "--input") == str(wrapper)
    assert f'@import "{THEMES / "parent" / "tailwind.css"}";' in wrapper.read_text(
        encoding="utf-8"
    )
    assert "input" not in recorder.kwargs


def test_compile_prefers_leaf_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The leaf layer's tailwind.css and config win over the parent's."""
    leaf = tmp_path / "leaf"
    leaf.mkdir()
    (leaf / "theme.yml").write_text(
        f"name: leaf\nextends: {THEMES / 'parent'}\n", encoding="utf-8"
    )
    (leaf / "tailwind.css").write_text("@tailwind utilities;", encoding="utf-8")
    (leaf / "tailwind.config.js").write_text("module.exports = {};", encoding="utf-8")
    layers = [
        ThemeLayer(name="leaf", root=leaf, manifest=load_manifest(leaf)),
        *resolve_theme(project_dir=tmp_path, path=str(THEMES / "parent")).chain,
    ]

    project_dir, recorder = _compile(tmp_path, monkeypatch, ResolvedTheme(chain=layers))

    assert _arg(recorder.command, "--config") == str(leaf / "tailwind.config.js")
    wrapper = project_dir / ".bartleby" / "input.css"
    assert _arg(recorder.command, "--input") == str(wrapper)
    assert f'@import "{leaf / "tailwind.css"}";' in wrapper.read_text(encoding="utf-8")
    assert str(THEMES / "parent" / "tailwind.css") not in wrapper.read_text(encoding="utf-8")


def test_compile_wrapper_imports_tokens_then_theme_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A theme shipping tailwind.css is wrapped so tokens.css is imported before it."""
    theme = resolve_theme(project_dir=tmp_path, path=str(THEMES / "parent"))

    project_dir, recorder = _compile(tmp_path, monkeypatch, theme, {"color.primary": "#123456"})

    wrapper = project_dir / ".bartleby" / "input.css"
    assert _arg(recorder.command, "--input") != str(THEMES / "parent" / "tailwind.css")
    assert wrapper.read_text(encoding="utf-8") == (
        f'@import "tokens.css";\n@import "{THEMES / "parent" / "tailwind.css"}";\n'
    )
    assert wrapper.parent == (project_dir / ".bartleby" / "tokens.css").parent


def test_css_import_line_uses_forward_slashes_for_windows_paths() -> None:
    """A Windows path becomes a forward-slash import so CSS never reads \\b as an escape."""
    line = css_import_line(PureWindowsPath("C:\\Users\\me\\.bartleby\\theme\\tailwind.css"))

    assert line == '@import "C:/Users/me/.bartleby/theme/tailwind.css";\n'
    assert "\\" not in line


def test_css_import_line_rejects_double_quote_in_path() -> None:
    """A double quote would end the CSS string early, so the path is refused by name."""
    with pytest.raises(ThemeCompileError, match='we"ird'):
        css_import_line(Path('/themes/we"ird/tailwind.css'))


def test_compile_content_covers_every_layer_and_project_dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--content lists each layer's templates glob plus the project override dirs."""
    theme = resolve_theme(project_dir=tmp_path, path=str(THEMES / "child"))
    project_dir = tmp_path / "project"
    (project_dir / "overrides").mkdir(parents=True)

    _, recorder = _compile(tmp_path, monkeypatch, theme)

    globs = _arg(recorder.command, "--content").split(",")
    assert str(THEMES / "child" / "templates" / "**" / "*.html") in globs
    assert str(THEMES / "parent" / "templates" / "**" / "*.html") in globs
    assert str(project_dir / "overrides" / "**" / "*.html") in globs


def test_compile_writes_tokens_css_and_input_imports_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """theme.tokens become --bb-* properties in .bartleby/tokens.css."""
    theme = ResolvedTheme(chain=[])

    project_dir, recorder = _compile(
        tmp_path, monkeypatch, theme, {"color.primary": "#123456", "font.body": "serif"}
    )

    tokens_css = (project_dir / ".bartleby" / "tokens.css").read_text(encoding="utf-8")
    assert "--bb-color-primary: #123456;" in tokens_css
    assert "--bb-font-body: serif;" in tokens_css
    assert tokens_css.lstrip().startswith(":root")
    generated = Path(_arg(recorder.command, "--input"))
    assert generated.read_text(encoding="utf-8").startswith('@import "tokens.css";')
    assert generated.parent == project_dir / ".bartleby"


def test_compile_empty_tokens_still_writes_tokens_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty tokens map leaves an empty-but-present tokens.css."""
    project_dir, _ = _compile(tmp_path, monkeypatch, ResolvedTheme(chain=[]))

    tokens_path = project_dir / ".bartleby" / "tokens.css"
    assert tokens_path.is_file()
    assert tokens_path.read_text(encoding="utf-8") == ""


def test_compile_fallback_input_has_directives_and_no_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no tailwind.css in any layer, a generated input is used and --config is omitted."""
    project_dir, recorder = _compile(
        tmp_path, monkeypatch, resolve_theme(project_dir=tmp_path, name="base")
    )

    generated = project_dir / ".bartleby" / "input.css"
    assert _arg(recorder.command, "--input") == str(generated)
    assert "--config" not in recorder.command
    assert generated.read_text(encoding="utf-8") == (
        '@import "tokens.css";\n@tailwind base;\n@tailwind components;\n@tailwind utilities;\n'
    )
    assert recorder.kwargs.get("input") is None


def test_active_theme_css_stale_when_project_local_theme_template_is_newer(
    tmp_path: Path,
) -> None:
    """Editing a template in a project-local theme layer invalidates the compiled CSS."""
    project_dir = tmp_path / "project"
    theme_dir = project_dir / "mytheme"
    (theme_dir / "templates").mkdir(parents=True)
    (theme_dir / "theme.yml").write_text("name: mytheme\n", encoding="utf-8")
    theme = resolve_theme(project_dir=project_dir, path="mytheme")
    template = theme_dir / "templates" / "page.html"
    template.write_text("<p></p>", encoding="utf-8")
    compiled = project_dir / ".bartleby" / "theme.css"
    compiled.parent.mkdir(parents=True)
    compiled.write_text("/* compiled */", encoding="utf-8")
    assert active_theme_css(project_dir, theme) == compiled

    later = compiled.stat().st_mtime + 100
    os.utime(template, (later, later))

    assert active_theme_css(project_dir, theme) is None


def test_active_theme_css_ignores_layers_outside_the_project(tmp_path: Path) -> None:
    """A bundled or package layer outside the project does not trigger staleness."""
    project_dir = tmp_path / "project"
    project_dir.mkdir(exist_ok=True)
    theme = resolve_theme(project_dir=project_dir, path=str(THEMES / "parent"))
    compiled = project_dir / ".bartleby" / "theme.css"
    compiled.parent.mkdir()
    compiled.write_text("/* compiled */", encoding="utf-8")
    old = compiled.stat().st_mtime - 1000
    os.utime(compiled, (old, old))

    assert active_theme_css(project_dir, theme) == compiled


def test_compile_with_real_tailwind_binary(tmp_path: Path) -> None:
    """Compile a fixture theme with a real Tailwind binary (skipped when none is available)."""
    on_path = shutil.which("tailwindcss")
    cached = default_cache_dir() / f"tailwindcss-{PINNED_TAILWIND_VERSION}"
    if on_path is None and not cached.exists():
        pytest.skip("no tailwindcss on PATH or in the bartleby cache")
    project_dir = tmp_path / "project"
    (project_dir / "templates").mkdir(parents=True)
    (project_dir / "templates" / "page.html").write_text(
        '<div class="p-4 text-red-500"></div>', encoding="utf-8"
    )
    theme = resolve_theme(project_dir=project_dir, path=str(THEMES / "parent"))

    result = compile_theme_css(project_dir, theme, {"color.primary": "#123456"})

    css = (project_dir / result.css_path).read_text(encoding="utf-8")
    assert ".p-4" in css
    # The theme's own tailwind.css uses var(--bb-color-primary); the wrapper must
    # have resolved both the tokens import and the theme file import.
    assert "--bb-color-primary" in css
    assert "#123456" in css
    assert "var(--bb-color-primary)" in css
    assert (project_dir / ".bartleby" / "tokens.css").is_file()
