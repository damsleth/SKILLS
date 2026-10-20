---
name: repo-health
description: Read-only weekly sweep over every repo under the code root (default ~/code, override with REPO_ROOT or --root) — dirty worktrees, unpushed/unpulled commits, broken git state, stale branches, missing CI/AGENTS.md/LICENSE, dead remotes, untiered or unversioned dirs. Writes REPO-HEALTH.md at the root and nominates the next repos for /repo-groom, /repo-deps or /repo-deep. Use when the user says "repo health", "sweep my repos", "how are my repos doing", "/repo-health", or on the weekly cron.
---

# repo-health

The detector in the repo-routine family. It only *finds* things; `/repo-groom`,
`/repo-deps` and `/repo-deep` are the fixers.

**Read-only, no exceptions.** Never commit, stash, fetch, prune, or `git gc`
anything while running this — not even "while I'm in there". If the user asks
for a fix mid-sweep, finish the report first and hand off to the fixer skill.

## Local overlay

If `~/.config/cj-skills/repo-health.md` exists, read it before acting. It holds this user's own profiles, paths and conventions, and it wins over the defaults here.

## Scope

The code root is `$REPO_ROOT` (default `~/code`; `--root` overrides). Its
`.repo-tiers.json` maps relative repo paths to tiers
(`S-priv` / `S-pub` / `W` / `W-ro` / `archive` / `external`); schema and tier
meanings are in [references/tiers.md](references/tiers.md), the single source
for the whole repo-routine family. Tiers `archive` and `external` are skipped. Repos on disk but absent from the file are swept
anyway and listed under "Not in `.repo-tiers.json`". If the file is missing,
everything discovered gets swept.

## Run it

```bash
<skill-dir>/repo-health.py            # ~1s over ~100 repos
<skill-dir>/repo-health.py --network  # + ls-remote per origin
<skill-dir>/repo-health.py --stdout   # don't write the file
```

Flags: `--root` (default `$REPO_ROOT`, else `~/code`), `--out` (default
`REPO-HEALTH.md`, relative to root, so the report follows the root), `--jobs`, `--stale-days` (default 180), `--network`, `--stdout`.

Default run is local-only and takes about a second. Use `--network` when the
user asks about dead remotes or it's been a while — it adds a few seconds and
can hang on VPN-only hosts.

When a weekly cron is set up, it runs `python3 <skill-dir>/repo-health.py --network`,
so a fresh `REPO-HEALTH.md` is usually already at the root; read it before rerunning.

## Then

1. Run the script. It writes the whole report itself, including a heuristic
   Top 5.
2. Read the report back and sanity-check it. The script scores mechanically; you
   know context it doesn't. Re-rank or replace the Top 5 by editing
   `REPO-HEALTH.md` when the heuristic picked something silly (a scratch repo
   with 200 dirty binaries is not the week's most valuable action).
3. Present to the user in chat: the summary counts in one or two lines, then the
   Top 5 as a numbered list with the concrete command to run. Don't paste the
   findings table — point at the file.

Nomination rules the script uses, for when you're re-ranking:

| Signal | Nominate |
|---|---|
| broken git state, dead remote | manual repair — no routine can run on it |
| missing CI / AGENTS.md / LICENSE | `/repo-groom <repo>` |
| has a dep manifest, otherwise fine | `/repo-deps <repo>` |
| clean baseline, active | `/repo-deep <repo>` |

## Notes

- "Broken" means `git log -1` fails. Two common causes show in the message:
  `not a git repository` (usually a vanished `.git/refs/`) and
  `cannot read commit object` (torn object store). Different fixes — re-init
  refs vs. `git fetch --refetch` or re-clone.
- Agent co-author trailers are matched on the *identity* in the trailer
  (`noreply@anthropic.com`, Copilot, Devin, Cursor, Codex), never on the
  `Co-authored-by:` key alone — real humans co-author too, and their trailers
  stay. Nothing scrubs them automatically: the fix is a `git filter-repo`
  history rewrite plus a force-push, which breaks every other clone, so it is
  never a `/repo-groom` step and never runs on a cron. Read the committer list
  before believing a repo is shared: two emails are usually one person with a
  laptop typo (`ann@example.org` vs `ann@example.com`), while a fork shows
  strangers and bots. Public repos may have clones no committer list can see.
  Take a backup branch first (`backup/pre-history-scrub-<date>`).
- Stale branch = merged into HEAD, or no commit in `--stale-days`. The current
  branch is never counted.
- Untiered repos are exempt from the baseline-file checks; they're scratch until
  the user tiers them. If one deserves a tier, say so.
