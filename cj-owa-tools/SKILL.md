---
name: cj-owa-tools
description: Drive the Outlook / Microsoft 365 CLI suite (owa-cal, owa-mail, owa-graph, owa-doctor, owa-people, owa-sched, owa-drive, owa-teams, owa-planner, owa-todo, owa-sites, owa-vids, owa-swodp) and the owa-piggy auth broker. Use when the user asks about their calendar, mail, Microsoft Graph, OneDrive, Teams chats/channels, Planner, Microsoft To Do, SharePoint, ServiceNow timesheets, meeting-recording downloads, free/busy scheduling, directory or people lookups, or any owa-* command. Source of truth for the install requirements, profile model, audiences, and auth troubleshooting that other owa-based skills reference.
---

# cj-owa-tools

Judgment layer for the `owa-tools` CLI suite and the `owa-piggy` auth broker.
Command syntax lives in each CLI: `<tool> --help` (or `owa <tool> --help`) is
always current, and `<tool> schema` gives the same as JSON. This file holds
what the help text cannot tell you: which profile to use, how auth breaks, and
what is safe to mutate.

Other skills built on the suite (`cj-meetings`, `cj-now`, ...) defer install,
profile and auth policy to this file. Change that policy here.

## Local overlay

If `~/.config/cj-skills/cj-owa-tools.md` exists, read it before acting. It holds this user's own profiles, paths and conventions, and it wins over the defaults here.

## Requirements

The skill needs two things on PATH: `owa-piggy` (the token broker) and
`owa-tools` (`owa`, `owa-cal`, `owa-mail`, `owa-graph`, ...). On first use in a
session, check:

```bash
command -v owa-piggy owa-cal
```

If either is missing, tell the user and suggest one of:

```bash
brew install damsleth/tap/owa-tools                    # brings owa-piggy along
curl -fsSL https://owa-piggy.dv.ms/install.sh | bash   # without Homebrew
```

Then create a profile, which opens Edge for a normal sign-in:

```bash
owa-piggy setup --profile <name> --email <address>
```

`owa list` confirms which consumer CLIs are installed and their suite version.
`owa-tui` (an interactive terminal client over the suite) is optional; the
skill never needs it.

## Language

Mirror the trigger language. Event subjects and bodies, mail drafts and your
own replies follow the language the user invoked the skill with. When replying
to or forwarding an existing message, match that thread's language. When the
trigger language is ambiguous, default to Norwegian (Bokmål) unless the overlay
names another, and stay in it until the user switches. CLI flags, profile
aliases and category names stay in their canonical form.

## Profiles

Each work account is one `owa-piggy` profile. Run `owa-piggy profiles list` (or
`owa-piggy status`) to see this user's profiles and which is the default (`*`).

### Read: default to `-A`

For every read or lookup, fan out across all active profiles instead of
guessing one. Profile inference is what silently loses data.

```bash
owa-cal    -A events --date today
owa-mail   -A messages --unread --pretty
owa-people -A find "<name>"
```

`-A` (aliases `--all-profiles`, `--profile all`) always returns the merged,
profile-keyed shape, even for a single profile:

```json
{"_owa": {"profiles": ["<a>", "<b>"]},
 "results": [{"profile": "<a>", "ok": true, "data": [...]}, ...]}
```

`--pretty` prints one `=== profile: <alias> ===` section per profile;
`--ndjson` tags each line. Filter on non-empty `results[].data` rather than
reasoning about which account should have the answer.

Exit codes under fan-out: `0` all ok, `2` some ok, `1` all failed. On `2`,
read the per-profile `ok` / `error` fields and use the good data. Profiles are
isolated, so one failure never aborts the others.

Narrow to `--profile <alias>` only when the user names an account, or when a
single mailbox genuinely is the subject.

### Write and auth: one explicit profile

Anything that sends, creates, changes or authenticates runs on exactly one
named profile. (`-A` on a send means one message from every account.)

```bash
owa-mail --profile <profile> send --to <...> --subject "<...>" --body -
owa-cal  --profile <profile> create --subject "<...>" --date <d>
owa-cal  config --profile <profile>          # pins owa_piggy_profile
```

