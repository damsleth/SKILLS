---
name: cj-code-review
description: Review a change for real bugs — a GitHub PR, a branch, or the local working-tree diff. Runs several independent review passes, scores each finding for confidence, drops everything below the bar, and prints a short report. Use when the user says "code review", "review this PR", "review my changes", "/cj-code-review", or asks whether a diff is safe to merge. Posts a PR comment only when asked.
---

# cj-code-review

## Overview

A confidence-filtered code review. The value is not in finding more issues — it is in
reporting only the ones that survive scrutiny. Most of the work is throwing findings away.

Model-agnostic on purpose: where this says **lightweight model**, use the cheapest model
your harness offers; **capable model** means your strongest available one. If your harness
has no subagents, run the passes yourself in sequence — the pass list matters, the
parallelism is just speed.

## Target

Resolve what to review, in this order:

1. Explicit argument — PR number/URL, branch name, or path.
2. An open PR for the current branch (`gh pr view --json number` — if `gh` is missing or
   unauthenticated, skip straight to 3, don't try to install it).
3. The local diff: uncommitted changes if any, else the branch's commits vs its merge base
   (`git diff $(git merge-base HEAD origin/HEAD)...HEAD`).

State in one line what you resolved to before reviewing.

## Steps

1. **Eligibility (lightweight model).** PR targets only: skip if the PR is closed, a draft,
   automated (dependabot/renovate), trivially safe, or already reviewed by you. Say why and
   stop. Local diffs are always eligible.
2. **Instruction files (lightweight model).** Collect *paths only* to the repo's agent
   instruction files — `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`,
   `.cursor/rules/*` — at the repo root and in every directory the diff touches.
3. **Summary (lightweight model).** Read the diff, return a short summary of the change.
4. **Review passes (capable model, parallel if you can).** Each returns a list of issues,
   each with the reason it was flagged:
   - **Instructions** — does the change violate the instruction files from step 2? Those
     files are guidance for writing code; not every line applies to review.
   - **Bugs** — shallow scan of the diff itself for real bugs. Don't go spelunking for
     context. Big things only; ignore likely false positives.
   - **History** — `git log`/`git blame` on the modified lines: does past context reveal a
     bug (a reverted fix reintroduced, a workaround removed, an invariant forgotten)?
   - **Prior review** — earlier PRs and review comments touching these files; does old
     feedback apply again? Skip this pass entirely if there's no PR host.
   - **Comments** — code comments in and around the modified code; does the change contradict
     documented intent?
5. **Score (lightweight model, one per issue).** Give the scorer the diff, the issue, and the
   instruction-file paths. For instruction-derived issues it must verify the file actually
   says that. Rubric, verbatim:
   - 0 — false positive, or pre-existing.
   - 25 — might be real, unverified. Stylistic and not explicitly called out in an
     instruction file.
   - 50 — verified real, but a nitpick or rare. Minor next to the rest of the change.
   - 75 — verified, very likely hit in practice; the change's approach is insufficient, or an
     instruction file names this directly.
   - 100 — certain, frequent, evidence directly confirms it.
6. **Filter at 80.** Below that, drop it silently. Nothing left → report no issues and stop.
7. **Re-check eligibility** (PR targets only) before posting anything.
8. **Report.** Terminal by default. Post a PR comment only if the user asked for one.

## False positives

Drop these without reporting:

- Pre-existing issues, and real issues on lines the change didn't touch.
- Things that look like bugs but aren't.
- Nitpicks a senior engineer wouldn't raise.
- Anything a linter, typechecker, compiler, or test run would catch — imports, types, broken
  tests, formatting. Assume CI runs them; don't run builds yourself.
- Generic "needs more tests / docs / security hardening", unless an instruction file requires it.
- Issues explicitly silenced in the code (lint-ignore comment and friends).
- Intentional behaviour changes that are the point of the change.

## Output

Brief. No emojis. Cite every finding with a file path — `path/to/file.ts:42` locally, or a
permalink on a PR. Never a verdict without a location.

```
### Code review

Found 2 issues:

1. <what breaks, and when> (AGENTS.md: "<quoted rule>")
   path/to/file.ts:40-44

2. <what breaks, and when> (bug: <one-line reason>)
   other/file.py:112-118
```

Nothing found:

```
### Code review

No issues found. Checked for bugs and instruction-file compliance.
```

## Posting to a PR

Only when asked. Use the host's CLI (`gh pr comment`, `glab mr note`) rather than web calls.
Permalinks need the full commit SHA inline — resolve it first with `git rev-parse HEAD` and
paste the literal value; a `$(...)` in the comment body renders as text.
`https://github.com/<owner>/<repo>/blob/<full-sha>/<path>#L40-L44`, one line of context either
side of the flagged lines.

Add no generated-by footer.
