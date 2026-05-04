---
name: cj-calendar
description: Manage Outlook/Microsoft 365 calendar events. Wraps owa-cal for listing, creating, updating, and deleting events. Auth is handled by owa-piggy. Use when the user asks about their calendar, schedule, meetings, or events.
version: 3.1.0
author: damsleth
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Glob
  - Grep
tags:
  - calendar
  - outlook
  - scheduling
---

# cj-calendar Skill

Manage the user's Outlook / Microsoft 365 calendar via `owa-cal`, which delegates auth to `owa-piggy`.

## Profiles

The user has multiple work accounts, each mapped to an `owa-piggy` profile. **Always infer the profile from context.**

| Profile   | Account / context                          |
|-----------|--------------------------------------------|
| `swon`    | SoftwareOne (default, `*`)                 |
| `crayon`  | Crayon / Norconsult work                   |
| `brkh`    | BRKH (Røde Kors volunteer role)            |
| `dno`     | dno (personal or other)                    |

Profile resolution rules:
- If the user says "my crayon calendar", "Norconsult schedule", "NOCOS meeting" -> `--profile crayon`
- If the user says "BRKH", "Røde Kors", "vaktgruppe" -> `--profile brkh`
- If the user says "SoftwareOne", "SWON", or no profile hint -> default (no flag needed, swon is `*`)
- When ambiguous and it matters, ask which calendar before running

Pass `--profile <alias>` as the **first** argument after `owa-cal`:

```bash
owa-cal --profile crayon events --pretty
owa-cal --profile brkh events --week 18 --pretty
owa-cal events --pretty                            # uses default (swon)
```

`--profile` overrides the config-pinned profile and `OWA_PROFILE` env var.

## Auth

`owa-cal` calls `owa-piggy` automatically on every command - no manual token handling needed unless something breaks.

```bash
owa-piggy status                                   # health of all profiles
owa-piggy remaining                                # minutes left on current token
owa-cal refresh                                    # force refresh, verify auth
owa-piggy reseed [--profile <alias>]               # recover from 24h hard-expiry (headless)
owa-piggy reseed --all                             # reseed every profile at once
owa-piggy setup --profile <alias> --email <addr>   # first-time or re-auth (opens Edge)
```

Token expiry has two rules:
- **Sliding 24h window** - rotates on every use; `owa-cal refresh` handles this
- **24h absolute hard-cap** (AADSTS700084) - run `owa-piggy reseed [--profile <alias>]`; if that fails, run `owa-piggy setup`

## Boot

On every invocation:

1. `which owa-cal` - verify it's on PATH
2. Infer profile from user's request (see Profiles table)
3. Proceed directly - owa-piggy handles auth transparently
4. If a command fails with a token error, run `owa-cal [--profile <alias>] refresh`; if that prints the 24h hard-expiry hint, run `owa-piggy reseed [--profile <alias>]`

## Commands

### List events

```bash
owa-cal [--profile <alias>] events --pretty                                    # today
owa-cal [--profile <alias>] events --date tomorrow --pretty
owa-cal [--profile <alias>] events --week 18 --pretty                          # ISO week
owa-cal [--profile <alias>] events --from 2026-04-14 --to 2026-04-18 --pretty
owa-cal [--profile <alias>] events --search "standup" --pretty
owa-cal [--profile <alias>] events --limit 100 --pretty                        # override default 50
```

Default output is JSON. `--pretty` gives a human-readable table.

### Create event

```bash
owa-cal [--profile <alias>] create --subject "lunsj" --start 11:00 --end 11:30 --category "CC LUNCH"
owa-cal [--profile <alias>] create --subject "Standup" --date tomorrow --start 09:00 --end 09:30
owa-cal [--profile <alias>] create --subject "Deep work" --start 13:00 --end 15:00 --showas busy
owa-cal [--profile <alias>] create --subject "Day off" --allday
```

Defaults: date=today, start=09:00, end=10:00, timezone=W. Europe Standard Time

### Update event