`--profile <alias>` goes first, before the subcommand. Precedence, highest
first: `--profile` / `-A` > `OWA_PROFILE` env > config-pinned
`owa_piggy_profile` > `owa-piggy`'s default. `OWA_PROFILE` is single-valued
and never fans out. `all` is reserved and cannot be a profile name.

Run these once per `--profile`, since they cannot fan out: `tui`, and
binary-output commands (`owa-drive get`, `owa-vids get`). `owa-doctor` already
probes every profile; it takes `--profile` to narrow.

## Auth via owa-piggy

Every consumer tool asks `owa-piggy` for a fresh access token on every call.
`owa-piggy` owns the refresh token; the consumer tools store at most a profile
alias.

```bash
owa-piggy status [--profile <p>] [--json]   # health per profile
owa-piggy reseed [--profile <p> | --all]    # headless recovery via the Edge sidecar
owa-piggy setup --profile <p> --email <a>   # first-time or full re-auth (opens Edge)
```

`owa-piggy tui` (same screen as bare `owa-piggy profiles` on a TTY) is the
interactive dashboard with live token freshness. Use it for a human check;
from automation use `status --json` or `profiles list`.

Refresh tokens die two ways:

- **Sliding 24h window**: rotates on every use. Any consumer's `refresh`
  (`owa-cal refresh`, `owa-mail refresh`, ...) handles it.
- **24h absolute hard cap** (AADSTS700084): the token dies 24h after the
  original sign-in regardless of activity. Recover with `owa-piggy reseed`;
  if that fails, `owa-piggy setup --profile <p> --email <a>`.

## Audiences

Same profile, different token scope. The cache is keyed on
`(profile, audience)`, so switching tools inside one profile never re-prompts.

- `outlook` (Outlook REST): `owa-cal`, `owa-mail`, `owa-todo`.
- `graph` (Microsoft Graph): `owa-graph`, `owa-people`, `owa-sched`,
  `owa-drive`, `owa-teams` enumeration, `owa-planner`, parts of `owa-doctor`.
- `owa-piggy audiences` lists the rest (e.g. `devops` for `owa-ado`).

The borrowed OWA client does **not** carry full Graph scopes for mail,
calendar, contacts, To Do, sites or presence: those `owa-graph` shortcuts 403.
Use `owa-cal` / `owa-mail`, or `owa-graph --audience outlook` where it applies.

---

# Per-tool notes

Syntax: `<tool> --help`. Below is only what the help leaves out.

- **owa-cal**: `create` defaults to today, 09:00-10:00, W. Europe Standard
  Time. Category names are case-sensitive; `owa-cal categories` lists them.
  Categories link events to billing projects, which timesheet matching
  (`owa-swodp`) relies on: give every work event one, and ask when the user
  has not. Non-work events (personal blocks, lunch) need one only when the
  user wants it.
- **owa-mail**: folder shortcuts `Inbox`, `Drafts`, `SentItems`,
  `DeletedItems`, `Junk`, `Archive`, or a folder id. `--search` is raw Outlook
  KQL.
- **owa-graph**: verb-first for any endpoint (`owa-graph GET /me`), or a
  shortcut group (`owa-graph <group>` prints the menu). `--all --ndjson` pages
  and streams; `--curl` / `--az` print the equivalent call instead of running it.
