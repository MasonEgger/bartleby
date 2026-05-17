# Lessons Learned

## Recent
<!-- 10 most recent lessons, newest first -->

- Auto-loaded CLAUDE.md rules (arriving as system-reminders) are NOT equivalent to skills invoked via the Skill tool — bias toward invoking on uncertainty, since double-loading is harmless but skipping is not (2026-05-17)
- mypy strict + `from __future__ import annotations` + `if TYPE_CHECKING:` is the clean way to keep type-only imports (e.g. `pathlib.Path`) out of the runtime import list and silence ruff `TC003` simultaneously (2026-05-17)
- When `mypy --strict` meets `yaml.safe_load`'s `Any` return, type the boundary as `Any`, then narrow with `isinstance` inside parse helpers — avoids casting churn while keeping strict mode happy (2026-05-17)
- For workflow commands that gate execution, prefer decision-based wording ("emit `Invoked: X` or `No matching skill` in user-facing text") over rigid "STOP" gates — the agent confirms the decision in chat, which catches silent skips (2026-05-17)
- `do-markdown` is not on PyPI — must add `[tool.uv.sources]` with `path = "../do-markdown", editable = true` for local resolution (2026-05-02)
- uv's `--dev` flag requires `[dependency-groups]` section, not `[project.optional-dependencies]` — the latter installs as extras, not dev deps (2026-05-02)
- Always `mkdir -p` before creating files in new directories — `Write` tool creates parents but Bash `touch` does not (2026-05-02)

## Python

- mypy strict + `from __future__ import annotations` + `if TYPE_CHECKING:` is the clean way to keep type-only imports (e.g. `pathlib.Path`) out of the runtime import list and silence ruff `TC003` simultaneously (2026-05-17)
- When `mypy --strict` meets `yaml.safe_load`'s `Any` return, type the boundary as `Any`, then narrow with `isinstance` inside parse helpers — avoids casting churn while keeping strict mode happy (2026-05-17)

## Tooling

- `do-markdown` is not on PyPI — must add `[tool.uv.sources]` with `path = "../do-markdown", editable = true` for local resolution (2026-05-02)
- uv's `--dev` flag requires `[dependency-groups]` section, not `[project.optional-dependencies]` — the latter installs as extras, not dev deps (2026-05-02)

## Workflow

- Auto-loaded CLAUDE.md rules (arriving as system-reminders) are NOT equivalent to skills invoked via the Skill tool — bias toward invoking on uncertainty, since double-loading is harmless but skipping is not (2026-05-17)
- For workflow commands that gate execution, prefer decision-based wording ("emit `Invoked: X` or `No matching skill` in user-facing text") over rigid "STOP" gates — the agent confirms the decision in chat, which catches silent skips (2026-05-17)
- Always `mkdir -p` before creating files in new directories — `Write` tool creates parents but Bash `touch` does not (2026-05-02)
