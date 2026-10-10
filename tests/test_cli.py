# ABOUTME: Tests for CLI command parsing and execution.
# Covers new site, new post, build, validate, serve placeholder.

from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING

import pytest

from bartleby.cli import _discover_shortcode_names, main
from bartleby.config import load_config
from bartleby.plugins import KNOWN_EVENTS
from bartleby.theme_loader import ResolvedTheme, ThemeLayer, ThemeManifest

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


def test_validate_flags_missing_template_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``validate`` reports a page whose ``template:`` override does not exist (Design 17)."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    page = tmp_path / "mysite" / "content" / "index.md"
    page.write_text(
        "---\ntitle: Home\ntemplate: nonexistent.html\n---\nWelcome.\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as exc:
        main(["validate", "--output", "json"])
    assert exc.value.code == 1

    payload = _last_json(capsys.readouterr().out)
    assert payload["valid"] is False
    errors = payload["errors"]
    assert isinstance(errors, list)
    assert any("nonexistent.html" in str(error["message"]) for error in errors)


def test_validate_flags_broken_crossref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``validate`` reports a markdown link to a non-existent page (Design 17)."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    page = tmp_path / "mysite" / "content" / "index.md"
    page.write_text(
        "---\ntitle: Home\n---\nSee [the void](does-not-exist.md).\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as exc:
        main(["validate", "--output", "json"])
    assert exc.value.code == 1

    payload = _last_json(capsys.readouterr().out)
    assert payload["valid"] is False
    errors = payload["errors"]
    assert isinstance(errors, list)
    assert any("does-not-exist.md" in str(error["message"]) for error in errors)


def test_validate_clean_site_still_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A freshly scaffolded site with no broken refs validates clean (Design 17 regression)."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    main(["validate", "--output", "json"])
    payload = _last_json(capsys.readouterr().out)
    assert payload["valid"] is True


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


def test_schema_taxonomies_json_omits_draft_only_terms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby schema taxonomies`` never lists a term contributed only by a draft."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    project = tmp_path / "mysite"
    monkeypatch.chdir(project)

    published = project / "content" / "blog" / "posts" / "published.md"
    published.write_text(
        '---\ntitle: "Published"\ndate: 2026-05-01\ndraft: false\ntags: [python]\n---\n\nBody.\n',
        encoding="utf-8",
    )
    draft = project / "content" / "blog" / "posts" / "draft.md"
    draft.write_text(
        '---\ntitle: "Draft"\ndate: 2026-05-02\ndraft: true\ntags: [python, draft-only]\n---\n\n'
        "Body.\n",
        encoding="utf-8",
    )

    main(["schema", "taxonomies", "--output", "json"])
    payload = _last_json(capsys.readouterr().out)
    taxonomies = payload["taxonomies"]
    tags = next(tax for tax in taxonomies if tax["name"] == "tags")
    terms = {term["term"]: term["count"] for term in tags["terms"]}
    assert "draft-only" not in terms
    assert terms["python"] == 1


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
    # A post that links to a real page, so the fixture also exercises the
    # orphan check: linked.md must not be reported orphaned.
    linked = tmp_path / "mysite" / "content" / "blog" / "posts" / "linked.md"
    linked.write_text(
        '---\ntitle: "Linked"\ndate: 2026-05-01\ndraft: false\ndescription: "d"\n---\n\nBody.\n',
        encoding="utf-8",
    )
    # A post with a broken cross-reference produces an error-level issue.
    post = tmp_path / "mysite" / "content" / "blog" / "posts" / "broken.md"
    post.write_text(
        '---\ntitle: "Broken"\ndate: 2026-05-01\ndraft: false\n---\n\n'
        "[gone](missing.md) and [linked](linked.md)\n",
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
    orphans = {issue["file"] for issue in payload["issues"] if issue["rule"] == "orphaned-page"}
    assert "blog/posts/linked.md" not in orphans


def test_lint_relative_md_link_resolves_before_orphan_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A page linked via a relative ``.md`` path is never reported orphaned.

    Regression guard for the missing crossref-resolution pre-pass in
    ``_cmd_lint``: without it, ``.md`` hrefs never get rewritten to output
    URLs, so ``_lint_orphans`` never matches an inbound link and reports
    every page orphaned.
    """
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    site = tmp_path / "mysite"
    (site / "content" / "blog" / "posts" / "linked.md").write_text(
        '---\ntitle: "Linked"\ndate: 2026-05-01\ndraft: false\ndescription: "d"\n---\n\nBody.\n',
        encoding="utf-8",
    )
    (site / "content" / "blog" / "posts" / "hub.md").write_text(
        '---\ntitle: "Hub"\ndate: 2026-05-01\ndraft: false\ndescription: "d"\n---\n\n'
        "[go](linked.md)\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(site)

    main(["lint", "--output", "json"])
    payload = _last_json(capsys.readouterr().out)
    orphans = {issue["file"] for issue in payload["issues"] if issue["rule"] == "orphaned-page"}
    assert "blog/posts/linked.md" not in orphans


def test_lint_nav_page_never_reported_orphaned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A page present in navigation is never reported orphaned, inbound links or not."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    site = tmp_path / "mysite"
    (site / "content" / "blog" / "posts" / "lonely.md").write_text(
        '---\ntitle: "Lonely"\ndate: 2026-05-01\ndraft: false\ndescription: "d"\n---\n\nBody.\n',
        encoding="utf-8",
    )
    config_path = site / "bartleby.yml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + '\nnav:\n  - "Lonely": blog/posts/lonely.md\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(site)

    main(["lint", "--output", "json"])
    payload = _last_json(capsys.readouterr().out)
    orphans = {issue["file"] for issue in payload["issues"] if issue["rule"] == "orphaned-page"}
    assert "blog/posts/lonely.md" not in orphans


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


def test_build_dry_run_reports_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby build --dry-run --output json`` reports changes and never writes site/."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    main(["build", "--dry-run", "--output", "json"])
    captured = capsys.readouterr()
    payload = _last_json(captured.out)
    assert payload["status"] == "dry_run"
    assert isinstance(payload["added"], list)
    assert payload["added"]  # a fresh site reports everything as added
    assert not (tmp_path / "mysite" / "site").exists()


def test_export_jsonl_emits_one_object_per_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby export`` defaults to JSONL with one published page per line."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")
    post = tmp_path / "mysite" / "content" / "blog" / "posts" / "p.md"
    post.write_text(
        '---\ntitle: "P"\ndate: 2026-05-01\ndraft: false\ndescription: "d"\n---\n\nBody.\n',
        encoding="utf-8",
    )
    capsys.readouterr()  # drop scaffolding output
    main(["export"])
    captured = capsys.readouterr()
    lines = [line for line in captured.out.splitlines() if line.strip()]
    records = [json.loads(line) for line in lines]
    titles = {record["title"] for record in records}
    assert "P" in titles


def test_export_include_content_embeds_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby export --include-content`` embeds the markdown body."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")
    post = tmp_path / "mysite" / "content" / "blog" / "posts" / "p.md"
    post.write_text(
        '---\ntitle: "P"\ndate: 2026-05-01\ndraft: false\ndescription: "d"\n---\n\n'
        "Unique body text.\n",
        encoding="utf-8",
    )
    capsys.readouterr()
    main(["export", "--include-content"])
    captured = capsys.readouterr()
    assert "Unique body text." in captured.out


def test_export_include_html_returns_the_built_page_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby export --include-html`` embeds the HTML the build puts in the page."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    site = tmp_path / "mysite"
    monkeypatch.chdir(site)
    post = site / "content" / "blog" / "posts" / "p.md"
    post.write_text(
        '---\ntitle: "P"\ndate: 2026-05-01\ndraft: false\ndescription: "d"\n---\n\n'
        "## Heading\n\nUnique *body* text.\n",
        encoding="utf-8",
    )
    draft = site / "content" / "blog" / "posts" / "d.md"
    draft.write_text('---\ntitle: "D"\ndate: 2026-05-02\ndraft: true\n---\n\nHidden.\n')
    capsys.readouterr()

    main(["export", "--include-html"])
    records = [
        json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")
    ]
    exported = next(record for record in records if record["title"] == "P")
    assert "<em>body</em>" in str(exported["html"])
    assert all(record["title"] != "D" for record in records)
    assert all(record["html"] for record in records)

    # The export and the build share one render path: the built page holds the same HTML.
    main(["build"])
    page_dir = site / "site" / str(exported["url"]).strip("/")
    built = (page_dir / "index.html").read_text(encoding="utf-8")
    assert str(exported["html"]) in built
    assert not [path for path in site.iterdir() if path.name.startswith(".bartleby-build-")]


def _site_with_event_recorder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Scaffold a site whose project hook appends every event it receives to fired.log."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    site = tmp_path / "mysite"
    monkeypatch.chdir(site)
    hooks_dir = site / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    handlers = "".join(
        f"def {event}(*args, **kwargs):\n    record({event!r}, args)\n\n\n"
        for event in sorted(KNOWN_EVENTS)
    )
    (hooks_dir / "recorder.py").write_text(
        "# ABOUTME: Test hook that records every event it receives.\n"
        "# Appends one line per event to fired.log in the project root.\n"
        "from pathlib import Path\n\n"
        "LOG = Path(__file__).parent.parent / 'fired.log'\n\n\n"
        "def record(event, args):\n"
        "    argument = args[0] if event == 'on_startup' else ''\n"
        "    with LOG.open('a', encoding='utf-8') as handle:\n"
        "        handle.write(f'{event} {argument}'.strip() + '\\n')\n\n\n" + handlers,
        encoding="utf-8",
    )
    return site


def test_export_include_html_fires_the_documented_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``export --include-html`` fires the load, body-render, and shutdown hooks only.

    ``on_shutdown`` fires exactly once, last, as it does at the end of a build.
    ``docs/content/reference/pages/plugin-hooks.md`` lists these events. Change the set
    here and in that page together.
    """
    site = _site_with_event_recorder(tmp_path, monkeypatch)
    capsys.readouterr()

    main(["export", "--include-html"])

    fired = (site / "fired.log").read_text(encoding="utf-8").splitlines()
    assert fired[0] == "on_startup export"
    assert fired[-1] == "on_shutdown"
    assert fired.count("on_shutdown") == 1
    assert {line.split()[0] for line in fired} == {
        "on_startup",
        "on_config",
        "on_pre_build",
        "on_files",
        "on_nav",
        "on_env",
        "on_pre_page",
        "on_page_read_source",
        "on_page_markdown",
        "on_page_content",
        "on_shutdown",
    }


def test_export_include_html_failure_fires_build_error_then_shutdown_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A page that fails to render fires ``on_build_error`` then ``on_shutdown``, once each."""
    site = _site_with_event_recorder(tmp_path, monkeypatch)
    first_page = next((site / "content").rglob("*.md"))
    first_page.write_text(
        first_page.read_text(encoding="utf-8") + "\n[% totally_unknown_shortcode %]\n",
        encoding="utf-8",
    )
    capsys.readouterr()

    with pytest.raises(SystemExit):
        main(["export", "--include-html"])

    fired = (site / "fired.log").read_text(encoding="utf-8").splitlines()
    assert fired[-2:] == ["on_build_error", "on_shutdown"]
    assert fired.count("on_build_error") == 1
    assert fired.count("on_shutdown") == 1


def test_export_include_html_metadata_failure_fires_build_error_then_shutdown_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Invalid metadata fires ``on_build_error`` then ``on_shutdown``, once each."""
    site = _site_with_event_recorder(tmp_path, monkeypatch)
    welcome = site / "content" / "blog" / "posts" / "welcome.md"
    welcome.write_text(
        welcome.read_text(encoding="utf-8").replace(
            "authors: [default]", "authors: [nobody-such-author]"
        ),
        encoding="utf-8",
    )
    capsys.readouterr()

    with pytest.raises(SystemExit):
        main(["export", "--include-html"])

    fired = (site / "fired.log").read_text(encoding="utf-8").splitlines()
    assert fired[-2:] == ["on_build_error", "on_shutdown"]
    assert fired.count("on_build_error") == 1
    assert fired.count("on_shutdown") == 1


def test_export_include_html_missing_content_dir_fires_build_error_then_shutdown_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing ``content/`` fires ``on_build_error`` then ``on_shutdown``, once each."""
    site = _site_with_event_recorder(tmp_path, monkeypatch)
    shutil.rmtree(site / "content")
    capsys.readouterr()

    with pytest.raises(SystemExit):
        main(["export", "--include-html"])

    fired = (site / "fired.log").read_text(encoding="utf-8").splitlines()
    assert fired[-2:] == ["on_build_error", "on_shutdown"]
    assert fired.count("on_build_error") == 1
    assert fired.count("on_shutdown") == 1


def test_export_without_include_html_does_not_render(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Plain ``bartleby export`` carries no ``html`` key."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    monkeypatch.chdir(tmp_path / "mysite")
    capsys.readouterr()
    main(["export"])
    records = [
        json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")
    ]
    assert records
    assert all("html" not in record for record in records)


def test_generate_skill_writes_three_skills(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``bartleby generate-skill`` writes the three skills under the configured output dir."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    site = tmp_path / "mysite"
    (site / "shortcodes").mkdir()
    (site / "shortcodes" / "callout.html").write_text("{{ text }}\n", encoding="utf-8")
    monkeypatch.chdir(site)
    capsys.readouterr()
    main(["generate-skill", "--output", "json"])
    captured = capsys.readouterr()
    payload = _last_json(captured.out)
    generated = payload["skills_generated"]
    assert isinstance(generated, list)
    assert len(generated) == 3
    skills_dir = tmp_path / "mysite" / ".claude" / "skills"
    assert (skills_dir / "bartleby-write.md").exists()
    assert (skills_dir / "bartleby-review.md").exists()
    assert (skills_dir / "bartleby-ops.md").exists()
    write_content = (skills_dir / "bartleby-write.md").read_text(encoding="utf-8")
    assert "callout" in write_content


def _write_malformed_front_matter(project_dir: Path) -> Path:
    """Write a content file whose front matter parses to a list, not a mapping."""
    bad_path = project_dir / "content" / "blog" / "posts" / "bad.md"
    bad_path.write_text(
        "---\n- not\n- a\n- mapping\n---\n\nBody text.\n",
        encoding="utf-8",
    )
    return bad_path


def test_content_error_prints_clean_message_and_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Malformed front matter on a content-discovering command (lint) exits 1
    with a clean stderr message and no raw Python traceback."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    _write_malformed_front_matter(tmp_path / "mysite")

    with pytest.raises(SystemExit) as exc:
        main(["lint"])
    assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
    assert "Traceback" not in captured.out
    assert "content_error" in captured.err
    assert "bad.md" in captured.err


def test_content_error_json_mode_emits_error_object(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """In JSON mode, malformed front matter is a parseable error object on stdout."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    _write_malformed_front_matter(tmp_path / "mysite")

    with pytest.raises(SystemExit) as exc:
        main(["lint", "--output", "json"])
    assert exc.value.code == 1

    captured = capsys.readouterr()
    payload = _last_json(captured.out)
    assert payload["error"]
    assert payload["code"] == "content_error"
    assert "bad.md" in str(payload["file"])


def test_content_error_traceback_reenabled_by_debug_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``BARTLEBY_DEBUG=1`` re-enables the raw traceback for malformed front matter."""
    from bartleby.content import ContentError

    _scaffold_and_enter(tmp_path, monkeypatch)
    _write_malformed_front_matter(tmp_path / "mysite")
    monkeypatch.setenv("BARTLEBY_DEBUG", "1")

    with pytest.raises(ContentError):
        main(["lint"])


def test_discover_shortcode_names_finds_project_root_location(tmp_path: Path) -> None:
    """A shortcode at ``<project>/shortcodes/foo.html`` is discovered."""
    (tmp_path / "shortcodes").mkdir()
    (tmp_path / "shortcodes" / "foo.html").write_text("foo\n", encoding="utf-8")

    assert _discover_shortcode_names(tmp_path) == ["foo"]


def test_discover_shortcode_names_finds_templates_shortcodes_location(tmp_path: Path) -> None:
    """A shortcode at ``<project>/templates/shortcodes/bar.html`` is still discovered."""
    (tmp_path / "templates" / "shortcodes").mkdir(parents=True)
    (tmp_path / "templates" / "shortcodes" / "bar.html").write_text("bar\n", encoding="utf-8")

    assert _discover_shortcode_names(tmp_path) == ["bar"]


def _single_layer_theme(root: Path) -> ResolvedTheme:
    manifest = ThemeManifest(name="stub")
    return ResolvedTheme(chain=[ThemeLayer(name="stub", root=root, manifest=manifest)])


def test_discover_shortcode_names_includes_builtin_theme_shortcodes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Built-in theme shortcodes (``<theme>/templates/shortcodes/*.html``) are included."""
    theme_dir = tmp_path / "theme"
    (theme_dir / "templates" / "shortcodes").mkdir(parents=True)
    (theme_dir / "templates" / "shortcodes" / "baked_in.html").write_text(
        "baked in\n", encoding="utf-8"
    )
    monkeypatch.setattr("bartleby.templates.default_theme", lambda: _single_layer_theme(theme_dir))

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    assert _discover_shortcode_names(project_dir) == ["baked_in"]


def test_discover_shortcode_names_finds_overrides_shortcodes_location(
    tmp_path: Path,
) -> None:
    """A shortcode at ``<project>/overrides/shortcodes/onlyoverride.html`` is discovered.

    Regression test for R13: a shortcode placed only under ``overrides/shortcodes``
    renders fine through the Jinja loader, so discovery must cover it too.
    """
    (tmp_path / "overrides" / "shortcodes").mkdir(parents=True)
    (tmp_path / "overrides" / "shortcodes" / "onlyoverride.html").write_text(
        "only in overrides\n", encoding="utf-8"
    )

    assert _discover_shortcode_names(tmp_path) == ["onlyoverride"]


def test_generate_skill_includes_overrides_only_shortcode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A shortcode defined only under ``overrides/shortcodes`` reaches the generated skill."""
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "mysite"])
    site = tmp_path / "mysite"
    (site / "overrides" / "shortcodes").mkdir(parents=True)
    (site / "overrides" / "shortcodes" / "onlyoverride.html").write_text(
        "{{ text }}\n", encoding="utf-8"
    )
    monkeypatch.chdir(site)
    capsys.readouterr()
    main(["generate-skill", "--output", "json"])
    capsys.readouterr()
    skills_dir = tmp_path / "mysite" / ".claude" / "skills"
    write_content = (skills_dir / "bartleby-write.md").read_text(encoding="utf-8")
    assert "onlyoverride" in write_content


def test_discover_shortcode_names_deduplicates_across_locations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A name defined in multiple locations appears once, sorted."""
    theme_dir = tmp_path / "theme"
    (theme_dir / "templates" / "shortcodes").mkdir(parents=True)
    (theme_dir / "templates" / "shortcodes" / "note.html").write_text(
        "theme note\n", encoding="utf-8"
    )
    monkeypatch.setattr("bartleby.templates.default_theme", lambda: _single_layer_theme(theme_dir))

    project_dir = tmp_path / "project"
    (project_dir / "shortcodes").mkdir(parents=True)
    (project_dir / "shortcodes" / "note.html").write_text("project note\n", encoding="utf-8")
    (project_dir / "shortcodes" / "warning.html").write_text("warning\n", encoding="utf-8")
    (project_dir / "templates" / "shortcodes").mkdir(parents=True)
    (project_dir / "templates" / "shortcodes" / "note.html").write_text(
        "alt note\n", encoding="utf-8"
    )

    assert _discover_shortcode_names(project_dir) == ["note", "warning"]


def _append_to_config(extra: str) -> None:
    """Append ``extra`` YAML to ``./bartleby.yml`` in the current directory."""
    from pathlib import Path as RuntimePath

    config_path = RuntimePath("bartleby.yml")
    config_path.write_text(config_path.read_text(encoding="utf-8") + extra, encoding="utf-8")


def test_build_with_old_material_feature_name_exits_one_with_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A mkdocs-material feature name fails the build with a message naming the native name."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    _append_to_config("\ntheme:\n  features:\n    - navigation.tabs\n")

    with pytest.raises(SystemExit) as exc:
        main(["build"])
    assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
    assert "config_error" in captured.err
    assert "theme.features" in captured.err
    assert "navigation.tabs" in captured.err
    assert "nav.tabs" in captured.err


def test_build_with_palette_key_exits_one_pointing_to_tokens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The removed ``palette`` key fails the build with a pointer to ``theme.tokens``."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    _append_to_config("\ntheme:\n  palette:\n    primary: indigo\n")

    with pytest.raises(SystemExit) as exc:
        main(["build"])
    assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "config_error" in captured.err
    assert "theme.tokens" in captured.err


def test_build_warns_when_theme_lacks_enabled_feature_and_still_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """An enabled feature the theme lacks prints a warning but the build completes."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    bare_theme = tmp_path / "bare-theme"
    bare_theme.mkdir()
    (bare_theme / "theme.yml").write_text(
        "name: bare\nextends: base\nfeatures: []\n", encoding="utf-8"
    )
    _append_to_config(f"\ntheme:\n  path: {bare_theme}\n  features:\n    - nav.tabs\n")

    with caplog.at_level("WARNING", logger="bartleby"):
        main(["build"])

    assert (tmp_path / "mysite" / "site" / "index.html").exists()
    messages = [record.getMessage() for record in caplog.records if record.levelname == "WARNING"]
    assert any("nav.tabs" in message and "does not implement" in message for message in messages)


# --- error-message contract through the CLI --------------------------------


def _run_failing_build(capsys: pytest.CaptureFixture[str], *argv: str) -> str:
    """Run the CLI expecting exit 1 and no traceback; return the stderr text."""
    with pytest.raises(SystemExit) as exc:
        main(list(argv))
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
    assert "Traceback" not in captured.out
    return captured.err


def test_build_unknown_top_level_key_surfaces_file_key_and_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A misspelled top-level key exits 1 with the file, the key, and the suggestion."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    _append_to_config("\ncontent_type:\n  docs:\n    path: docs\n")
    err = _run_failing_build(capsys, "build")
    assert "config_error" in err
    assert "bartleby.yml" in err
    assert "content_type" in err
    assert "content_types" in err


def test_build_bad_metadata_schema_type_surfaces_content_type_and_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A metadata field with an unknown type names the content type and field."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    config_path = tmp_path / "mysite" / "bartleby.yml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "    readtime: true\n",
            "    readtime: true\n    metadata:\n      rating:\n        type: number\n",
        ),
        encoding="utf-8",
    )
    err = _run_failing_build(capsys, "build")
    assert "content_types.blog.metadata.rating.type" in err
    assert "string" in err


def test_build_duplicate_author_id_surfaces_file_and_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A duplicated author id exits 1 as author_error naming the authors file and the id."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    (tmp_path / "mysite" / ".authors.yml").write_text(
        "authors:\n  default:\n    name: A\n  default:\n    name: B\n", encoding="utf-8"
    )
    err = _run_failing_build(capsys, "build")
    assert "author_error" in err
    assert ".authors.yml" in err
    assert "default" in err
    assert "duplicate" in err


def test_build_unknown_post_author_surfaces_known_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A post naming an unknown author fails the build listing the known author ids."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    post = tmp_path / "mysite" / "content" / "blog" / "posts" / "hello.md"
    post.write_text("---\ntitle: Hello\nauthors: [nobody]\n---\n\nHi\n", encoding="utf-8")
    err = _run_failing_build(capsys, "build")
    assert "build_error" in err
    assert "hello.md" in err
    assert "nobody" in err
    assert "default" in err


def test_build_theme_path_without_manifest_surfaces_what_a_theme_needs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A theme.path directory with no theme.yml exits 1 as theme_error with the fix."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    (tmp_path / "mysite" / "my-theme").mkdir()
    _append_to_config("\ntheme:\n  path: my-theme\n")
    err = _run_failing_build(capsys, "build")
    assert "theme_error" in err
    assert "my-theme" in err
    assert "theme.yml" in err
    assert "fix:" in err


def test_build_missing_content_directory_surfaces_path_and_fix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A project without content/ exits 1 as build_error naming the directory."""
    import shutil

    _scaffold_and_enter(tmp_path, monkeypatch)
    shutil.rmtree(tmp_path / "mysite" / "content")
    err = _run_failing_build(capsys, "build")
    assert "build_error" in err
    assert str(tmp_path / "mysite" / "content") in err
    assert "fix:" in err


def test_build_page_colliding_with_schema_json_is_a_clean_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A page that would overwrite schema.json exits 1 as agent_surface_error, no traceback."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    page = tmp_path / "mysite" / "content" / "schema.md"
    page.write_text("---\ntitle: Schema\nurl: schema.json\n---\n\nHi\n", encoding="utf-8")
    err = _run_failing_build(capsys, "build")
    assert "agent_surface_error" in err
    assert "schema.md" in err
    assert "schema.json" in err
    assert "fix:" in err


def test_build_page_colliding_with_schema_json_json_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """In JSON mode the collision is one error object with the stable code."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    page = tmp_path / "mysite" / "content" / "schema.md"
    page.write_text("---\ntitle: Schema\nurl: schema.json\n---\n\nHi\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main(["build", "--output", "json"])
    assert exc.value.code == 1
    payload = _last_json(capsys.readouterr().out)
    assert payload["code"] == "agent_surface_error"
    assert "schema.json" in str(payload["error"])


def test_build_unknown_shortcode_surfaces_template_to_create(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unknown shortcode fails the build naming the page and the template to add."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    page = tmp_path / "mysite" / "content" / "blog" / "posts" / "hello.md"
    page.write_text("---\ntitle: Hello\n---\n\n[% banner %]\n", encoding="utf-8")
    err = _run_failing_build(capsys, "build")
    assert "hello.md" in err
    assert "shortcodes/banner.html" in err


def test_missing_config_names_the_path_and_how_to_create_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Running build outside a project is a usage error (exit 2) with the next step."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["build"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "bartleby.yml" in err
    assert "bartleby new site" in err
    assert "--config" in err


# --- global flags: --quiet and --verbose ------------------------------------


def test_quiet_build_prints_no_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--quiet`` suppresses the text summary of a successful build."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    capsys.readouterr()
    main(["build", "--quiet"])
    assert capsys.readouterr().out == ""
    assert (tmp_path / "mysite" / "site" / "index.html").exists()


def test_quiet_does_not_hide_json_or_data_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """JSON output and data-returning commands are the product, so quiet leaves them alone."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    capsys.readouterr()
    main(["build", "--quiet", "--output", "json"])
    assert "pages" in _last_json(capsys.readouterr().out)
    main(["content", "list", "--quiet"])
    assert capsys.readouterr().out.strip() != ""


def test_quiet_still_reports_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--quiet`` never hides a failure."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    _append_to_config("\nbogus_key: 1\n")
    with pytest.raises(SystemExit) as exc:
        main(["build", "--quiet"])
    assert exc.value.code == 1
    assert "bogus_key" in capsys.readouterr().err


def test_quiet_raises_log_threshold_and_verbose_lowers_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--quiet`` keeps only errors from the log; ``--verbose`` adds debug detail."""
    import logging

    monkeypatch.delenv("BARTLEBY_DEBUG", raising=False)
    _scaffold_and_enter(tmp_path, monkeypatch)
    main(["build", "--quiet"])
    assert logging.getLogger("bartleby").level == logging.ERROR
    main(["build", "--verbose"])
    assert logging.getLogger("bartleby").level == logging.DEBUG
    main(["build"])
    assert logging.getLogger("bartleby").level == logging.INFO


def test_verbose_build_logs_progress_detail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """``--verbose`` surfaces per-phase detail that a normal build does not log."""
    monkeypatch.delenv("BARTLEBY_DEBUG", raising=False)
    _scaffold_and_enter(tmp_path, monkeypatch)
    with caplog.at_level("DEBUG", logger="bartleby"):
        main(["build", "--verbose"])
    messages = [record.getMessage() for record in caplog.records if record.levelname == "DEBUG"]
    assert any("discovered" in message for message in messages)
    assert any("wrote" in message for message in messages)


def test_quiet_and_verbose_conflict_is_a_usage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Asking for both is contradictory; argparse reports it and exits 2."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    with pytest.raises(SystemExit) as exc:
        main(["build", "--quiet", "--verbose"])
    assert exc.value.code == 2
    assert "not allowed with" in capsys.readouterr().err


# --- ai.skills.regenerate_on_build -------------------------------------------


def test_build_regenerates_skills_when_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``ai.skills.regenerate_on_build: true`` writes the three skills after a build."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    _append_to_config("\nai:\n  skills:\n    regenerate_on_build: true\n")
    main(["build"])
    skills_dir = tmp_path / "mysite" / ".claude" / "skills"
    assert sorted(path.name for path in skills_dir.iterdir()) == [
        "bartleby-ops.md",
        "bartleby-review.md",
        "bartleby-write.md",
    ]


def test_build_leaves_skills_alone_by_default_and_on_dry_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without the setting, or on a dry run, a build writes no skills."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    main(["build"])
    assert not (tmp_path / "mysite" / ".claude").exists()
    _append_to_config("\nai:\n  skills:\n    regenerate_on_build: true\n")
    main(["build", "--dry-run"])
    assert not (tmp_path / "mysite" / ".claude").exists()


# --- serve --dirty -----------------------------------------------------------


def test_serve_dirty_flag_is_gone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Incremental rebuilds are a non-goal, so ``serve --dirty`` is an unknown argument."""
    _scaffold_and_enter(tmp_path, monkeypatch)
    with pytest.raises(SystemExit) as exc:
        main(["serve", "--dirty"])
    assert exc.value.code == 2
    assert "--dirty" in capsys.readouterr().err
