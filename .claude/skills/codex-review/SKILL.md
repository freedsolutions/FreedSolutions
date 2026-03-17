---
name: codex-review
description: Run a Codex-backed review of the current git worktree, save a structured JSON report, and either present findings or apply fixes.
argument-hint: "[review|apply] [optional focus area]"
---

# Codex Review

Run a local Python script that packages the current git diff, project context files, and the full contents of changed files, then sends that bundle to the OpenAI Responses API for a structured review.

## Usage

```text
/codex-review
/codex-review review
/codex-review review focus on regressions in the Notion flow
/codex-review apply
/codex-review apply fix only the medium and high issues
```

## Mode selection

Interpret the first argument like this:

1. No argument: use `review`
2. `review`: run the review and present findings
3. `apply`: run the review, then fix issues that are real and safely actionable

Treat the remaining text, if any, as the focus string passed to the script.

## Step 1: Run the reviewer

Always run the local reviewer first from the repo root:

```text
python scripts/codex_review.py --mode <review|apply> --output .claude/tmp/codex-review/latest.json [--focus "..."]
```

If the script fails:

1. Report the failure clearly
2. Include the important stderr lines
3. Stop there

If the script succeeds:

1. Read the console summary
2. Inspect `.claude/tmp/codex-review/latest.json` if you need the full structured payload

## Step 2: Respond based on the review result

If the report status is `pass`:

1. Say the review passed
2. Mention any follow-up tests the report suggested
3. Do not invent issues that are not in the report

If the report status is `fail` and mode is `review`:

1. Present findings ordered by severity
2. Use a review mindset: bugs, regressions, security, and missing tests first
3. Ask whether to implement the fixes

If the report status is `fail` and mode is `apply`:

1. Treat the report as advisory, not absolute
2. Validate each finding against the local code before editing
3. Fix the issues that are real, in scope, and safe to change
4. After edits, rerun the same reviewer once to confirm the result if practical

## Guardrails

1. Do not blindly trust the external review if the code clearly disagrees
2. Do not auto-fix speculative low-signal findings
3. Keep the report path explicit in your answer: `.claude/tmp/codex-review/latest.json`
4. If the script says the payload is too large, narrow the scope instead of forcing a huge request
