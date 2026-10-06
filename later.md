# Later

Punch list of things to look at when convenient. Not blocking.

## Stop hook misbehaviour

The session-scoped Stop hook attached to the BPE-loop goal keeps re-firing
after the goal's stop condition is met, with feedback that is partly
incorrect and partly about things outside the agent's control.

**Observed behaviour (2026-06-02, twice in one session):**

The hook claims things like "`/bpe:execute-plan` was never invoked",
"`/bpe:session-summary` was not invoked", "`/bpe:commit-message` was not
invoked" — but those skills WERE invoked via the Skill tool at every one
of the 27 implementation steps. The transcript shows the calls; the hook
seems to be looking for something other than Skill-tool invocations
(maybe slash-command literal text in the assistant's prose?) and missing
the actual workflow.

It also claims `/clear` was never run, which is true — but `/clear` is a
CLI built-in and the harness exposes no way for the agent to invoke it
programmatically. The agent flagged this in early turns. The hook
shouldn't be treating this as a process violation the agent could fix.

The lessons-pruning gap (only ran `/bpe:lessons prune` at the end rather
than periodically) was a legitimate critique; that one's been addressed.

**Diagnosis hypothesis:**

The hook's stopping condition is encoded as process-only ("you must use
the BPE loop") rather than outcome-or-process ("done when todo.md is
checked off and tests pass"). The goal text in `/goal` set at the
beginning of the session reads as outcome-based ("You are done when every
item in the @todo.md is checked off and the project is passing all
tests"), but the hook is interpreting the surrounding prose about the
workflow as an additional gate. After the outcome is met and the user
redirects to a new task (write docs, run audit), the hook keeps firing
because the workflow prose doesn't match the new task.

**Suggested fixes:**

1. Look at the hook config — probably in `.claude/settings.json` or
   wherever the `/goal` command stashes session-scoped Stop hooks. Either
   tighten the condition to outcome-only, or have it auto-clear once the
   outcome is met (the goal text said "It auto-clears once the condition
   is met"; that didn't seem to happen).
2. If the hook is supposed to detect BPE skill invocations, teach it to
   recognise Skill-tool calls rather than literal `/bpe:foo` text in
   assistant output.
3. Consider whether `/clear` should be reachable from the agent — there's
   precedent for harness-internal capabilities being callable via tools,
   but no current Skill or built-in tool wraps it. If it stays out of
   reach, the hook shouldn't penalise its absence.

**Workaround for now:** explain the situation to the user and ask whether
to continue current work or pause to investigate. Each fire of the hook
burns a turn.
