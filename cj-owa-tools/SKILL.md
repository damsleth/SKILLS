---
name: cj-owa-tools
description: Drive the Outlook / Microsoft 365 CLI suite (owa-cal, owa-mail, owa-graph, owa-doctor, owa-people, owa-sched, owa-drive) and the owa-piggy auth broker. Use when the user asks about their calendar, mail, Microsoft Graph, OneDrive, free/busy scheduling, directory or people lookups, or any owa-* command. Source of truth for the profile model, audiences, and auth troubleshooting referenced by cj-meeting-notes, cj-did, and cj-weekly-review.
version: 1.0.0
author: damsleth
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Glob
  - Grep
tags:
  - outlook
  - microsoft365
  - calendar
  - mail
  - graph
  - onedrive
  - scheduling
  - owa
---

# cj-owa-tools Skill

Single reference for the `owa-tools` CLI suite plus the `owa-piggy` auth
broker. Use this skill directly when the user wants to do something with
their calendar, mail, Microsoft Graph, OneDrive, free/busy scheduling, or
directory data. Other skills (`cj-meeting-notes`, `cj-did`,
`cj-weekly-review`, `cj-timereg`) defer their profile / auth / install
guidance to this skill - update those policies here, not in the workflow
skills.

## Boot

On every invocation:

```bash
which owa && which owa-piggy
```

If either is missing, the install is broken. One-liner fix:

```bash
brew install damsleth/tap/owa-piggy damsleth/tap/owa-tools
```

That gives you eight binaries (`owa`, `owa-cal`, `owa-mail`, `owa-graph`,
`owa-doctor`, `owa-people`, `owa-sched`, `owa-drive`) plus the `owa-piggy`
auth broker, all reporting one suite version. PyPI alternative:
`pipx install owa-piggy && pipx install owa-tools`.

## Profiles

The user has multiple work accounts, each mapped to an `owa-piggy` profile.
**Always infer the profile from context.**

| Profile  | Account / context                       |
|----------|-----------------------------------------|
| `swon`   | SoftwareOne (default, `*`)              |
| `crayon` | Crayon / Norconsult work                |
| `brkh`   | BRKH (Røde Kors volunteer role)         |
| `dno`    | dno (personal or other)                 |

Inference rules:

- "my crayon calendar", "Norconsult", "NOCOS", "Sandvika" -> `--profile crayon`
- "BRKH", "Røde Kors", "vaktgruppe", "korpsleder" -> `--profile brkh`
- "SoftwareOne", "SWON", or no profile hint -> default (swon, no flag)
- "dno", "personal" -> `--profile dno`
- Ambiguous and it matters? Ask which account before running.

`--profile <alias>` goes as the **first** argument after the binary, before
the subcommand:

```bash
owa-cal --profile crayon events --pretty
owa-mail --profile brkh messages --unread --pretty
owa-graph --profile crayon GET /me
```

Precedence (highest first): `--profile` flag > `OWA_PROFILE` env >
config-pinned `owa_piggy_profile` > `owa-piggy`'s default profile.

To pin a tool to a profile permanently:

```bash
owa-cal config --profile crayon          # any tool that has `config --profile`
```

## Auth via owa-piggy

Every consumer tool shells out to `owa-piggy` for a fresh access token on
every call. `owa-piggy` owns the refresh token; the consumer tools store
nothing more than an optional profile alias.

```bash
owa-piggy status                                   # all profiles, ISO8601 health
owa-piggy status --profile crayon                  # one profile
owa-piggy remaining                                # minutes left on current token
owa-piggy reseed [--profile <alias>]               # recover from 24h hard-expiry (headless Edge)
owa-piggy reseed --all                             # reseed every profile in one go
owa-piggy setup --profile <alias> --email <addr>   # first-time or full re-auth (opens Edge)
```

Refresh tokens have two expiry rules:

- **Sliding 24h window** - rotates on every use. Any consumer's `refresh`
  command handles this (`owa-cal refresh`, `owa-mail refresh`, etc.).
- **24h absolute hard-cap** (AADSTS700084) - the refresh token dies 24h after
  the original sign-in, regardless of activity. Recover with
  `owa-piggy reseed [--profile <alias>]`. If reseed fails, fall back to
  `owa-piggy setup --profile <alias> --email <addr>`.

## Audiences

Each consumer targets one of two audiences. Same profile, different scope:

- `outlook` -> Outlook REST. Used by `owa-cal`, `owa-mail`.
- `graph` -> Microsoft Graph. Used by `owa-graph`, `owa-people`, `owa-sched`,
  `owa-drive`, parts of `owa-doctor`.