- **owa-people**: `find` ranks people the user has interacted with ("who do I
  know called X"); `directory` searches the whole tenant ("anyone named X at
  Y"). Fan `find` out with `-A`, since you rarely know which tenant knows them.
- **owa-sched**: `--who` does not add the caller. To check the user's own
  availability, include their address explicitly.
- **owa-teams**: enumeration uses Graph, message bodies use an ic3 token
  against a regional chat service (default `emea`; pin with
  `owa-teams config --region`). Channel `members` is scope-walled (exit 12);
  chat members work.
- **owa-planner**: read-only.
- **owa-todo**: full CRUD on Microsoft To Do. Use it only for tasks that must
  live in To Do (shared or work flows). When Things 3 (cj-things) is installed
  it is the primary task system and `now` (cj-now) the read across it; `now`
  does not read To Do, so a personal task filed there drops out of view.
- **owa-sites**: site = bare name, path (`sites/x`, `teams/x`), full URL, or
  omitted for the tenant root. Mints a SharePoint-resource token; the host
  auto-discovers unless pinned with `owa-sites config --host`. `search --q` is
  tenant-wide search. The best lever for SharePoint-heavy (SPFx) work.
- **owa-vids**: `<source>` is the pasted recording URL (Stream page, copy-link
  or videomanifest; kind auto-detected). `get` needs `ffmpeg` on PATH. Pairs
  with `cj-meetings` recap (download, transcribe, summarize) and
  `cj-video-vision` (frame analysis).
- **owa-swodp**: ServiceNow timesheet data layer; calendar input comes from
  `owa-cal`, matching is workflow logic. It authenticates through its own Edge
  sidecar per `--instance prod|uat`, not `owa-piggy`; if `status` fails, run
  `setup` for that instance. Writes touch only Pending cards and need
  `--confirm`; a write aimed at a Submitted, Approved or Processed card exits
  15 and leaves it untouched. Prefer `--instance uat`. A production write
  needs explicit authorization plus snapshot, one reviewed row, verify,
  restore. Take every snapshot or verification read from the bare binary:
  output routed through `rtk proxy` or the rtk hook has dropped rows and
  rewritten `Approved` to `Submitted` on a `cards` read, so never gate a
  decision on it.
- **owa-doctor** / **owa doctor**: exit `0` ok, `1` a token near expiry
  (< 10 min), `2` fail. `--no-tokens` checks installs only.

---

# Cross-tool patterns

**Look up someone, then mail them.**

```bash
addr=$(owa-people directory "<name>" --limit 1 | jq -r '.[0].mail')
owa-mail --profile <profile> send --to "$addr" --subject "<...>" --body "<...>"
```

**Find a slot, then book it.**

```bash
owa-sched --profile <profile> find-time --who a@x.com,b@x.com,<me> --duration 30 --date tomorrow --pretty
owa-cal   --profile <profile> create --subject "<...>" --date tomorrow --start 10:00 --end 10:30 --category "<cat>"
```

**Expand a workday template.** The overlay may define workday templates: a
name, trigger phrases, a profile, and time blocks with categories, e.g.

```
08:00-11:00  <Client>  [<category>]
11:00-11:30  Lunch     [<lunch category>]
11:30-16:00  <Client>  [<category>]
```

A day off is `owa-cal create --allday` with a `PTO`-style category. When the
user's intent matches a template, create its events on each date without
asking for the times and categories it already specifies. For a week-shape
("Tuesday and Thursday at the client, Friday off"), resolve each weekday to a
date and pick one template per day. Either way, list the resolved dates and
events back and create only after confirmation.

**Audit one profile end to end.**

```bash
owa-piggy status --profile <profile>
owa doctor --profile <profile> --pretty
owa-cal -A events --pretty
```

---

# Error handling

| Error | Action |
|---|---|
| Token expired (sliding 24h) | `<tool> refresh` |
| AADSTS700084 / 24h hard cap | `owa-piggy reseed [--profile <p>]` |
| reseed fails | `owa-piggy setup --profile <p> --email <a>` |
| 401 / 403 | `owa-piggy status` + `<tool> config` |
| Mail/calendar 403 via owa-graph | Wrong audience: use `owa-cal` / `owa-mail`, or `--audience outlook` |
| 404 | Wrong event / message / path id |
| 429 | Rate limited: wait and retry (`owa-graph` takes `--retry`) |

---

# Safety rules

1. Delete events, messages or drive items only after explicit user
   confirmation. `owa-drive rm` and `owa-mail delete` have no undo;
   `owa-cal delete` goes to Deleted Items.
2. Before touching more than 5 events or messages, list them and get approval.
3. Compute actual dates from relative terms (`date`, or Python `datetime`)
   and show them back before creating.
4. Warn before creating an event in the past or one that overlaps an existing
   event (read the day first).
5. Every send / create / update / delete runs on one explicit `--profile`.
