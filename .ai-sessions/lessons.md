# Lessons Learned

## Recent
<!-- 10 most recent lessons, newest first -->

- Integration tests that only check file *existence* miss content bugs. After `bartleby new site && bartleby new post && bartleby build`, the post template rendered an empty author byline and the listing page rendered an empty post list, yet every test passed because they stopped at `(site / "blog" / "index.html").exists()` (2026-06-02)
- Dogfooding documentation against the tool is a high-signal integration test — writing the docs for Bartleby's shortcode feature immediately surfaced a real bug where the preprocessor didn't respect fenced code blocks or inline `code` spans (2026-06-02)
- Run `/bpe:lessons prune` periodically (not just at end of major work) — the BPE goal description called for it and the pile of redundant Python/YAML notes that accumulated across 27 implementation steps was real lint debt (2026-06-02)
- The previous session's "Suggested Skills for Next Session" line is a high-signal hint — trust it on the next `/bpe:execute-plan` and invoke those skills first, then layer on anything the current step uniquely needs (2026-05-23)
- Auto-loaded CLAUDE.md rules (arriving as system-reminders) are NOT equivalent to skills invoked via the Skill tool — bias toward invoking on uncertainty, since double-loading is harmless but skipping is not (2026-05-17)
- `do-markdown` is not on PyPI — must add `[tool.uv.sources]` with `path = "../do-markdown", editable = true` for local resolution (2026-05-02)

## Testing

- Integration tests that only check file *existence* miss content bugs. After `bartleby new site && bartleby new post && bartleby build`, the post template rendered an empty author byline and the listing page rendered an empty post list, yet every test passed because they stopped at `(site / "blog" / "index.html").exists()` (2026-06-02)
- Dogfooding documentation against the tool is a high-signal integration test — writing the docs for Bartleby's shortcode feature immediately surfaced a real bug where the preprocessor didn't respect fenced code blocks or inline `code` spans (2026-06-02)

## Tooling

- `do-markdown` is not on PyPI — must add `[tool.uv.sources]` with `path = "../do-markdown", editable = true` for local resolution (2026-05-02)

## Workflow

- Run `/bpe:lessons prune` periodically (not just at end of major work) — the BPE goal description called for it and the pile of redundant Python/YAML notes that accumulated across 27 implementation steps was real lint debt (2026-06-02)
- The previous session's "Suggested Skills for Next Session" line is a high-signal hint — trust it on the next `/bpe:execute-plan` and invoke those skills first, then layer on anything the current step uniquely needs (2026-05-23)
- Auto-loaded CLAUDE.md rules (arriving as system-reminders) are NOT equivalent to skills invoked via the Skill tool — bias toward invoking on uncertainty, since double-loading is harmless but skipping is not (2026-05-17)