The token cache is keyed on `(profile, audience)`, so switching tools inside
one profile does not re-prompt for consent.

The OWA first-party SPA client `owa-piggy` borrows does **not** carry full
Graph scopes for mail/calendar/contacts. Reads on `/me`, `/users`,
`/me/joinedTeams`, `/groups`, `/planner`, `/me/drive` work via Graph; for
mail and calendar use the audience-specific siblings (`owa-cal`, `owa-mail`)
which target the Outlook REST audience.

---

# Per-tool reference

## owa-cal (Outlook calendar CRUD)

```bash
# Read
owa-cal [--profile <alias>] events --pretty                                  # today
owa-cal events --date tomorrow --pretty
owa-cal events --week 18 --year 2026 --pretty
owa-cal events --from 2026-04-14 --to 2026-04-18 --pretty
owa-cal events --search "standup" --pretty
owa-cal events --limit 100 --pretty                                          # default 50

# Create
owa-cal create --subject "lunsj" --start 11:00 --end 11:30 --category "CC LUNCH"
owa-cal create --subject "Deep work" --date tomorrow --start 13:00 --end 15:00 --showas busy
owa-cal create --subject "Day off" --allday

# Update (partial, only supplied fields change)
owa-cal update --id <event-id> --subject "New title"
owa-cal update --id <event-id> --category "ProjectX"
owa-cal update --id <event-id> --start 14:00 --end 15:00

# Delete
owa-cal delete --id <event-id>                                               # prompts
owa-cal delete --id <event-id> --confirm                                     # no prompt

# Categories
owa-cal categories                       # list (JSON)
owa-cal categories --pretty
owa-cal categories --add "NewCat"

# Profiles (combined owa-cal local + owa-piggy)
owa-cal profiles --pretty
owa-cal profiles add brkh --webcal "https://example.invalid/feed?key=..."
owa-cal profiles delete <alias>

# Config
owa-cal config                           # show current settings
owa-cal config --profile crayon          # pin owa_piggy_profile
```

Defaults for `create`: date=today, start=09:00, end=10:00, timezone=W. Europe
Standard Time.

### Categories and did

Categories link calendar events to billing projects. **Every work event
should have a category.** Categories are a string array on each event
(`["CC LUNCH"]`). did reads categories to sort events into the correct
project/customer. Category names are **case-sensitive**.

- Always ask for a category when creating work events if the user has not
  specified one.
- Skip asking for non-work events (personal blocks, lunch) unless the user
  wants one.

### Workday templates

Encoded conventions for translating high-level user intent into concrete
event creation. When the user says "I'll work Tuesday and Thursday at
Norconsult next week", expand it via the matching template and create the
events on each date - do not ask for times/categories that the template
already specifies. Always confirm the resolved dates and the event list
before creating.

**Norconsult workday** (`crayon` profile):

```
08:00-11:00  Norconsult     [NC NOCOS]
11:00-11:30  Lunsj          [CC LUNCH]
11:30-16:00  Norconsult     [NC NOCOS]
```

Triggers: "Norconsult day", "NC day", "jobbe på Norconsult", "Sandvika",
"NOCOS-dag".

**SoftwareOne home day** (`swon` profile, default):

```
08:00-11:00  SWON           [Intern]
11:00-11:30  Lunsj          [CC LUNCH]
11:30-16:00  SWON           [Intern]
```

Triggers: "SWON day", "home day", "jobbe hjemme for SWON", "regular work day".

**Day off / vacation**:

```
allday       Day off        [PTO]
```

Use `--allday` on `owa-cal create`. Triggers: "fri", "ferie", "day off", "PTO".

**BRKH vakt**: ad hoc, shifts vary. Ask for start/end and event type before
creating. Profile: `brkh`. Default category: `Vakt`.

