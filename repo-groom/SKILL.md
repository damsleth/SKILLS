---
name: repo-groom
description: Bring ONE repo up to the quality baseline — CI workflow, AGENTS.md, LICENSE (public only), README accuracy, lint config — writing only what is MISSING and respecting the repo's tier policy. The fixer half of the repo-routine family; repo-health finds the gaps, this closes them. Use when the user says "repo-groom", "groom <repo>", "bring <repo> up to baseline", or "/repo-groom <repo>".
---

# repo-groom

The quality-baseline fixer. `repo-health` detects; this closes the gaps on
**one** repo. Grooming is a **write op**, so always show a plan and get a nod
before touching files, and make every change **idempotent** — never clobber a
file that is already good.

## Local overlay

If `~/.config/cj-skills/repo-groom.md` exists, read it before acting. It holds this user's own profiles, paths and conventions, and it wins over the defaults here.

## 1. Resolve tier and stack (read-only)

```bash
<skill-dir>/repo-groom.py <repo>          # human-readable plan
<skill-dir>/repo-groom.py <repo> --json   # same, machine-readable
```

`<repo>` may be a tier key (`CLI/mytool`), a bare name (`mytool`), or a path. The
script resolves the tier from `.repo-tiers.json` in the code root (`$REPO_ROOT`, default `~/code`; schema in the repo-health skill's `references/tiers.md`; without the file every repo counts as untiered), detects the stack, and
prints GAPS (to fix) vs ALREADY OK (to leave alone). Gap definitions match
`repo-health.py` exactly so the two never disagree.

**Refuse and stop** if the script says REFUSE:
- `W-ro` / `archive` / `external` → out of scope. Explain why, do nothing.
- **untiered** → tell the user to add it to `.repo-tiers.json` first (pick a
  tier); untiered repos are scratch, not groomed.

**Commit policy by tier** (the script prints this too):
- `S-priv` → commit **and push** OK.
- `S-pub` → commit + push OK, but releases/tags need approval. Extra baseline
  demands: LICENSE present, no committed secrets, README actually accurate.
- `W` → **new branch + local commits only**. Do NOT push. Tell the user to
  push/open the PR themselves.

## 2. Show the plan BEFORE writing

Turn the GAPS list into a short plan of proposed additions and show it to the
user. Name each file you'd create, note anything you'd leave untouched, and for
`S-pub` LICENSE ask which license before writing anything. Wait for a go.

## 3. Close the gaps — only what's MISSING, idempotently

Never overwrite an existing good file. If a check says ALREADY OK, skip it.

### CI workflow (skip entirely if CI already present)

Write `.github/workflows/ci.yml` adapted from the template for the stack.
Keep it minimal — lint + test + build for the repo's ACTUAL stack. Substitute
the real package/source path (the templates below use placeholders). Don't invent heavy CI.

**Python**:
```yaml
name: ci
on:
  push: { branches: [main] }
  pull_request:
concurrency: { group: ci-${{ github.ref }}, cancel-in-progress: true }
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with: { python-version: "3.11" }
      - run: pip install ruff
      - run: ruff check <PKG> tests      # <-- real package + test dirs
  test:
    runs-on: ubuntu-latest
    strategy: { fail-fast: false, matrix: { python-version: ["3.11", "3.12"] } }
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
          cache-dependency-path: pyproject.toml
      - run: pip install -e ".[dev]"     # or .[test] — match the repo's extras
      - run: pytest -q
```

**Rust**:
```yaml
name: CI
on:
  push: { branches: [main] }
  pull_request:
jobs:
  rust:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with: { components: clippy }
      - run: cargo check --workspace     # drop --workspace if single crate
      - run: cargo test --workspace
      - run: cargo clippy --workspace --all-targets -- -D warnings
```

**Node/TS** — use this minimal
conditional template (only runs lint/build/test if those scripts exist in
`package.json`; adjust `npm` → `pnpm`/`bun`/`yarn` to match the repo's lockfile):
```yaml
name: ci
on:
  push: { branches: [main] }
  pull_request:
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: npm }
      - run: npm ci
      - run: npm run lint --if-present
      - run: npm run build --if-present
      - run: npm test --if-present
```

**dotnet / shell / unknown**: no template here. Propose a minimal one to the
user or skip with a one-line note — don't build one blind.
<!-- ponytail: Python/Rust/Node only. dotnet/shell get a "skip with note", not a template. -->

`S-pub` repos may also want the `release.yml` pattern (tag-triggered, re-runs CI
gates, builds artifacts, creates the GitHub Release) — offer it, but any tag or
release still needs the user's approval per tier policy.

### Agent-instruction file — AGENTS.md, and only AGENTS.md

`AGENTS.md` is canonical in every repo, for every agent, whatever the harness.
**Never create a `CLAUDE.md`** — not a symlink, not an `@AGENTS.md` shim, not a
copy. A second path to the same content is a second place to forget to update.
The script reports which case applies:
- `ok-agents` / `ok-*-symlink` / `ok-claude-include` → already fine, do nothing.
  Existing pointers (`@AGENTS.md`, a one-line "read AGENTS.md", an old symlink)
  are harmless; leave them rather than churning the repo.
- `claude-only` → a real `CLAUDE.md` exists but no `AGENTS.md`.
  `git mv CLAUDE.md AGENTS.md`, content preserved. Do not put anything back.
- `missing` → generate a terse `/init`-style `AGENTS.md`: what the repo is, the
  stack, how to build/test, and any ground rules. Keep it short. Nothing else.

Anything durable you learn about a repo belongs in its `AGENTS.md`. If you find
real instructions sitting in a `CLAUDE.md`, move them over.

<!-- ponytail: one file, one direction. No bridges to maintain. -->

### LICENSE — S-pub only, only if missing

Default MIT with the repo owner as copyright holder (name from `git config user.name`). **Confirm the license choice
with the user before writing** — don't hardcode blindly. Never add a LICENSE to
S-priv/W repos as part of grooming.

### README — presence + accuracy check

If missing, add a minimal one. If present, skim it against the actual code and
**flag drift** (stale commands, renamed entry points, features that no longer
exist) — report it, don't rewrite the whole thing unless the user asks.

### lint/format config — only if the stack has an obvious standard and it's absent

`ruff` for Python, `eslint`/`prettier` for Node. Offer it; don't force it. Rust
ships rustfmt/clippy with the toolchain, so nothing to add. Skip if already
present (the script checks pyproject `[tool.ruff]`, `ruff.toml`, eslint/prettier
configs, and devDependencies).

## 4. Verify the groom didn't break anything

Run the repo's own tests/lint if present — `pytest -q`, `cargo test`,
`npm test`, `ruff check`, `cargo clippy`. Confirm green. YAML-lint the new
workflow if you can. If a tool isn't installed locally, say so rather than
claiming a pass.

## 5. Commit per tier policy

Stage only the files you added/changed (never `git add -A` — don't sweep stray
`.DS_Store` or unrelated dirty files). Clear message summarizing what was added
vs what was already fine, e.g. `chore: add CI workflow + AGENTS.md baseline`.

- `S-priv` → commit + push.
- `S-pub` → commit + push; no tag/release without approval.
- `W` → create a branch first (`git switch -c groom/baseline`), commit locally,
  and tell the user to push and open the PR. Do NOT push.

Finish by telling the user what changed, what was already at baseline, and (for
W repos) that the branch is waiting for them to PR.