```bash
owa-cal [--profile <alias>] update --id <event-id> --subject "New title"
owa-cal [--profile <alias>] update --id <event-id> --category "ProjectX"
owa-cal [--profile <alias>] update --id <event-id> --start 14:00 --end 15:00
owa-cal [--profile <alias>] update --id <event-id> --date 2026-04-15
```

Partial updates are safe - only the supplied fields change.

### Delete event

```bash
owa-cal [--profile <alias>] delete --id <event-id>           # prompts for confirmation
owa-cal [--profile <alias>] delete --id <event-id> --confirm # skip prompt
```

### Categories

```bash
owa-cal [--profile <alias>] categories              # list all (JSON)
owa-cal [--profile <alias>] categories --pretty     # list all (table)
owa-cal [--profile <alias>] categories --add "NewCat"
```

### Config

```bash
owa-cal config                              # show config path and current settings
owa-cal config --profile <alias>            # pin a default owa-piggy profile
owa-cal config --app-client-id <id>         # set app registration client ID (optional)
```

## Categories and did

Categories link calendar events to billing projects. **Every work event should have a category.**

- Categories are a string array on each event: `["CC LUNCH"]`
- `did` reads categories to sort events into the correct project/customer
- Category names are **case-sensitive**
- Always ask for a category when creating work events if the user hasn't specified one
- Skip asking for non-work events (personal blocks, lunch) unless the user wants one

Modifying or deleting events affects timesheet data - confirm before bulk changes.

## Workday templates

Encoded conventions for translating high-level user intent into concrete event creation. When the user says "I'll work Tuesday and Thursday at Norconsult next week", expand it via the matching template and create the events on each date - do not ask for times/categories that the template already specifies. Always confirm the resolved dates and the event list before creating.

### Norconsult workday (`crayon` profile)

```
08:00-11:00  Norconsult     [NC NOCOS]
11:00-11:30  Lunsj          [CC LUNCH]
11:30-16:00  Norconsult     [NC NOCOS]
```

Triggers: "Norconsult day", "NC day", "jobbe på Norconsult", "Sandvika", "NOCOS-dag".

### SoftwareOne home day (`swon` profile, default)

```
08:00-11:00  SWON           [Intern]
11:00-11:30  Lunsj          [CC LUNCH]
11:30-16:00  SWON           [Intern]
```

Triggers: "SWON day", "home day", "jobbe hjemme for SWON", "regular work day".

### Day off / vacation

```
allday       Day off        [PTO]
```

Use `--allday` on `owa-cal create`. Triggers: "fri", "ferie", "day off", "PTO".

### BRKH vakt

Ad hoc - shifts vary. Ask for start/end and event type before creating. Profile: `brkh`. Default category: `Vakt`.

### Bulk-week pattern

When the user gives a week-shape ("Tuesday + Thursday at Norconsult, rest SWON, Friday off"), resolve each weekday to a date, pick the matching template per day, list the full plan back to the user, and create only after confirmation. Never silently create more than 5 events.

## Presentation

- Times in 24h format (09:00-10:00)
- Group by day for multi-day ranges
- Show: time, subject, location (if set), categories (if set)
- Compact table - not verbose JSON

```
2026-04-14
  09:00-10:00  Standup                       [Intern]
  10:00-11:30  Sprint planning               [ProjectX]
  11:00-11:30  lunsj                         [CC LUNCH]
  13:00-14:00  1:1 with Nina
```

## Safety rules

1. Never delete events without explicit user confirmation
2. Never bulk-modify more than 5 events without listing and getting approval
3. Warn if creating events in the past
4. Warn if creating overlapping events - check existing events first
5. Always verify dates - compute actual calendar dates from relative terms (`python3` or `date`)

## Error handling

| Error | Action |
|-------|--------|
| Token expired (sliding) | `owa-cal [--profile <alias>] refresh` |
| AADSTS700084 / 24h hard-expiry | `owa-piggy reseed [--profile <alias>]` |
| reseed fails | `owa-piggy setup --profile <alias> --email <addr>` |
| 401/403 | `owa-piggy status` + `owa-cal config` |
| 404 | Wrong event ID |
| 429 | Rate limited - wait and retry |
