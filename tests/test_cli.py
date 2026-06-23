# ABOUTME: Tests for CLI command parsing and execution.
# Covers new site, new post, build, validate, serve placeholder.

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from bartleby.cli import main
from bartleby.config import load_config

if TYPE_CHECKING:
    from pathlib import Path


def _last_json(stdout: str) -> dict[str, object]:
    """Parse the last non-empty stdout line as JSON.

    Scaffolding helpers print their own result line before the command under
    test runs, so the JSON we care about is the final line.
    """
    line = [ln for ln in stdout.splitlines() if ln.strip()][-1]
    parsed: dict[str, object] = json.loads(line)
    return parsed


def test_new_site_creates_structure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``bartleby new site mysite`` creates the standard project skeleton."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    site = tmp_path / "mysite"
    assert (site / "bartleby.yml").exists()
    assert (site / ".authors.yml").exists()
    assert (site / "content" / "index.md").exists()
    assert (site / "templates").is_dir()
    assert (site / "static").is_dir()
    assert (site / "hooks").is_dir()


def test_new_site_valid_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The scaffolded bartleby.yml loads cleanly through the config system."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    config = load_config(tmp_path / "mysite" / "bartleby.yml")
    assert config.site.title


def test_new_site_blog_opted_into_tags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The scaffolded blog content type opts into the tags taxonomy.

    Without this, a fresh user writing ``tags:`` in a post's front matter
    sees no /tags/ pages generated and has no obvious way to discover why.
    """
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    config = load_config(tmp_path / "mysite" / "bartleby.yml")
    assert "tags" in config.content_types["blog"].taxonomies


def test_new_site_directory_exists_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Re-scaffolding into an existing site directory errors out."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mysite").mkdir()
    with pytest.raises(SystemExit):
        main(["new", "site", "mysite"])


def test_new_post_creates_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``bartleby new post 'Title' --type blog`` writes a slugified .md file."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")
    main(["new", "post", "My Cool Post", "--type", "blog"])
    target = tmp_path / "mysite" / "content" / "blog" / "posts" / "my-cool-post.md"
    assert target.exists()


def test_new_post_front_matter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A new post has title and date front matter at minimum."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")
    main(["new", "post", "Hello World", "--type", "blog"])
    body = (tmp_path / "mysite" / "content" / "blog" / "posts" / "hello-world.md").read_text()
    assert "title:" in body
    assert "date:" in body


def test_build_command_invokes_pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``bartleby build`` runs the full build and produces ``site/``."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")
    main(["build"])
    assert (tmp_path / "mysite" / "site" / "index.html").exists()


def test_validate_command_zero_exit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``bartleby validate`` exits 0 on a clean config."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")
    main(["validate"])


def test_parse_args_help_exits_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """``bartleby --help`` exits with SystemExit code 0."""
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_theme_compile_command_emits_json_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby theme compile --output json`` emits the documented shape."""
    from bartleby.theme_compile import ThemeCompileResult

    _scaffold_and_enter(tmp_path, monkeypatch)

    def fake_compile(*args: object, **kwargs: object) -> ThemeCompileResult:
        return ThemeCompileResult(
            css_path=".bartleby/theme.css",
            binary="cached",
            duration_ms=410,
            classes_scanned=1842,
        )

    monkeypatch.setattr("bartleby.cli.compile_theme_css", fake_compile)
    main(["theme", "compile", "--output", "json"])

    payload = _last_json(capsys.readouterr().out)
    assert payload == {
        "status": "success",
        "css_path": ".bartleby/theme.css",
        "binary": "cached",
        "duration_ms": 410,
        "classes_scanned": 1842,
    }


