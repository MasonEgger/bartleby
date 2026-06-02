# Pruned Lessons

## Pruned 2026-06-02

- uv's `--dev` flag requires `[dependency-groups]` section, not `[project.optional-dependencies]` — the latter installs as extras, not dev deps (2026-05-02) — already incorporated in `~/.claude/plugins/cache/mmegger-plugins/python/0.1.0/skills/python/SKILL.md` (Packaging section)
- For workflow commands that gate execution, prefer decision-based wording ("emit `Invoked: X` or `No matching skill` in user-facing text") over rigid "STOP" gates — the agent confirms the decision in chat, which catches silent skips (2026-05-17) — already incorporated in the BPE execute-plan command's hardened Step 3 wording
- Reuse the parsing skeleton from `config.py` for every new YAML-backed module (`from __future__ import annotations`, `TYPE_CHECKING` for `Path`, `Any` at the `yaml.safe_load` boundary, `isinstance` narrowing, slotted dataclasses) — keeps mypy strict happy on first run and matches the established Bartleby style (2026-05-23) — promoted to project `CLAUDE.md` under a new "Module style" section
- Always `mkdir -p` before creating files in new directories — `Write` tool creates parents but Bash `touch` does not (2026-05-02) — outdated: confusingly worded and not actionable. The Write tool DOES create parent directories automatically; the lesson conflates two unrelated tools.
