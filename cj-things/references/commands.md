# `things` command reference

Companion to `SKILL.md`. Captures the full command surface of `things3-cli` (binary: `things`,
v0.3.0). The CLI is self-documenting — `things help` lists commands and `things help <command>`
prints the authoritative flags. This file is a quick map so you don't have to shell out for the
common cases. When in doubt, trust `things help <command>` over this doc.

## Global

```
things [GLOBAL OPTIONS...] <COMMAND> [ARGS...]
```

| Global option | Effect |
|---|---|
| `-V`, `--version` | Print things3-cli + detected Things.app version |
| `--debug` | Verbose debug output |
| `--foreground` | Open Things in the foreground (default: background) |
| `--dry-run` | Print the Things URL (or matched set) without acting |

Environment:

- `THINGS_AUTH_TOKEN` — URL-scheme token, **required by `update*`**. Set via `things auth` steps.
- `THINGSDB` — override the path to the Things SQLite database (same as `--db=PATH`).

## Read commands (SQLite, read-only)

Need Full Disk Access for the terminal. All accept the **shared read filters** below.

| Command | Lists |
|---|---|
| `today` | Tasks Things would show in Today (incl. predicted/repeating) |
| `upcoming` | Scheduled for the future |
| `inbox` | Unsorted inbox |
| `anytime` / `someday` | The two backlog buckets |
| `deadlines` | Everything with a hard deadline |
| `repeating` / `templates` | Active repeats / their template tasks |
| `logbook` | Completed/canceled history |
| `logtoday` / `createdtoday` | Completed today / created today |
| `completed` / `canceled` / `trash` | By terminal status |
| `tasks` | All todos (default: incomplete, non-trashed) |
| `projects` / `areas` / `tags` | List the containers |
| `all` | Key sections in one dump |
| `search <QUERY>` | Substring search over todos & projects (title/notes) |
| `show --id=<ID>` \| `show <QUERY>` | One item, exact match; `--recursive` adds checklist items |
| `list-project-tasks --id=<UUID>` | Todos inside a project |

### Shared read filters

Apply to `tasks`, `today`, `upcoming`, `search`, and the other list views:

| Flag | Meaning |
|---|---|
| `--status=incomplete\|completed\|canceled\|any` | Status filter (default `incomplete`) |
| `--project=<title or ID>` | Filter by project |
| `--area=<title or ID>` | Filter by area |
| `--tag=<title or ID>` | Filter by tag |
| `--search=<text>` | Case-insensitive substring on title/notes |
| `--query=<expr>` | Rich query: boolean ops, fields, regex — e.g. `title:/deploy/ AND tag:work` |
| `--limit=N` / `--offset=N` | Paginate (limit `0` = no limit; default 200) |
| `--created-after` / `--created-before` | `YYYY-MM-DD` or RFC3339 |
| `--modified-after` / `--modified-before` | `YYYY-MM-DD` or RFC3339 |
| `--due-before=<YYYY-MM-DD>` | Due-date filter |
| `--json` | Machine-readable output (**use for skill integration**) |
| `--no-header` | Drop the column header row |
| `--db=PATH` | Override DB path |

Default table columns: `UUID  TITLE  PROJECT  AREA  HEADING  STATUS  TRASHED`. The **UUID** is
the stable handle for `update`/`delete --id=`.

## Add commands (URL scheme — no token)

```
things add [OPTIONS...] [--] [-|TITLE]
things add-project [OPTIONS...] [TITLE]
things add-area    [OPTIONS...] [TITLE]
```

`-` as the title reads from STDIN; with multi-line STDIN the first line becomes the title and the
rest become notes (notes from STDIN take precedence over `--notes`).

| Flag | Meaning |
|---|---|
| `--notes=<text>` | Notes (≤10,000 chars) |
| `--when=DATE\|DATETIME` | Schedule: `today`, `tomorrow`, `evening`, `someday`, or a date/datetime |
| `--deadline=<DATE>` | Hard deadline |
| `--tags=TAG1[,TAG2,…]` | Assign tags |
| `--list=<title>` / `--list-id=<ID>` | Put into a project/area |
| `--heading=<text>` | Place under a project heading |
| `--checklist-item=<item>` | Add a checklist item (repeatable, ≤100) |
| `--completed` / `--canceled` | Create already-done/canceled (canceled wins) |
| `--creation-date` / `--completion-date` | ISO8601; ignored if in the future |
| `--repeat=day\|week\|month\|year` | Recurring (created via DB; needs a single explicit title) |
| `--repeat-every=N`, `--repeat-mode=schedule\|after-completion`, `--repeat-until`, `--repeat-clear` | Recurrence tuning |
| `--show-quick-entry` | Open the quick-entry dialog prepopulated instead of adding silently |

## Update commands (URL scheme — **token required**)

```
things update --id=<UUID> [OPTIONS...]
things update [FILTERS...] --yes [OPTIONS...]   # bulk update over a query
things update-project / update-area
```

Completing a todo is `update --completed` (there is no separate `complete` command).

| Flag | Meaning |
|---|---|
| `--auth-token=<token>` | Override `THINGS_AUTH_TOKEN` |
| `--id=<UUID>` | Target todo (required for single update) |
| `--completed` / `--canceled` | Mark done / canceled |
| `--when` / `--deadline` / `--heading` / `--list` | Reschedule / move (same semantics as `add`) |
| `--tags=…` (replace) / `--add-tags=…` (append) | Tag edits |
| `--notes=<text>` | Replace notes |
| `--yes` | Confirm a bulk (query-filtered) update |
| `--allow-unsafe-title` | Allow titles that look like `key=value` |

## Delete commands (AppleScript — Automation permission)

```
things delete --id=<UUID> --confirm=<UUID>     # non-interactive single
things delete <TITLE>                           # interactive (prompts)
things delete [FILTERS...] --confirm=delete --yes   # bulk over a query
things delete-project / delete-area
```

| Flag | Meaning |
|---|---|
| `--id=<UUID>` | Target todo |
| `--confirm=<ID\|title>` | Confirm a single delete non-interactively; `--confirm=delete` for query deletes |
| `--yes` | Confirm a bulk delete |

## Other

| Command | Purpose |
|---|---|
| `undo` | Undo the last bulk action |
| `rename-project` | Rename a project |
| `auth` | Show token status + setup help |
| `help [<command>]` | Documentation |

## Recipes

```bash
# Capture a quick task
things add "Renew passport" --when=someday --tags=admin

# Capture a task with context piped in (title + notes from a note body)
printf 'Follow up with Acme\nThey wanted the revised quote by Friday.\n' | things add -

# Today's actionable list as JSON for another skill
things today --json --no-header

# Find and complete a specific todo
things search "passport"            # grab the UUID from the output
things update --id=<UUID> --completed   # needs THINGS_AUTH_TOKEN

# Preview a bulk reschedule before committing
things tasks --tag=urgent --due-before=2026-06-10        # see what matches
things update --tag=urgent --due-before=2026-06-10 --when=today --yes   # then do it

# Safely preview a bulk delete
things delete --project="Old Project" --dry-run
```
