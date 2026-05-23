# Lessons Learned

## Recent
<!-- 10 most recent lessons, newest first -->

- Reuse the parsing skeleton from `config.py` for every new YAML-backed module (`from __future__ import annotations`, `TYPE_CHECKING` for `Path`, `Any` at the `yaml.safe_load` boundary, `isinstance` narrowing, slotted dataclasses) — keeps mypy strict happy on first run and matches the established Bartleby style (2026-05-23)
- The previous session's "Suggested Skills for Next Session" line is a high-signal hint — trust it on the next `/bpe:execute-plan` and invoke those skills first, then layer on anything the current step uniquely needs (2026-05-23)
- Auto-loaded CLAUDE.md rules (arriving as system-reminders) are NOT equivalent to skills invoked via the Skill tool — bias toward invoking on uncertainty, since double-loading is harmless but skipping is not (2026-05-17)
- mypy strict + `from __future__ import annotations` + `if TYPE_CHECKING:` is the clean way to keep type-only imports (e.g. `pathlib.Path`) out of the runtime import list and silence ruff `TC003` simultaneously (2026-05-17)
- When `mypy --strict` meets `yaml.safe_load`'s `Any` return, type the boundary as `Any`, then narrow with `isinstance` inside parse helpers — avoids casting churn while keeping strict mode happy (2026-05-17)
- For workflow commands that gate execution, prefer decision-based wording ("emit `Invoked: X` or `No matching skill` in user-facing text") over rigid "STOP" gates — the agent confirms the decision in chat, which catches silent skips (2026-05-17)
- `do-markdown` is not on PyPI — must add `[tool.uv.sources]` with `path = "../do-markdown", editable = true` for local resolution (2026-05-02)
- uv's `--dev` flag requires `[dependency-groups]` section, not `[project.optional-dependencies]` — the latter installs as extras, not dev deps (2026-05-02)
- Always `mkdir -p` before creating files in new directories — `Write` tool creates parents but Bash `touch` does not (2026-05-02)

## Python

- Reuse the parsing skeleton from `config.py` for every new YAML-backed module (`from __future__ import annotations`, `TYPE_CHECKING` for `Path`, `Any` at the `yaml.safe_load` boundary, `isinstance` narrowing, slotted dataclasses) — keeps mypy strict happy on first run and matches the established Bartleby style (2026-05-23)
- mypy strict + `from __future__ import annotations` + `if TYPE_CHECKING:` is the clean way to keep type-only imports (e.g. `pathlib.Path`) out of the runtime import list and silence ruff `TC003` simultaneously (2026-05-17)
- When `mypy --strict` meets `yaml.safe_load`'s `Any` return, type the boundary as `Any`, then narrow with `isinstance` inside parse helpers — avoids casting churn while keeping strict mode happy (2026-05-17)

## Tooling

- `do-markdown` is not on PyPI — must add `[tool.uv.sources]` with `path = "../do-markdown", editable = true` for local resolution (2026-05-02)
- uv's `--dev` flag requires `[dependency-groups]` section, not `[project.optional-dependencies]` — the latter installs as extras, not dev deps (2026-05-02)

## Workflow

- The previous session's "Suggested Skills for Next Session" line is a high-signal hint — trust it on the next `/bpe:execute-plan` and invoke those skills first, then layer on anything the current step uniquely needs (2026-05-23)
- Auto-loaded CLAUDE.md rules (arriving as system-reminders) are NOT equivalent to skills invoked via the Skill tool — bias toward invoking on uncertainty, since double-loading is harmless but skipping is not (2026-05-17)
- For workflow commands that gate execution, prefer decision-based wording ("emit `Invoked: X` or `No matching skill` in user-facing text") over rigid "STOP" gates — the agent confirms the decision in chat, which catches silent skips (2026-05-17)
- Always `mkdir -p` before creating files in new directories — `Write` tool creates parents but Bash `touch` does not (2026-05-02)