def test_theme_compile_clean_error_when_binary_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A binary-resolution failure prints a clean coded error and exits 1."""
    from bartleby.theme_compile import ThemeCompileError

    _scaffold_and_enter(tmp_path, monkeypatch)

    def boom(*args: object, **kwargs: object) -> object:
        raise ThemeCompileError("checksum mismatch")

    monkeypatch.setattr("bartleby.cli.compile_theme_css", boom)

    with pytest.raises(SystemExit) as exc:
        main(["theme", "compile"])
    assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
    assert "theme_compile_error" in captured.err
    assert "checksum mismatch" in captured.err


def test_serve_command_constructs_devserver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``bartleby serve`` instantiates a DevServer with config-derived host/port."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")

    captured: dict[str, object] = {}

    class FakeDevServer:
        def __init__(self, *args: object, **kwargs: object) -> None:
            captured["args"] = args
            captured["kwargs"] = kwargs

        def run(self) -> None:
            captured["ran"] = True

    monkeypatch.setattr("bartleby.server.DevServer", FakeDevServer)
    main(["serve"])
    assert captured["ran"] is True


def _scaffold_and_enter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Create a fresh site and chdir into it so build/validate can run."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")


def test_build_error_prints_clean_message_and_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A build failure prints a clean stderr message with file path and a stable
    error code, exits 1, and never leaks a raw Python traceback."""
    from bartleby.build import BuildError, PageError

    _scaffold_and_enter(tmp_path, monkeypatch)

    def boom(*args: object, **kwargs: object) -> object:
        raise BuildError([PageError(file_path="content/blog/posts/bad.md", message="boom")])

    monkeypatch.setattr("bartleby.cli.async_build", boom)

    with pytest.raises(SystemExit) as exc:
        main(["build"])
    assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
    assert "Traceback" not in captured.out
    # The clean message carries the offending file path and the cause.
    assert "content/blog/posts/bad.md" in captured.err
    assert "boom" in captured.err
    # A stable, machine-recognizable error code is present.
    assert "build_error" in captured.err


def test_build_error_traceback_reenabled_by_debug_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``BARTLEBY_DEBUG=1`` re-enables the raw traceback for development."""
    from bartleby.build import BuildError, PageError

    _scaffold_and_enter(tmp_path, monkeypatch)
    monkeypatch.setenv("BARTLEBY_DEBUG", "1")

    def boom(*args: object, **kwargs: object) -> object:
        raise BuildError([PageError(file_path="content/blog/posts/bad.md", message="boom")])

    monkeypatch.setattr("bartleby.cli.async_build", boom)

    # With debug on, the boundary re-raises so Python prints the full traceback.
    with pytest.raises(BuildError):
        main(["build"])


def test_config_error_prints_clean_message_and_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A config failure during build surfaces cleanly with its stable code."""
    from bartleby.config import ConfigError

    _scaffold_and_enter(tmp_path, monkeypatch)

    def boom(*args: object, **kwargs: object) -> object:
        raise ConfigError("site section is required", key_path="site")

    monkeypatch.setattr("bartleby.cli.async_build", boom)

    with pytest.raises(SystemExit) as exc:
        main(["build"])
    assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
    assert "config_error" in captured.err
    assert "site section is required" in captured.err


def test_build_output_json_is_valid_and_parseable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby build --output json`` emits a single parseable JSON object on stdout."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    main(["build", "--output", "json"])
    captured = capsys.readouterr()
    payload = _last_json(captured.out)
    assert payload["status"] == "success"
    assert payload["pages"] >= 1
    assert payload["output_dir"]
    assert isinstance(payload["errors"], list)
    assert isinstance(payload["warnings"], list)


def test_validate_output_json_is_valid_and_parseable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby validate --output json`` emits a parseable JSON object on stdout."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    main(["validate", "--output", "json"])
    captured = capsys.readouterr()
    payload = _last_json(captured.out)
    assert payload["valid"] is True
    assert payload["files_checked"] >= 1


