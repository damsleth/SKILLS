---
name: cj-timereg
description: Sync confirmed did hours into the legacy timereg.inmeta.com timesheet via timereg-cli. Use when the user asks to "do my hours", "sync timereg", "update timereg", or mentions Norconsult/Inmeta/timereg time entry. Drives the timereg-cli state machine via `timereg-cli status --json` and routes the user through login → init (mapping) → sync as needed.
version: 1.0.0
author: damsleth
allowed-tools:
  - Bash
  - Read
  - Skill
tags:
  - timesheet
  - timereg
  - hours
  - time-tracking
  - sync
---

# cj-timereg Skill

Sync hours from did into the legacy timereg.inmeta.com timesheet.

## Architecture

```
Calendar (Outlook)  -- owa-cal (cj-owa-tools) -->  did  -- did-cli -->  timereg-cli  -->  timereg.inmeta.com
                                                    |
                                                    +-->  (future) xledger-cli, swondp-cli, ...
```

`timereg-cli` is one leg of the fan-out from `did`. It reads confirmed did
entries and emits timereg rows. Other LOB systems get their own CLI with
the same `status --json` contract.

This skill **only** handles the timereg leg. For the calendar/did side,
delegate to `cj-did`. For an end-to-end "do my hours" run, an outer
orchestrator skill is expected to compose `cj-did` + `cj-timereg` + future
peers.

## Boot

Every invocation, run:

```bash
timereg-cli status --json
```

That single call returns everything needed to decide what to do. Schema:

```json
{
  "tool": "timereg-cli",
  "version": "0.2.0",
  "session": "valid|expired|missing",
  "deps": { "did-cli": "ok|missing" },
  "data": {
    "mapping_path": "...",
    "mapping_exists": true,
    "mapping_version": 2,
    "did_window_days": 30,
    "tags_seen": 12,
    "tags_mapped": 10,
    "tags_skipped": 3,
    "tags_unmapped": ["UNE 4LYF", "ACME PILOT"]
  },
  "ready": false,
  "next_action": {
    "cmd": "login|init|sync|null",
    "argv": ["timereg-cli", "..."],
    "reason": "human-readable why",
    "interactive": true|false
  },
  "warnings": []
}
```

## Decision tree

Branch on `next_action.cmd`:

### `login`
Session is missing or expired. Run:

```bash
timereg-cli login
```

This is **non-interactive** if `USER`/`PASS` are set in `~/.config/timereg-cli/.env`
(or `./.env`). If it prompts and there's no TTY, tell the user to populate
the .env file and re-run.

### `init` (interactive — hand to user)
There are unmapped did tags. **Do not** try to drive `init` yourself —
each tag walk requires the user's judgement (which timereg customer/
project/activity does this did tag map to?).

Tell the user:

> You have N unmapped did tags: <list from `data.tags_unmapped`>.
> Run `timereg-cli init` in a terminal — for each tag you'll get
> `[a]ccept / [e]dit / [s]kip / [q]uit`. Quit anytime, your progress
> is saved.

After they're done, re-run `timereg-cli status --json` to verify
`tags_unmapped` is empty.

### `sync` (the happy path)
Run a dry-run, show the user what would land:

```bash
timereg-cli sync --period current --pretty
```

Then explicitly note: **timereg-cli does not POST to the site yet.** It
only prints rows that *would* be entered. The user must still copy them
into the timereg UI manually, until `--commit` is implemented.

### `null` (with reason)
`did-cli` missing → tell user to install it.
`did-cli` failed → surface the warning, suggest `did-cli config` (delegate to `cj-did`).
No did entries in window → no hours to sync, you're done.

## Common requests

**"do my hours" / "sync timereg" / "update timereg"**
1. `timereg-cli status --json`
2. Walk the decision tree once. If it lands on `sync`, run dry-run and
   show output.
3. If `next_action.interactive` is true, hand off to user with clear
   instructions and stop.

**"what's my timereg state?"**
Run `timereg-cli status` (pretty mode, no `--json`) and pass through to user.

**"show me what would land in timereg this week"**
```bash
timereg-cli sync --period current --pretty
```

**"add a new project to my timereg mapping"** / **"map this did tag"**
Hand off: `timereg-cli init` (the `[e]dit` branch walks the live timereg
customer/project/activity dropdowns).

**"browse timereg customers"** / **"what's in timereg?"**
```bash
timereg-cli browse        # interactive drill-down
timereg-cli customers     # list bookable customers
```

## Caveats

- **Mapping is per-machine.** Lives at `~/.config/timereg-cli/config.json`.
  Not synced anywhere by default.
- **`init` and `browse` create a transient unsaved row** on the timereg
  server. The CLI cleans up via the "Slett" button on exit, but if a
  process is SIGKILLed, a 0-hour ghost row may persist. Visible/deletable
  in the timereg UI.
- **No `--commit` yet.** sync is dry-run only.
- **The customer list differs by source:** TimeSkjema = ~377 bookable
  customers (default for `browse`/`init`); ProsjektAdmin = ~800 known
  (`timereg-cli customers --all`).

## When NOT to use this skill

- User wants to fix calendar events or did directly → `cj-did`.
- User wants to plan their week → `cj-weekly-review`.
- User asks about other LOB systems (xledger, swondp) → those CLIs don't
  exist yet; flag it as future work.
