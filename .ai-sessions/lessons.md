# Lessons Learned

## Recent
<!-- 10 most recent lessons, newest first -->

- `do-markdown` is not on PyPI — must add `[tool.uv.sources]` with `path = "../do-markdown", editable = true` for local resolution (2026-05-02)
- uv's `--dev` flag requires `[dependency-groups]` section, not `[project.optional-dependencies]` — the latter installs as extras, not dev deps (2026-05-02)
- Always `mkdir -p` before creating files in new directories — Write tool creates parents but Bash `touch` does not (2026-05-02)

## Categories
<!-- Lessons organized by topic -->

### Tooling
- `do-markdown` is not on PyPI — must add `[tool.uv.sources]` with `path = "../do-markdown", editable = true` for local resolution (2026-05-02)
- uv's `--dev` flag requires `[dependency-groups]` section, not `[project.optional-dependencies]` — the latter installs as extras, not dev deps (2026-05-02)

### Workflow
- Always `mkdir -p` before creating files in new directories — Write tool creates parents but Bash `touch` does not (2026-05-02)