def test_build_error_json_mode_emits_error_object(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """In JSON mode a build failure is a parseable error object on stdout, exit 1."""
    from bartleby.build import BuildError, PageError

    _scaffold_and_enter(tmp_path, monkeypatch)

    def boom(*args: object, **kwargs: object) -> object:
        raise BuildError([PageError(file_path="content/blog/posts/bad.md", message="boom")])

    monkeypatch.setattr("bartleby.cli.async_build", boom)

    with pytest.raises(SystemExit) as exc:
        main(["build", "--output", "json"])
    assert exc.value.code == 1

    captured = capsys.readouterr()
    payload = _last_json(captured.out)
    assert payload["error"]
    assert payload["code"] == "build_error"
    assert payload["file"] == "content/blog/posts/bad.md"


def test_new_site_output_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby new site --output json`` emits the documented path/config object."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite", "--output", "json"])
    captured = capsys.readouterr()
    payload = _last_json(captured.out)
    assert payload["path"]
    assert payload["config"]


def test_new_post_missing_type_json_is_usage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unknown content type in JSON mode is a usage error (exit 2), never a prompt."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")

    with pytest.raises(SystemExit) as exc:
        main(["new", "post", "Hi", "--type", "nope", "--output", "json"])
    assert exc.value.code == 2

    captured = capsys.readouterr()
    payload = _last_json(captured.out)
    assert payload["code"] == "usage_error"


def test_schema_content_type_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby schema blog --output json`` emits the content type's field schema."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")

    main(["schema", "blog", "--output", "json"])
    payload = _last_json(capsys.readouterr().out)
    assert payload["content_type"] == "blog"
    assert "required_fields" in payload
    assert "optional_fields" in payload


def test_schema_authors_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby schema authors --output json`` lists configured authors."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")

    main(["schema", "authors", "--output", "json"])
    payload = _last_json(capsys.readouterr().out)
    listed = payload["authors"]
    assert isinstance(listed, list)
    assert any(entry["name"] for entry in listed)


def test_schema_taxonomies_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby schema taxonomies --output json`` lists taxonomies and in-use terms."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")

    main(["schema", "taxonomies", "--output", "json"])
    payload = _last_json(capsys.readouterr().out)
    taxonomies = payload["taxonomies"]
    assert isinstance(taxonomies, list)
    assert any(tax["name"] == "tags" for tax in taxonomies)


def test_schema_unknown_content_type_is_usage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby schema nope`` for an undefined content type fails as a usage error."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")

    with pytest.raises(SystemExit) as exc:
        main(["schema", "nope", "--output", "json"])
    assert exc.value.code == 2
    payload = _last_json(capsys.readouterr().out)
    assert payload["code"] == "usage_error"


def _write_published_post(project_dir: Path) -> None:
    """Write a non-draft blog post into the scaffolded site for content-query tests."""
    post = project_dir / "content" / "blog" / "posts" / "hello-world.md"
    post.write_text(
        '---\ntitle: "Hello World"\ndate: 2026-05-01\ndraft: false\n---\n\nA short body.\n',
        encoding="utf-8",
    )


def test_content_list_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby content list --output json`` lists published pages with curated fields."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    _write_published_post(tmp_path / "mysite")
    monkeypatch.chdir(tmp_path / "mysite")

    main(["content", "list", "--output", "json"])
    payload = _last_json(capsys.readouterr().out)
    assert payload["count"] >= 1
    titles = {entry["title"] for entry in payload["content"]}
    assert "Hello World" in titles


def test_content_list_excludes_drafts_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby content list`` omits draft posts by default."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")
    main(["new", "post", "Secret Draft", "--type", "blog"])

    main(["content", "list", "--output", "json"])
    payload = _last_json(capsys.readouterr().out)
    titles = {entry["title"] for entry in payload["content"]}
    assert "Secret Draft" not in titles


