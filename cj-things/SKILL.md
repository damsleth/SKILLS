---
name: cj-things
description: Manage Things 3 (Cultured Code) tasks, projects, and areas from the terminal via the `things` CLI — full CRUD plus the standard read views (today, upcoming, inbox, deadlines, logbook) with JSON output. Use when the user wants to add / list / complete / update / delete a Things task or project, capture a todo into Things, or pull their Things tasks for planning. Feeds cj-weekly-review and pairs with cj-notes to turn captured notes into real tasks.
---

# cj-things

## Overview

`things` is a macOS CLI for [Things 3](https://culturedcode.com/things/) by Cultured Code.
The binary on PATH is **Kim's fork**: `~/.local/bin/things` →
`~/code/things3-cli` ([damsleth/things3-cli](https://github.com/damsleth/things3-cli),
forked from [ossianhempel/things3-cli](https://github.com/ossianhempel/things3-cli)).
The fork adds field-clearing via empty flag values — upstream silently drops them.

It talks to the app three ways, which is what decides whether a command needs setup:

- **Reads** (`today`, `tasks`, `search`, `show`, …) query the local SQLite database. The DB
  lives in the Things app sandbox, so the terminal needs **Full Disk Access** to read it.
- **Adds** (`add`, `add-project`, `add-area`) go through the Things URL scheme. No token.
- **Updates** (`update`, `update-project`, `update-area`) also use the URL scheme but
  **require an auth token** (`THINGS_AUTH_TOKEN`). See [Auth](#auth-only-for-updates).
- **Deletes** (`delete`, `delete-project`, `delete-area`) use AppleScript, so they need
  **Automation permission** and a confirmation, but no token.

macOS only. Run `things help <command>` for the authoritative flag list, or read
[`references/commands.md`](references/commands.md) for the full surface.

## Boot

```bash
command -v things        # expect ~/.local/bin/things → ~/code/things3-cli (the fork)
things --version         # CLI + detected Things.app version
things auth              # token status — required only for `update*`
```

If `things` is missing, say so and stop — don't fabricate task data. If a read errors with a
database/permission message, the terminal likely lacks Full Disk Access; tell the user to
grant it in System Settings → Privacy & Security → Full Disk Access.

## Reading tasks

Predefined views (each is read-only and accepts the same filter flags as `tasks`):

```bash
things today             # what Things would show in Today (incl. predicted/repeating)
things upcoming          # scheduled for the future
things inbox             # unsorted inbox
things deadlines         # everything with a hard deadline
things anytime           # the Anytime backlog
things someday           # the Someday backlog
things logbook           # completed/canceled history
things logtoday          # completed today
```

General-purpose list + lookup:

```bash
things tasks                                    # all incomplete, non-trashed todos
things tasks --project="Work" --tag=urgent      # filter by project / area / tag
things tasks --search="invoice"                 # substring match on title or notes
things tasks --query='title:/deploy/ AND tag:work'   # rich query: boolean + regex + fields
things search "standup"                         # search todos & projects by substring
things show --id=<UUID>                         # one item, exact; --recursive for checklists
things projects          # things areas          # things tags    # list the containers
```

Useful flags on every read command: `--status=incomplete|completed|canceled|any`,
`--limit=N` / `--offset=N`, date filters (`--due-before`, `--created-after`, `--modified-after`, …),
and `--no-header` to drop the column header.

### JSON for programmatic use

When another skill (or you) needs to *parse* the output rather than show it, add `--json`.
This is the integration backbone — prefer it over scraping the table:

```bash
things today --json
things tasks --project="Work" --json
things show --id=<UUID> --json
```

**Gotcha:** `show --json` returns a *sparse* object — unset and most non-core fields
are omitted entirely, so `jq '.deadline'` yields `null` whether the field was cleared
or never serialized. Fine for existence/title lookup; to **verify a field update**,
read back via `things tasks --search/--query --json` or the matching view
(`deadlines`, `upcoming`, …), which emit the full task shape.

Default table output uses columns `UUID  TITLE  PROJECT  AREA  HEADING  STATUS  TRASHED`.
The **UUID** is the stable handle — capture it from a read, then pass it to `update`/`delete`
via `--id=`. Never guess a UUID.

## Writing tasks

### Add (no token needed)

```bash
things add "Call the dentist"
things add "Draft Q3 report" --notes="Pull numbers from the dashboard first" \
  --when=today --deadline=2026-06-20 --tags=work,writing --list="Work"
printf 'Title line\nNote line one\nNote line two\n' | things add -   # first line = title, rest = notes
```

Common `add` flags: `--notes`, `--when=DATE|DATETIME` (e.g. `today`, `tomorrow`, `2026-06-10`,
or `someday`), `--deadline=DATE`, `--tags=a,b`, `--list="Project or Area"` (or `--list-id=ID`),
`--heading`, `--checklist-item="…"` (repeatable), and repeat flags (`--repeat=day|week|month|year`,
`--repeat-every=N`, …). `add-project` / `add-area` create containers.

### Update & complete (needs token)

Completing a todo *is* an update — there is no separate `complete` command:

```bash
things update --id=<UUID> --completed                  # mark done
things update --id=<UUID> --when=tomorrow --tags=work  # reschedule / retag
things update --id=<UUID> --canceled                   # cancel instead of complete
```

`update` mirrors `add`'s mutation flags (`--notes`, `--when`, `--deadline`, `--tags`,
`--add-tags`, `--completed`, `--canceled`, `--list`, `--heading`) and is identified by `--id`.
Bulk update via query filters (same as `tasks`) is possible but requires `--yes`.

**Clearing a field:** pass an empty value — a fork feature (upstream drops empty
flags from the URL, making this a silent no-op there):

```bash
things update --id=<UUID> --deadline=""              # remove the deadline
things tasks --search="<title>" --json               # verify via the tasks shape
```

### Delete (needs Automation permission)

```bash
things delete --id=<UUID> --confirm=<UUID>   # non-interactive single delete
things delete --id=<UUID>                    # interactive — prompts for confirmation
```

Bulk delete via query filters needs `--confirm=delete --yes`.

## Auth (only for updates)

`update*` commands need a Things URL-scheme token in `THINGS_AUTH_TOKEN`.

**On this machine the token lives in 1Password** and resolves via the `secret` helper
(`~/.zsh/secrets.zsh`) — no need to touch the Things UI:

```bash
source ~/.zsh/secrets.zsh 2>/dev/null   # required in harness/non-interactive shells:
                                        # the snapshot has a stale `secret` fn and loses
                                        # OP_SECRETS. Trailing compdef error is harmless —
                                        # don't `&&` directly after source.
tok=$(secret THINGS_AUTH_TOKEN -p)
THINGS_AUTH_TOKEN="$tok" things update --id=<UUID> --completed
```

Never print the token — pass it inline, and redact `auth-token=` from any echoed
URLs (`sed -E 's/auth-token=[^&" ]+/auth-token=REDACTED/g'`).

If `secret` reports the name unknown, fall back to manual setup:

1. Things 3 → Settings → General → Things URLs → enable/copy the token.
2. `export THINGS_AUTH_TOKEN=<token>` (add to `~/.zshrc` to persist).
3. Re-run `things auth` to confirm.

Reads and `add`/`delete` don't need it.

## Safety

- **Preview before bulk writes.** `--dry-run` prints the URL (writes) or the matched set
  (bulk update/delete) without touching anything. Use it whenever a query could match more
  than one todo.
- **Confirm destructive ops.** Deletes are real. Confirm with the user before `delete`,
  and never run a bulk query-delete without showing the matches (`tasks` with the same
  filters, or `delete --dry-run`) first.
- **Background by default.** Writes open Things in the background; pass `--foreground` only
  if the user wants the app brought forward.
- **UUIDs, not guesses.** Always resolve a UUID via a read (`tasks`/`search`/`show`) before
  `update`/`delete`. Don't act on a stale or assumed ID.
- Keep responses tight: when listing, curate to what matters rather than dumping the whole
  backlog (a Things DB can have hundreds of tasks).

## Integration with other skills

This skill is the single front door to Things for the rest of the suite — they call the same
`things` binary, ideally with `--json`.

- **cj-weekly-review** pulls the task picture in its Things3 step:
  `things today`, `things upcoming`, `things deadlines`, `things logtoday`. Use `--json`
  when it needs to merge Things tasks with calendar/ledger data programmatically.
- **cj-notes** captures human-facing notes. When a note contains a concrete, actionable
  next step ("send X", "follow up with Y"), offer to push it to Things with
  `things add "<task>" --notes="<context / link back to the note>"` so the action doesn't
  get lost in prose. Keep the note as the record; Things holds the *do*.
- **Capture flow generally:** anything the user says like "add that to my tasks", "put it in
  Things", "remind me to…" → `things add`. Confirm the title (and project/when if obvious)
  in one line; don't over-ask.
