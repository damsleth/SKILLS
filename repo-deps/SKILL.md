---
name: repo-deps
description: Security & dependency pass over active repos — vulnerabilities (npm/pip/cargo/dotnet audit), outdated deps, secret scan, and unpinned GitHub Actions. Analysis half is read-only and runs monthly on cron; remediation applies SAFE minor/patch bumps interactively per tier policy and flags majors. Use when the user says "repo-deps", "dependency audit", "security audit my repos", "check for vulnerable deps", or "/repo-deps".
---

# repo-deps

The security & dependency fixer in the repo-routine family. Two halves:

- **A) Analysis** — read-only. `repo-deps.py` runs each repo's native audit
  tools without modifying anything and writes `REPO-DEPS.md` in the code root. This is the
  half a scheduled job can run (`--analysis`).
- **B) Remediation** — writes. Applies SAFE (minor/patch) dep bumps as commits,
  one repo at a time, tests after each, per tier policy. Majors are flagged for
  manual review, never auto-bumped. Secrets are never auto-remediated. This half
  is interactive only — it is NOT in the script and never runs on cron.

## Local overlay

If `~/.config/cj-skills/repo-deps.md` exists, read it before acting. It holds this user's own profiles, paths and conventions, and it wins over the defaults here.

## Scope & tiers

`.repo-tiers.json` in the code root (`$REPO_ROOT`, default `~/code`; schema in the repo-health skill's `references/tiers.md`) maps repos to tiers. Without the file every discovered repo is audited. Analysis covers the active tiers
(`S-priv` / `S-pub` / `W` / `W-ro`); `archive` and `external` are skipped.
Remediation autonomy per tier:

| Tier | Analysis | Remediation |
|---|---|---|
| **S-priv** | yes | commit **and push** safe bumps |
| **S-pub** | yes | commit + push safe bumps; **releases/tags need approval** |
| **W** | yes | branch + local commit only, **user pushes** — never push |
| **W-ro** | yes | **report only** — never commit/branch/push |
| archive / external | no | never touched |

Priority order in the report and when remediating: **deployed services first**
(repos with a root deploy config such as `wrangler.*`), then public (S-pub), then private (S-priv), then work (W/W-ro).

## A) Analysis — run it

```bash
<skill-dir>/repo-deps.py                       # all active repos
<skill-dir>/repo-deps.py CLI/mytool  # one or more repos
<skill-dir>/repo-deps.py --stdout              # don't write the file
```

Flags: `--root` (default `$REPO_ROOT`, else `~/code`), `--out` (default `REPO-DEPS.md`),
`--analysis` (explicit no-op — the script is analysis-only, this documents cron
intent), `--jobs`, `--stdout`.

Per stack it runs, where the tool exists: Node `npm/pnpm outdated` +
`audit --package-lock-only`; Python `uvx pip-audit` (from `uv export --frozen`
or `requirements.txt`); Rust `cargo audit` + `cargo outdated`; .NET
`dotnet list package --vulnerable` / `--outdated` (two calls). Plus a secret
scan (gitleaks `--redact` if installed, else a regex fallback that reports only
pattern name + `file:line`, never the value) and a GitHub Actions pinned-by-SHA
check. Missing tools (`cargo-audit`, `gitleaks`, …) are noted and skipped — a
missing tool never fails the run.

**Network:** `npm audit` / `pip-audit` hit advisory APIs, so a run needs
network; each tool call has a timeout and the sweep continues past hangs.

### Then (analysis)

1. Run the script (or read the cron-written `REPO-DEPS.md`).
2. Present in chat: the summary counts, then the deployed/public repos with real
   vulnerabilities first. Point at the file for the full table; don't paste it.
3. Note false positives from the regex secret fallback are expected (it flags
   patterns in test fixtures and `.env.example` files) — verify before alarming.
4. Offer remediation on the highest-priority repo with real, fixable vulns.

## B) Remediation — interactive, per tier policy

Do this ONE repo at a time, highest priority first. For each repo:

1. **Show the proposed bumps and get the user's OK before committing.** List the
   SAFE (minor/patch) bumps you intend to apply and the MAJOR bumps you are
   flagging but NOT applying. Wait for explicit approval.
2. Apply only the safe bumps (`npm update <pkg>` / `npm audit fix` without
   `--force`; `uv lock --upgrade-package <pkg>`; `cargo update -p <pkg>`;
   `dotnet add package <pkg>`). Never `npm audit fix --force` — that pulls
   majors.
3. **Run that repo's build/test and confirm green before committing.** If tests
   fail, revert the bump and flag it for manual review. Don't commit red.
4. Commit per tier: S-priv/S-pub commit + push; W branch + local commit only,
   no push; W-ro/archive/external never commit. Releases/tags on S-pub still
   need user approval.
5. **Majors:** never auto-bump. List them (package, current -> latest, likely
   breaking change) for the user to schedule manually.
6. **Secrets:** never auto-remediate. Report the hit; if it's real, tell the
   user to rotate the credential and scrub history themselves.

## Notes

- The script is read-only by construction — the monthly cron can never write to
  a repo. All writes happen here, interactively, under the tier matrix above.
- `npm outdated` without an installed `node_modules` returns sparse results;
  `npm audit --package-lock-only` still finds vulnerabilities from the lockfile.