def test_content_get_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby content get <path> --output json`` returns one page's metadata and body."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    _write_published_post(tmp_path / "mysite")
    monkeypatch.chdir(tmp_path / "mysite")

    main(["content", "get", "content/blog/posts/hello-world.md", "--output", "json"])
    payload = _last_json(capsys.readouterr().out)
    assert payload["content_type"] == "blog"
    assert payload["metadata"]["title"] == "Hello World"
    assert "word_count" in payload


def test_content_get_unknown_path_is_usage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby content get`` for a missing page fails as a usage error."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")

    with pytest.raises(SystemExit) as exc:
        main(["content", "get", "content/blog/posts/nope.md", "--output", "json"])
    assert exc.value.code == 2
    payload = _last_json(capsys.readouterr().out)
    assert payload["code"] == "usage_error"


def test_render_command_html_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby render <path> --output json`` renders one page to HTML without a build."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    _write_published_post(tmp_path / "mysite")
    monkeypatch.chdir(tmp_path / "mysite")

    main(["render", "content/blog/posts/hello-world.md", "--output", "json"])
    payload = _last_json(capsys.readouterr().out)
    assert payload["path"] == "content/blog/posts/hello-world.md"
    assert payload["url"]
    assert "A short body" in str(payload["html"])
    assert payload["metadata"]["title"] == "Hello World"
    assert payload["word_count"] >= 1
    assert isinstance(payload["warnings"], list)
    assert "site" not in [p.name for p in (tmp_path / "mysite").iterdir()]


def test_render_command_no_full_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``bartleby render`` does not write the ``site/`` output tree."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    _write_published_post(tmp_path / "mysite")
    monkeypatch.chdir(tmp_path / "mysite")

    main(["render", "content/blog/posts/hello-world.md"])
    assert not (tmp_path / "mysite" / "site").exists()


def test_render_command_markdown_format(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--format markdown`` returns processed markdown without HTML conversion."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    _write_published_post(tmp_path / "mysite")
    monkeypatch.chdir(tmp_path / "mysite")

    main(
        [
            "render",
            "content/blog/posts/hello-world.md",
            "--format",
            "markdown",
            "--output",
            "json",
        ]
    )
    payload = _last_json(capsys.readouterr().out)
    assert "A short body" in str(payload["markdown"])
    assert "<p>" not in str(payload["markdown"])


def test_render_unknown_path_is_usage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby render`` for a missing page fails as a usage error."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")

    with pytest.raises(SystemExit) as exc:
        main(["render", "content/blog/posts/nope.md", "--output", "json"])
    assert exc.value.code == 2
    payload = _last_json(capsys.readouterr().out)
    assert payload["code"] == "usage_error"


def test_lint_command_json_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby lint --output json`` emits issues plus a severity summary."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")
    # A post with a broken cross-reference produces an error-level issue.
    post = tmp_path / "mysite" / "content" / "blog" / "posts" / "broken.md"
    post.write_text(
        '---\ntitle: "Broken"\ndate: 2026-05-01\ndraft: false\n---\n\n[gone](missing.md)\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as exc:
        main(["lint", "--output", "json"])
    assert exc.value.code == 1

    payload = _last_json(capsys.readouterr().out)
    assert "issues" in payload
    assert "summary" in payload
    assert payload["summary"]["errors"] >= 1
    rules = {issue["rule"] for issue in payload["issues"]}
    assert "broken-crossref" in rules


def test_lint_check_external_off_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby lint`` does not check external URLs unless --check-external is given."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")
    post = tmp_path / "mysite" / "content" / "blog" / "posts" / "ext.md"
    post.write_text(
        '---\ntitle: "Ext"\ndate: 2026-05-01\ndraft: false\ndescription: "d"\n---\n\n'
        "[x](https://example.invalid/missing)\n",
        encoding="utf-8",
    )

    called: dict[str, bool] = {"checked": False}

    def fake_checker(url: str) -> bool:
        called["checked"] = True
        return False

    monkeypatch.setattr("bartleby.linting.check_external_url", fake_checker)
    main(["lint", "--output", "json"])
    assert called["checked"] is False
