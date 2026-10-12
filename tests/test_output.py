# ABOUTME: Tests for the structured output layer (text + json formatter).
# Covers build/validate/new/error result shapes and meaningful exit codes.

from __future__ import annotations

import json

from bartleby.output import (
    EXIT_ERROR,
    EXIT_SUCCESS,
    EXIT_USAGE,
    BuildOutput,
    ErrorOutput,
    NewPostOutput,
    NewSiteOutput,
    ServeStartOutput,
    ValidateOutput,
    ValidationError,
    Warning,
    render,
)


def test_build_output_json_shape() -> None:
    """A build result renders to the documented JSON keys."""
    result = BuildOutput(
        pages=47,
        static_files=12,
        duration_ms=1230,
        output_dir="site/",
        warnings=[Warning(file="content/blog/posts/old.md", message="stale", code="W001")],
    )
    payload = json.loads(render(result, "json"))
    assert payload["status"] == "success"
    assert payload["pages"] == 47
    assert payload["static_files"] == 12
    assert payload["duration_ms"] == 1230
    assert payload["output_dir"] == "site/"
    assert payload["errors"] == []
    assert payload["warnings"] == [
        {"file": "content/blog/posts/old.md", "message": "stale", "code": "W001"}
    ]


def test_build_output_json_is_deterministic() -> None:
    """Rendering the same result twice yields byte-identical JSON."""
    result = BuildOutput(pages=3, static_files=1, duration_ms=10, output_dir="site/")
    assert render(result, "json") == render(result, "json")


def test_build_output_exit_code_success() -> None:
    """A build result exits 0."""
    result = BuildOutput(pages=1, static_files=0, duration_ms=5, output_dir="site/")
    assert result.exit_code == EXIT_SUCCESS


def test_build_output_text_is_human_readable() -> None:
    """Text mode renders the same data without JSON braces."""
    result = BuildOutput(pages=47, static_files=12, duration_ms=1230, output_dir="site/")
    text = render(result, "text")
    assert "47" in text
    assert "site/" in text
    assert not text.lstrip().startswith("{")


def test_validate_output_json_shape() -> None:
    """A validate result renders the documented valid/errors/warnings keys."""
    result = ValidateOutput(
        valid=False,
        files_checked=47,
        errors=[
            ValidationError(
                file="content/blog/posts/foo.md",
                line=3,
                field="date",
                message="required field missing",
                code="E001",
            )
        ],
    )
    payload = json.loads(render(result, "json"))
    assert payload["valid"] is False
    assert payload["files_checked"] == 47
    assert payload["errors"][0]["field"] == "date"
    assert payload["errors"][0]["code"] == "E001"
    assert payload["warnings"] == []


def test_validate_output_exit_code_reflects_validity() -> None:
    """An invalid validate result exits 1; a valid one exits 0."""
    bad = ValidateOutput(
        valid=False,
        files_checked=1,
        errors=[ValidationError(file="f.md", line=1, field="x", message="m", code="E001")],
    )
    good = ValidateOutput(valid=True, files_checked=1)
    assert bad.exit_code == EXIT_ERROR
    assert good.exit_code == EXIT_SUCCESS


def test_validate_output_text_lists_errors() -> None:
    """Text mode surfaces each validation error line."""
    result = ValidateOutput(
        valid=False,
        files_checked=1,
        errors=[
            ValidationError(file="f.md", line=3, field="date", message="missing", code="E001")
        ],
    )
    text = render(result, "text")
    assert "f.md" in text
    assert "missing" in text


def test_error_output_json_shape() -> None:
    """An error renders as a JSON object with error/code/file keys."""
    result = ErrorOutput(message="boom", code="build_error", file="content/bad.md")
    payload = json.loads(render(result, "json"))
    assert payload["error"] == "boom"
    assert payload["code"] == "build_error"
    assert payload["file"] == "content/bad.md"


def test_error_output_omits_null_file() -> None:
    """An error with no file omits the file key rather than emitting null."""
    result = ErrorOutput(message="bad config", code="config_error")
    payload = json.loads(render(result, "json"))
    assert "file" not in payload


def test_error_output_exit_code_default_one() -> None:
    """An error exits 1 by default and 2 when flagged as a usage error."""
    assert ErrorOutput(message="m", code="config_error").exit_code == EXIT_ERROR
    assert ErrorOutput(message="m", code="usage_error", usage=True).exit_code == EXIT_USAGE


def test_error_output_text_carries_code_and_message() -> None:
    """Text mode prints a clean message with the stable code."""
    result = ErrorOutput(message="boom", code="build_error", file="content/bad.md")
    text = render(result, "text")
    assert "build_error" in text
    assert "boom" in text
    assert "content/bad.md" in text


def test_new_site_output_json_shape() -> None:
    """new site renders path, config, created entries, next command, and the flags."""
    result = NewSiteOutput(
        path="mysite/",
        config="mysite/bartleby.yml",
        created=["bartleby.yml", "content/"],
        next_command="cd mysite && bartleby serve",
    )
    payload = json.loads(render(result, "json"))
    assert payload == {
        "path": "mysite/",
        "config": "mysite/bartleby.yml",
        "created": ["bartleby.yml", "content/"],
        "next_command": "cd mysite && bartleby serve",
        "blog": False,
        "full_config": False,
    }


def test_new_site_output_text_names_the_next_step() -> None:
    """new site lists what it created, then tells a first-time user how to see the site."""
    result = NewSiteOutput(
        path="mysite/",
        config="mysite/bartleby.yml",
        created=["bartleby.yml", "content/"],
        next_command="cd mysite && bartleby serve",
    )
    assert render(result, "text").splitlines() == [
        "Created site at mysite/",
        "  bartleby.yml",
        "  content/",
        "Next: cd mysite && bartleby serve",
    ]


def test_new_site_output_text_notes_the_flags() -> None:
    """--blog and --full-config each annotate the entry they changed."""
    result = NewSiteOutput(
        path="mysite/",
        config="mysite/bartleby.yml",
        created=["bartleby.yml", "content/"],
        next_command="cd mysite && bartleby serve",
        blog=True,
        full_config=True,
    )
    text = render(result, "text")
    assert "  bartleby.yml (every option, from --full-config)" in text
    assert "  content/ (with a blog in content/blog/)" in text


def test_serve_start_output_text_has_summary_url_and_stop_hint() -> None:
    """The serve startup block is the build summary, the URL, and the stop hint."""
    result = ServeStartOutput(
        url="http://127.0.0.1:8123/",
        build=BuildOutput(pages=7, static_files=5, duration_ms=12, output_dir="site/"),
    )
    assert render(result, "text").splitlines() == [
        "Built 7 pages (5 static files) into site/",
        "Serving at http://127.0.0.1:8123/",
        "Press Ctrl+C to stop",
    ]


def test_serve_start_output_json_is_a_ready_event() -> None:
    """The same facts as one JSON object a machine reader can parse."""
    result = ServeStartOutput(
        url="http://127.0.0.1:8123/",
        build=BuildOutput(pages=7, static_files=5, duration_ms=12, output_dir="site/"),
    )
    assert json.loads(render(result, "json")) == {
        "type": "ready",
        "url": "http://127.0.0.1:8123/",
        "pages": 7,
        "static_files": 5,
        "output_dir": "site/",
        "stop_hint": "Press Ctrl+C to stop",
    }


def test_new_post_output_json_shape() -> None:
    """new post renders the created file path."""
    result = NewPostOutput(path="content/blog/posts/hello.md")
    payload = json.loads(render(result, "json"))
    assert payload["path"] == "content/blog/posts/hello.md"
