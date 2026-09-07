# ABOUTME: Structured output layer: result dataclasses plus a text/json formatter.
# The JSON shapes here are the stable CLI contract every agent consumer depends on.

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol

# Meaningful exit codes (spec.md "Global Flags"): 0 success, 1 error, 2 usage error.
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


class Result(Protocol):
    """A command result that can render to JSON and report an exit code."""

    @property
    def exit_code(self) -> int:
        """Process exit code this result implies."""
        ...

    def to_dict(self) -> dict[str, object]:
        """The result as a JSON-serializable mapping (the stable contract)."""
        ...

    def to_text(self) -> str:
        """The result as a human-readable single block."""
        ...


@dataclass(slots=True)
class Warning:
    """A non-fatal advisory tied to a content file."""

    file: str
    message: str
    code: str

    def to_dict(self) -> dict[str, object]:
        return {"file": self.file, "message": self.message, "code": self.code}


@dataclass(slots=True)
class ValidationError:
    """A fatal validation failure with file/line/field locality."""

    file: str
    line: int
    field: str
    message: str
    code: str

    def to_dict(self) -> dict[str, object]:
        return {
            "file": self.file,
            "line": self.line,
            "field": self.field,
            "message": self.message,
            "code": self.code,
        }


@dataclass(slots=True)
class BuildOutput:
    """Result of ``bartleby build`` (spec.md ``bartleby build`` JSON output)."""

    pages: int
    static_files: int
    duration_ms: int
    output_dir: str
    warnings: list[Warning] = field(default_factory=list)
    errors: list[Warning] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        return EXIT_ERROR if self.errors else EXIT_SUCCESS

    def to_dict(self) -> dict[str, object]:
        return {
            "status": "error" if self.errors else "success",
            "pages": self.pages,
            "static_files": self.static_files,
            "duration_ms": self.duration_ms,
            "errors": [error.to_dict() for error in self.errors],
            "warnings": [warning.to_dict() for warning in self.warnings],
            "output_dir": self.output_dir,
        }

    def to_text(self) -> str:
        lines = [
            f"Built {self.pages} pages ({self.static_files} static files) into {self.output_dir}"
        ]
        lines += [f"warning [{w.code}] {w.file}: {w.message}" for w in self.warnings]
        return "\n".join(lines)


@dataclass(slots=True)
class DryRunOutput:
    """Result of ``bartleby build --dry-run`` (spec.md dry-run JSON output)."""

    added: list[str]
    modified: list[str]
    unchanged: int
    deleted: list[str]

    @property
    def exit_code(self) -> int:
        return EXIT_SUCCESS

    def to_dict(self) -> dict[str, object]:
        return {
            "status": "dry_run",
            "added": self.added,
            "modified": self.modified,
            "unchanged": self.unchanged,
            "deleted": self.deleted,
        }

    def to_text(self) -> str:
        lines = [
            f"dry run: {len(self.added)} added, {len(self.modified)} modified, "
            f"{self.unchanged} unchanged, {len(self.deleted)} deleted"
        ]
        lines += [f"  + {path}" for path in self.added]
        lines += [f"  ~ {path}" for path in self.modified]
        lines += [f"  - {path}" for path in self.deleted]
        return "\n".join(lines)


@dataclass(slots=True)
class ValidateOutput:
    """Result of ``bartleby validate`` (spec.md ``bartleby validate`` JSON output)."""

    valid: bool
    files_checked: int
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        return EXIT_SUCCESS if self.valid else EXIT_ERROR

    def to_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "errors": [error.to_dict() for error in self.errors],
            "warnings": [warning.to_dict() for warning in self.warnings],
            "files_checked": self.files_checked,
        }

    def to_text(self) -> str:
        if self.valid:
            return f"validation passed ({self.files_checked} files checked)"
        lines = [f"validation failed ({self.files_checked} files checked)"]
        lines += [f"{e.file}:{e.line} [{e.code}] {e.field}: {e.message}" for e in self.errors]
        lines += [f"{w.file}:{w.line} [{w.code}] {w.field}: {w.message}" for w in self.warnings]
        return "\n".join(lines)


@dataclass(slots=True)
class NewSiteOutput:
    """Result of ``bartleby new site`` (spec.md JSON output)."""

    path: str
    config: str

    @property
    def exit_code(self) -> int:
        return EXIT_SUCCESS

    def to_dict(self) -> dict[str, object]:
        return {"path": self.path, "config": self.config}

    def to_text(self) -> str:
        return f"Created site at {self.path}"


@dataclass(slots=True)
class NewPostOutput:
    """Result of ``bartleby new post``: the created content file path."""

    path: str

    @property
    def exit_code(self) -> int:
        return EXIT_SUCCESS

    def to_dict(self) -> dict[str, object]:
        return {"path": self.path}

    def to_text(self) -> str:
        return f"Created post {self.path}"