**Bulk-week pattern**: when the user gives a week-shape ("Tuesday + Thursday
at Norconsult, rest SWON, Friday off"), resolve each weekday to a date, pick
the matching template per day, list the full plan back to the user, and
create only after confirmation. Never silently create more than 5 events.

## owa-mail (Outlook mail)

```bash
# Read
owa-mail messages --pretty                                                   # Inbox, last 25
owa-mail messages --unread --limit 10 --pretty
owa-mail messages --folder SentItems --since 2026-04-01 --pretty
owa-mail messages --from "nina" --subject "ferie" --pretty
owa-mail messages --search 'subject:"Q1 plan" AND from:"alice"' --pretty
owa-mail folders --pretty
owa-mail show --id <message-id> --pretty                                     # header block + body

# Compose
owa-mail send --to a@example.com --subject "hi" --body "hello"
owa-mail send --to a@example.com,b@example.com --cc c@example.com --subject "x" --body -   # stdin
owa-mail send --to a@example.com --subject "later" --body "..." --send-at 2026-05-01T09:00:00Z
owa-mail send --to a@example.com --subject "draft" --body "..." --save-draft
owa-mail send --to a@example.com --subject "html" --body "<p>hi</p>" --html

# Reply / forward
owa-mail reply --id <message-id> --body "thanks"
owa-mail reply-all --id <message-id> --body "all of us"
owa-mail forward --id <message-id> --to b@example.com --body "fyi"

# Manage
owa-mail mark --id <message-id> --read                                       # also --unread / --flag / --unflag
owa-mail move --id <message-id> --to Archive
owa-mail delete --id <message-id> --confirm
```

Folder names accept well-known shortcuts (`Inbox`, `Drafts`, `SentItems`,
`DeletedItems`, `Junk`, `Archive`) or folder IDs.

`--search` is mutually exclusive with `--from`/`--subject`/`--unread`
filters - it goes straight to Outlook KQL.

## owa-graph (Microsoft Graph)

Verb-first for arbitrary endpoints, or one of 14 resource shortcut groups.

```bash
# Verb-first
owa-graph GET /me --pretty
owa-graph GET '/users?$top=5' --pretty
owa-graph GET /users --search 'displayName:Bob' --count
owa-graph GET /me/messages --top 10 --select id,subject,from
owa-graph POST /me/sendMail --body @mail.json
owa-graph PATCH /me/messages/<id> --body '{"isRead":true}'

# Shortcut groups (run `owa-graph <group>` for the menu)
owa-graph me whoami
owa-graph users find "ola"
owa-graph teams list
owa-graph chats list
owa-graph presence get
owa-graph files ls
owa-graph groups list

# Common flags
--all                  Follow @odata.nextLink until exhausted
--ndjson               One item per line (jq-friendly; pairs with --all)
--select F1,F2         Shortcut for $select
--top N                Shortcut for $top
--filter EXPR          Shortcut for $filter
--count                Shortcut for $count=true (sets ConsistencyLevel: eventual)
--search EXPR          Shortcut for $search="EXPR"
--beta                 Use the beta graph endpoint
--audience <name>      Forward to owa-piggy. Default: graph
--curl                 Print equivalent curl and exit
--az                   Print equivalent `az rest` and exit
```

Resource groups: `me`, `mail`, `calendar`, `files`, `users`, `teams`,
`chats`, `presence`, `contacts`, `groups`, `planner`, `todo`, `sites`,
`directory`.

Scope caveat: mail/calendar/contacts/todo/sites/presence shortcuts return
403 on the OWA SPA scope. Use `owa-cal` / `owa-mail` for those domains
instead, or pass `--audience outlook` where it applies.

## owa-people (directory + contacts)

```bash
owa-people find "vibeke" --pretty               # recently-interacted ranked (/me/people)
owa-people show vtv@une.no                       # full details
owa-people directory "norconsult" --limit 50 --pretty   # company directory (/users)
owa-people me --pretty                           # the authenticated user (/me)
owa-people contacts                              # your personal contacts (/me/contacts)
owa-people --profile crayon find "ole kristian"
```

`find` searches the user's interaction graph (best for "who do I know
called X"). `directory` searches the whole tenant (best for "find anyone
named X at Y").

## owa-sched (free/busy + slot finding)

```bash
owa-sched availability --who alice@x.com,bob@x.com --week 19 --pretty
owa-sched availability --who vibeke@une.no --date tomorrow --pretty
owa-sched availability --who you@yourcompany.com --from 2026-05-12 --to 2026-05-14 --pretty
owa-sched find-time --who alice@x.com,bob@x.com --duration 30 --week 19 --pretty
owa-sched find-time --who ole@example.com --date 2026-05-12 --duration 60 --pretty
```

Flag is `--who` (not `--emails`). Defaults: working window 09:00-17:00,
slot length 30min, 30min `availabilityView` granularity. Use `--start`
and `--end` to widen / narrow the working window.

If the user wants to check their own availability, include their email in
`--who` explicitly - the CLI does not auto-include the caller.

## owa-drive (OneDrive CRUD)

```bash
owa-drive ls --pretty                            # drive root
owa-drive ls "/Documents" --pretty
owa-drive show "/Documents/Q1 plan.docx" --pretty
owa-drive get "/Documents/foo.txt" --out ./foo.txt
owa-drive get "/Documents/foo.txt" | jq .        # if it is JSON
owa-drive put ./foo.txt "/Documents/foo.txt"
cat ./report.md | owa-drive put - "/Documents/report.md"
owa-drive rm "/Documents/old.txt" --confirm
```

**Upload limit:** `put` is small-file only (< 4MB). Larger files need the
chunked Graph upload session, which is not implemented in this CLI yet -
fall back to `owa-graph` raw calls if you need it.

`rm` requires `--confirm`. There is no undo.

---

# Pointer tools

## owa-doctor

```bash
owa doctor                          # default: full probe across all profiles, audience=graph
owa doctor --pretty                 # human-readable table
owa doctor --profile swon --pretty  # one profile
owa doctor --audience outlook       # check Outlook REST instead of Graph
owa doctor --no-tokens              # only check installs + versions (no auth)
```

Exit codes: 0 ok, 1 near-expiry (< 10min on one or more profiles), 2 fail.

## owa (umbrella)

Thin discovery binary. Subcommands:

- `owa list` - JSON list of installed consumer CLIs and versions
- `owa schema [--tool <name>]` - aggregate `<tool> schema` output
- `owa doctor [...]` - forwards to `owa-doctor probe`
- `owa version` - umbrella version

---

# Cross-tool patterns

These tie multiple binaries together for things no single tool does on its
own. Use them as recipes; the individual command surfaces are above.

**Look up someone, then mail them.**

```bash
addr=$(owa-people directory "ola nordmann" --limit 1 | jq -r '.[0].mail')
owa-mail send --to "$addr" --subject "kort spørsmål" --body "Hei Ola, ..."
```

**Check availability, then create a meeting.**

```bash
owa-sched find-time --who alice@x.com,bob@x.com --duration 30 --date tomorrow --pretty
# pick a slot, then:
owa-cal create --subject "Sync" --date tomorrow --start 10:00 --end 10:30 \
  --category "Sync" --body "Agenda: ..."
```

**Audit a profile end-to-end.**

```bash
owa-piggy status --profile crayon
owa doctor --profile crayon --pretty
owa-cal --profile crayon events --pretty
```

---

# Error handling

| Error                         | Action                                            |
|-------------------------------|---------------------------------------------------|
| Token expired (sliding 24h)   | `<tool> refresh` (owa-cal refresh, owa-mail refresh, ...) |
| AADSTS700084 / 24h hard-cap   | `owa-piggy reseed [--profile <alias>]`            |
| reseed fails                  | `owa-piggy setup --profile <alias> --email <addr>` |
| 401 / 403                     | `owa-piggy status` + `<tool> config`              |
| 404                           | Wrong event/message/path ID                       |
| 429                           | Rate limited - wait and retry. Most tools support `--retry`. |
| Mail/cal 403 via owa-graph    | Wrong audience - use owa-cal or owa-mail instead, or `owa-graph --audience outlook`. |

---

# Safety rules

1. Never delete events, messages, or drive items without explicit user
   confirmation.
2. Never bulk-modify more than 5 events / messages without listing them
   first and getting approval.
3. Warn if creating events in the past.
4. Warn if creating overlapping events - check existing events first.
5. Always verify dates - compute actual calendar dates from relative
   terms (`python3 -c 'from datetime import...'`  or `date`).
6. Categories on work events: ask before creating an uncategorised one.
   See Categories and did above for why.
7. `owa-drive rm` and `owa-mail delete` are not undoable. `owa-cal delete`
   sends to Deleted Items first but bulk operations still need approval.

---

# Adjacent skills

These skills use `owa-tools` for their workflow and defer profile / auth
/ install policy to this file:

- `cj-meeting-notes` - meeting prep, note-taking, summary. Uses `owa-cal`
  for calendar lookup.
- `cj-did` - timesheet review and fixes. Uses `owa-cal` to edit events
  (the source of truth for did hours).
- `cj-weekly-review` - weekly brief combining Things3, calendar, did,
  and the cognitive ledger. Uses `owa-cal` across profiles.
- `cj-timereg` - sync did hours into timereg.inmeta.com. Reads calendar
  data only transitively (via did).

If you change profile rules, auth troubleshooting, or installation
guidance, change them here. Do not re-introduce them in the workflow
skills.
