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
    """new site renders the documented path/config keys."""
    result = NewSiteOutput(path="mysite/", config="mysite/bartleby.yml")
    payload = json.loads(render(result, "json"))
    assert payload == {"path": "mysite/", "config": "mysite/bartleby.yml"}


def test_new_post_output_json_shape() -> None:
    """new post renders the created file path."""
    result = NewPostOutput(path="content/blog/posts/hello.md")
    payload = json.loads(render(result, "json"))
    assert payload["path"] == "content/blog/posts/hello.md"
