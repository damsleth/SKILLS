---
name: repo-deep
description: On-demand deep code-quality pass over ONE repo — the deepest, most expensive routine in the repo family. Orchestrates ponytail-audit if installed (over-engineering/bloat), the code-review command if available (correctness + reuse/simplify/efficiency), and a test-gap check, then applies only the fixes the user approves, per tier policy. Use when the user says "repo-deep", "deep pass on <repo>", "deep-clean <repo>", "code-quality pass", or "/repo-deep".
---

# repo-deep

The code-level improver in the repo-routine family. `repo-health` detects,
`repo-groom` fixes the baseline, `repo-deps` handles security/deps — **this one
improves the code itself**: bloat, correctness, simplification, test gaps.

It is the **most expensive** routine, so:

- **ONE repo at a time.** Never batch. If handed several, do the first and stop.
- **It ORCHESTRATES existing skills — it does not reinvent them.** The analysis
  comes from `ponytail-audit` and the `code-review` command. Invoke those and
  consolidate. Both are optional; step 3 says what to do without them.
- **Plan-and-approve before applying.** Deep changes are high-touch. Present a
  prioritized findings list and get explicit approval on WHICH to apply. Never
  auto-apply a batch of refactors silently.

## Local overlay

If `~/.config/agent-skills/repo-deep.md` exists, read it before acting. It holds this user's own profiles, paths and conventions, and it wins over the defaults here.

## 1. Select + resolve tier (read-only)

```bash
<skill-dir>/repo-deep.py <repo>          # human-readable
<skill-dir>/repo-deep.py <repo> --json   # machine-readable
<skill-dir>/repo-deep.py                 # no arg -> nominate
```

`<repo>` may be a tier key (`CLI/mytool`), a bare name (`mytool`), or a path. The
script resolves the tier from `.repo-tiers.json` in the code root (`$REPO_ROOT`, default `~/code`; schema in the repo-health skill's `references/tiers.md`), detects the stack,
reports whether a test suite exists, and suggests a code-review effort by size.

**No arg** → it reads `REPO-HEALTH.md` in the code root and nominates the next candidate
(an explicit `/repo-deep <repo>` line if present, otherwise a derived
suggestion). **Always confirm the nominee with the user before running** — this
routine is never auto-run.

**Refuse and stop** if the script says REFUSE:
- `W-ro` / `archive` / `external` → out of scope. Explain why, do nothing. At
  most produce a read-only findings report if the user explicitly asks — never
  commit, branch, or push.
- **untiered** → tell the user to tier it in `.repo-tiers.json` first.

**Commit policy by tier** (the script prints this too):
- `S-priv` → commit **and push** OK.
- `S-pub` → commit + push OK; releases/tags need approval; hold the extra bar
  (no secrets, README accurate).
- `W` → **new branch + local commits only**. Do NOT push. The user pushes/PRs.

## 2. Orient (read-only)

Get a quick lay of the code before running the passes:
- Confirm the stack from step 1; read `README`/`AGENTS.md` if present.
- Note size, entry points, and whether there's a test suite (the script's
  `tests:` line). This calibrates the code-review effort and the test-gap read.

## 3. Run the analysis passes — COLLECT, don't apply yet

Run all three and gather findings. Apply nothing in this step.

### a) ponytail-audit — over-engineering / bloat

If the **`ponytail:ponytail-audit`** plugin skill is installed, load it, scoped to the
target repo. It returns a ranked cut list (`delete:` / `stdlib:` / `native:` /
`yagni:` / `shrink:`) and applies nothing — a one-shot report that drops
straight into the consolidated list below. Without the plugin, skim the repo
yourself for dead code, unused dependencies and needless abstraction, and list
the top cuts in the same one-line form.

### b) code-review — correctness + reuse/simplify/efficiency

If the **`code-review`** command is available, run it with the target path and an **explicit effort level every time** — default
`medium`, scaled by repo size (the script suggests one; small→`low`,
large→`high`). Always pass the level: omitting it makes the command reuse the
last level typed, which is sticky hidden state.

Collect findings only (no `--fix`); approved fixes are applied
by hand in step 5 so nothing lands without a nod. (`--comment` posts to a PR —
not part of this flow unless the user asks.)

Without the command, review the riskiest code yourself for correctness bugs
and obvious reuse/simplification, at the same one-line granularity.

### c) test-gap check — repo-deep's own work (not delegated)

Is there a test suite? What critical logic is untested? **Don't build a full
suite.** Ponytail-style, identify only the ONE or two highest-value missing
tests (the ones guarding the code most likely to break). Propose them; build
them only if the user picks them in step 4.

## 4. PRESENT a consolidated, prioritized list — get explicit approval

Merge the three passes into ONE prioritized list, in this order:

1. **Correctness bugs** (from code-review) — highest priority.
2. **Simplifications / deletions** (from ponytail-audit + code-review) — ranked
   biggest cut first.
3. **Test gaps** — the 1–2 highest-value missing tests.

Show it in chat, one line per finding (what + where + the fix). Then **ask which
to apply.** Do not proceed on assumption — the user picks the subset. Deep
refactors are never applied as a silent batch.

## 5. Apply approved fixes — smallest working diff, test after each

For each approved change, in priority order (bugs first):
- Make the change as the **shortest working diff** — deletion over addition,
  per ponytail. Leave a `ponytail:` comment on any deliberate shortcut
  (harvestable by `ponytail-debt` when that plugin is installed).
- **Run the repo's own tests/build after each logical change** and confirm green
  (`pytest -q`, `cargo test`, `npm test`, `cargo clippy`, `ruff check`, …). If a
  change goes red, revert it and flag it — never commit red. If a tool isn't
  installed locally, say so rather than claiming a pass.

## 6. Commit per tier policy — one commit per coherent change

Stage only the files you touched (never `git add -A` — don't sweep stray
`.DS_Store` or unrelated dirty files). One commit per coherent change, not one
giant refactor commit. Clear messages (`fix: …`, `refactor: …`, `test: …`).

- `S-priv` → commit + push.
- `S-pub` → commit + push; no tag/release without approval.
- `W` → branch first (`git switch -c deep/<repo>`), commit locally, tell the
  user to push and open the PR. Do NOT push.

Finish by summarizing what changed, what was **deferred** (approved-but-skipped
or flagged-for-later), and where you left `ponytail:` shortcut comments. For W
repos, note the branch is waiting for the user to PR.

## Notes

- Orchestration, not reinvention: the value here is consolidating
  `ponytail-audit` + `code-review` + a test-gap read into one approve-then-apply
  loop.
- The helper script is selection/tier-resolution only (mirrors repo-groom.py's
  `load_tiers`/`resolve`). All judgement and every write happen here, in chat,
  under the tier matrix above.