@dataclass(slots=True)
class RawOutput:
    """A pre-serialised text payload (e.g. export output) emitted as-is.

    Export already produces its own JSONL/JSON/CSV string, so the output layer
    passes it through unchanged in both text and JSON modes rather than wrapping
    it in another JSON object.
    """

    text: str

    @property
    def exit_code(self) -> int:
        return EXIT_SUCCESS

    def to_dict(self) -> dict[str, object]:  # pragma: no cover - render() bypasses this
        return {"output": self.text}

    def to_text(self) -> str:
        return self.text


@dataclass(slots=True)
class GenerateSkillOutput:
    """Result of ``bartleby generate-skill`` (spec.md generate-skill JSON output)."""

    skills_generated: list[dict[str, object]]
    output_dir: str

    @property
    def exit_code(self) -> int:
        return EXIT_SUCCESS

    def to_dict(self) -> dict[str, object]:
        return {
            "skills_generated": self.skills_generated,
            "output_dir": self.output_dir,
        }

    def to_text(self) -> str:
        lines = [f"Generated {len(self.skills_generated)} skills into {self.output_dir}"]
        lines += [f"  {entry['path']}" for entry in self.skills_generated]
        return "\n".join(lines)


@dataclass(slots=True)
class ErrorOutput:
    """A failure rendered to stderr (text) or stdout (json) per the error contract.

    :ivar usage: When ``True``, the failure is a usage error and exits 2.
    """

    message: str
    code: str
    file: str | None = None
    usage: bool = False

    @property
    def exit_code(self) -> int:
        return EXIT_USAGE if self.usage else EXIT_ERROR

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"error": self.message, "code": self.code}
        if self.file is not None:
            payload["file"] = self.file
        return payload

    def to_text(self) -> str:
        location = f" {self.file}:" if self.file is not None else ""
        return f"error [{self.code}]{location} {self.message}"


@dataclass(slots=True)
class RenderOutput:
    """Result of ``bartleby render <path>`` (spec.md single-page render output).

    Exactly one of ``html`` or ``markdown`` is populated depending on the
    ``--format`` requested; ``metadata`` mode populates neither. Fields that do
    not apply to the chosen format are omitted from the JSON contract.
    """

    path: str
    url: str
    metadata: dict[str, object]
    word_count: int
    read_time_minutes: int
    warnings: list[Warning] = field(default_factory=list)
    html: str | None = None
    markdown: str | None = None

    @property
    def exit_code(self) -> int:
        return EXIT_SUCCESS

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "path": self.path,
            "url": self.url,
            "metadata": self.metadata,
            "word_count": self.word_count,
            "read_time_minutes": self.read_time_minutes,
            "warnings": [warning.to_dict() for warning in self.warnings],
        }
        if self.html is not None:
            payload["html"] = self.html
        if self.markdown is not None:
            payload["markdown"] = self.markdown
        return payload

    def to_text(self) -> str:
        if self.html is not None:
            return self.html
        if self.markdown is not None:
            return self.markdown
        title = self.metadata.get("title", "")
        return f"{title} ({self.path})"


@dataclass(slots=True)
class LintOutput:
    """Result of ``bartleby lint`` (spec.md lint JSON output)."""

    issues: list[dict[str, object]]
    errors: int
    warnings: int
    info: int

    @property
    def exit_code(self) -> int:
        return EXIT_ERROR if self.errors else EXIT_SUCCESS

    def to_dict(self) -> dict[str, object]:
        return {
            "issues": self.issues,
            "summary": {"errors": self.errors, "warnings": self.warnings, "info": self.info},
        }

    def to_text(self) -> str:
        if not self.issues:
            return "lint: no issues"
        lines = [
            f"{issue['severity']} [{issue['rule']}] {issue['file']}: {issue['message']}"
            for issue in self.issues
        ]
        lines.append(f"{self.errors} error(s), {self.warnings} warning(s), {self.info} info")
        return "\n".join(lines)


def render(result: Result, fmt: str) -> str:
    """Serialize ``result`` to ``"json"`` or ``"text"``.

    One code path drives both formats: every result type supplies ``to_dict``
    (the stable JSON contract) and ``to_text`` (the human form). JSON is emitted
    with sorted keys so output is byte-stable for diffing and golden tests.

    :param result: The command result to render.
    :param fmt: Either ``"json"`` or ``"text"``.
    :returns: The serialized string (no trailing newline).
    """
    # Export already produces its own structured payload (JSONL/JSON/CSV chosen
    # via --format), so it is emitted verbatim regardless of --output.
    if isinstance(result, RawOutput):
        return result.text
    if fmt == "json":
        return json.dumps(result.to_dict(), sort_keys=True)
    return result.to_text()
