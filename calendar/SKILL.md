---
name: calendar
description: Manage Outlook/Microsoft 365 calendar events. Wraps cal-cli for listing, creating, updating, and deleting events. Supports JWT, cookie, and OAuth auth. Use when the user asks about their calendar, schedule, meetings, or events.
version: 2.1.0
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

# Calendar Skill

Manage the user's Outlook / Microsoft 365 calendar. Wraps `cal-cli` (on PATH).

## Architecture

```
/calendar skill  -->  cal-cli  -->  Outlook REST API v2.0
                                    Microsoft Graph v1.0 (OAuth mode)
```

- **CLI**: `cal-cli` (must be on PATH)
- **Auth** (tried in order):
  1. **JWT token** from Outlook Web - grab from DevTools, ~65 min lifetime, full permissions
  2. **OAuth** via `get-token` CLI - automated flow, requires Calendars.ReadWrite scope
  3. **Cookie** - full Cookie header from DevTools, longer-lived but messier
- **Token refresh**: `cal-cli refresh` uses CDP (Chrome DevTools Protocol) to capture a fresh token from the running browser without user interaction. Requires browser started with `cal-cli setup` (one-time).
- **Config**: `.env` in cal-cli's install directory (see `cal-cli config` for the resolved path)

## Categories

Categories are the bridge between the calendar and did. **Every work event should have a category** - it determines which project/customer the time gets billed to.

- Categories are a string array on each event: `["CC LUNCH"]`
- did reads categories to sort events into the correct project/customer
- An event without a category is "uncategorized" in did
- Category names are **case-sensitive** and must match what did expects
- List available categories: `cal-cli categories`
- **Always ask for a category** when creating work events if the user hasn't specified one
- Don't ask for non-work events (lunch, personal blocks) unless the user has a category for them

## did awareness

did reads directly from this calendar - **the calendar IS the timesheet**:

- Event categories map to did projects/customers
- Modifying or deleting events affects timesheet data
- Always confirm before bulk updates or deletions
- The did CLI (`did-cli`) is the companion tool for timesheet review

## Boot

On every invocation:

1. Verify cal-cli is available: `which cal-cli`
2. Check auth status: `cal-cli config`
3. If token is expired, try `cal-cli refresh` first (headless CDP refresh, no UI needed)
4. If refresh fails (no CDP), fall back to `cal-cli login` (interactive, reads clipboard)

## Usage

### Auth / Token management

```bash
cal-cli login               # Interactive: grabs JWT from clipboard or prompts for paste
cal-cli setup               # One-time: restart browser with remote debugging (CDP port 9222)
cal-cli refresh             # Headless: capture fresh token via CDP (no UI)
```

Typical flow when token expires:
1. Try `cal-cli refresh` - works if browser was started with `cal-cli setup`
2. If no CDP available, use `cal-cli login` - opens Outlook, reads clipboard

### List events

```bash
cal-cli events --pretty                          # today
cal-cli events --date tomorrow --pretty          # tomorrow
cal-cli events --week 16 --pretty                # ISO week 16
cal-cli events --from 2026-04-14 --to 2026-04-18 --pretty  # date range
cal-cli events --search "standup" --pretty       # search by subject
```

Default output is JSON (pipe-friendly). Add `--pretty` for human-readable tables.

### Create event

```bash
cal-cli create --subject "lunsj" --start 11:00 --end 11:30 --category "CC LUNCH"
cal-cli create --subject "Standup" --date tomorrow --start 09:00 --end 09:30
cal-cli create --subject "Deep work" --start 13:00 --end 15:00 --showas busy
```

Defaults: date=today, start=09:00, end=10:00, timezone=W. Europe Standard Time

### Update event

```bash
cal-cli update --id <event-id> --subject "New title"
cal-cli update --id <event-id> --category "ProjectX"
cal-cli update --id <event-id> --start 14:00 --end 15:00
cal-cli update --id <event-id> --date 2026-04-15   # moves to new date, keeps times
```

Update is smart about partial changes - changing just date, just start time, or just end time preserves the other components from the existing event.

### Delete event

```bash
cal-cli delete --id <event-id>           # interactive confirm
cal-cli delete --id <event-id> --confirm # skip confirmation
```

### Categories

```bash
cal-cli categories              # list all
cal-cli categories --add "NewCat"  # add new
```

### Config

```bash
cal-cli config                              # show current
cal-cli config --token "eyJ..."             # set JWT
cal-cli config --cookie "ClientId=...; ..." # set cookie
cal-cli config --oauth 1                    # enable OAuth
```

## Presentation

When showing events to the user (from `--pretty` output or your own formatting):

- Format times in 24h format (e.g. 09:00-10:00)
- Group by day if spanning multiple days
- Show: time, subject, location (if set), categories (if set)
- Compact table or list - not verbose JSON

Example:

```
2026-04-14
  09:00-10:00  Standup                       [Intern]
  10:00-11:30  Sprint planning               [ProjectX]
  11:00-11:30  lunsj                         [CC LUNCH]
  13:00-14:00  1:1 with Nina
```

## Safety rules

1. **Never delete events without explicit user confirmation**
2. **Never bulk-modify more than 5 events** without listing and getting approval
3. **Warn if creating events in the past**
4. **Warn if creating overlapping events** - check existing events first
5. **Remember did**: modifications affect the timesheet
6. **Always verify dates** - when creating events for "this week" or similar relative ranges, compute the actual calendar dates first (use `python3` or `date` to confirm day-of-week). Never assume date-to-weekday mappings.

## Workflow

When the user invokes `/calendar`:

1. Run boot (check cal-cli, check auth)
2. If no specific request, show today's events
3. For modifications, show what will change before applying
4. After creating/updating, show the result
5. For batch operations, list all changes and confirm before executing

## Error handling

- **Token expired**: Run `cal-cli refresh` first. If that fails, fall back to `cal-cli login`
- **401/403**: Auth issue, check `cal-cli config`
- **404**: Wrong event ID
- **429**: Rate limited, wait and retry
