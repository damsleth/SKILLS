---
name: cj-uxloop
description: Run the UX loop on a web app with @damsleth/ux-loop (`uxl`) - capture screenshots, get a scored UX critique, apply fixes safely in a worktree, iterate until the score converges, and gate PRs in CI. Also covers first-time setup (install, `uxl.config.mjs`, required-flow mapping). Use when asked to "run the UX loop", review or improve a UI, audit UX or accessibility from screenshots, compare UX scores between runs, add UX review to CI, set up `uxl`, or troubleshoot `uxl` errors.
---

# cj-uxloop

`uxl` runs `shots -> review -> implement` against a real running app. What
it adds over an agent eyeballing a page ad hoc: forced flow coverage, an
objective score (axe-core + heuristics) blended with the LLM critique,
scope-limited edits in a worktree, keep-best rollback, and a PR gate. Use it
for repeatable, comparable runs; for a one-off "does this look right",
just open the page.

## Decide first

- No `uxl.config.mjs` in the repo root, or `uxl flows check` below 100%:
  do [Onboarding](#onboarding), then run.
- Config exists and coverage is complete: go straight to [Running](#running).
- Asked only for a review or a score: stop after `uxl review`. Never
  `implement` unless asked.

## Running

Run from the repo root. `current`/`branch` targets need a clean git tree.

1. Pre-flight: `git status` clean, `uxl flows check` complete, nothing
   already bound to the configured port (`uxl shots` refuses to reuse a server).
2. Pick scope. Default `uxl run --iterations 2 --score-threshold 85`.
   Constrain edits with `--scope css-only|text-only|layout-safe|unrestricted`
   (start with `css-only` or `layout-safe` on unfamiliar code).
3. On a new repo, preview first: `uxl implement --dry-run` or `uxl diff`
   (patch only, nothing applied).
4. Run: `uxl run`, or stepwise `uxl shots`, `uxl review`, `uxl implement`.
   Runner: `--runner claude|codex|copilot|openai` (openai reviews only).
5. Read the result, do not just report "done":
   - `.uxl/report.md` and the JSON in `.uxl/reports/` (score, `score_source`,
     `kept_iteration`, `best_score`, `restored`)
   - `.uxl/shots/`: look at a few screenshots yourself
   - the diff in the worktree/branch (`uxl diff`)
6. Land it: review the diff, then `uxl apply [--commit]`. Bad run:
   `uxl rollback --list`, then `uxl rollback --to <timestamp> --yes`.
7. Compare runs: `uxl report --left <old.json> --right <new.json>`.

Report to the user: score before/after, what changed (files, one line each),
what the loop could not fix, and the path to the diff.

## CI

`uses: damsleth/ux-loop@v1` runs `shots` + `review` on PRs (never implement),
posts a sticky comment, and fails below `fail-under`. Needs
`ANTHROPIC_API_KEY` (claude runner) or `OPENAI_API_KEY`. Local equivalent:
`uxl report --format github --fail-under 70` (exit 2 below threshold).

## Onboarding

Short path; details in [references/onboarding.md](references/onboarding.md).

1. Node 22+, a `package.json`, run from the repo root.
2. `npm i -D @damsleth/ux-loop playwright` (add `axe-core` for accessibility
   metrics, `openai` only for the openai runner). If the install 404s, the
   package is not published yet; install from the repo instead.
3. `uxl init` (`--non-interactive` for automation, `--force` only to replace).
4. Map flows (mandatory, `uxl shots` fails otherwise): `uxl flows check`,
   repair with `flows list|add|map|import-playwright --yes`, repeat to 100%.
   Keep `capture.flowMapping` names equal to real
   `capture.playwright.flows[].name`; slug-case ids; leave
   `capture.onboarding.status` `pending` until coverage is complete.
5. Smoke test: `uxl shots`, confirm `.uxl/shots/manifest.json`.

## Guardrails

- Never bypass incomplete flow coverage.
- Do not set `reuseExistingServer: true` unless the user manages the server.
- Do not enable `autoCommit`, or use `--target current`, on a dirty tree.
- Treat the score as a trend, not truth: re-run to confirm, and say which
  `score_source` produced it.

## References

- [references/onboarding.md](references/onboarding.md): config skeleton, coverage rules, runners, custom capture adapter
- [references/troubleshooting.md](references/troubleshooting.md): error-to-fix playbook
