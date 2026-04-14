---
name: did
description: Review and manage did timesheets. Shows hours, submission status, and period summaries. Fixes timesheet issues via cal-cli (calendar is the source of truth). Use when the user asks about their timesheet, hours, did, time tracking, or wants to review/submit a period.
version: 1.0.0
author: damsleth
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Skill
tags:
  - timesheet
  - did
  - hours
  - time-tracking
---

# did Skill

Review and manage timesheets via `did-cli` and `cal-cli`.

## Architecture

```
Calendar (Outlook)  <-- cal-cli (read/write)
       |
       v
did (timesheet)     <-- did-cli (read-only view of calendar data)
```

- **did is read-only**. It reads calendar events and presents them as timesheet entries.
- **The calendar IS the timesheet**. To change hours, you change calendar events.
- **Categories are the bridge**. Event categories map to did projects/customers.
- **did-cli** at `/Users/damsleth/Code/CLI/did-cli/` - queries did's GraphQL API
- **cal-cli** at `/Users/damsleth/Code/CLI/cal-cli/` - reads/writes Outlook calendar

## Boot

On every invocation:

1. Check did-cli: `which did-cli`
2. Check cal-cli: `which cal-cli`
3. Quick auth check: `did-cli config` (verify DID_COOKIE is set)

If auth is broken, tell the user to update their cookie:
```bash
did-cli config --cookie "<value>"   # did session cookie
cal-cli config --token "<value>"    # Outlook JWT token
```

## Core workflow

The typical flow is: **review in did, fix in calendar**.

### 1. Review timesheet

```bash
# Current week
did-cli report --period current --pretty

# Last week
did-cli report --period last --pretty

# Specific week
did-cli report --week 15 --pretty

# Date range
did-cli report --from 2026-04-01 --to 2026-04-14 --pretty

# Filter by customer/project
did-cli report --customer "Skanska" --from 2026-01 --to 2026-03 --pretty

# Another employee
did-cli report --employee "Oistein Unnerud" --period current --pretty

# All employees
did-cli report --employee all --period current --pretty

# Status (time bank, vacation, current period)
did-cli status --pretty
```

### 2. Identify issues

Common problems to surface:

- **Missing categories**: events without a category are "uncategorized" in did
- **Wrong hours**: event duration doesn't match actual work
- **Missing time**: gaps in the workday with no events
- **Unsubmitted periods**: weeks that should be submitted but aren't

When reviewing, compare did hours against calendar events:
```bash
# did view of the week
did-cli report --week 16 --pretty

# Calendar view of the same week
cal-cli events --week 16 --pretty
```

### 3. Fix via calendar

Since did is read-only, all fixes go through cal-cli (or invoke the /calendar skill for complex changes):

```bash
# Add missing category
cal-cli update --id <event-id> --category "ProjectX"

# Fix event times
cal-cli update --id <event-id> --start 09:00 --end 11:00

# Create missing event
cal-cli create --subject "Deep work" --date 2026-04-14 --start 13:00 --end 15:00 --category "ProjectX"

# Delete duplicate
cal-cli delete --id <event-id>
```

For bulk calendar operations or complex changes, invoke the /calendar skill:
```
Use the Skill tool: skill: "calendar"
```

### 4. Submit period

Once the timesheet looks correct:
```bash
# Preview what will be submitted
did-cli report --period current --pretty

# Submit
did-cli submit --period current

# Submit without interactive prompt
did-cli submit --period current --confirm
```

## Default behavior

When the user invokes `/did` with no specific request:

1. Run boot checks
2. Show `did-cli status --pretty` (current period, time bank, vacation)
3. Show `did-cli report --period current --pretty` (this week's entries)
4. If period is not submitted and it's Thursday or later, nudge about submission

## Presentation

- Always use `--pretty` for user-facing output
- When showing both did and calendar data, clearly label which is which
- Round hours to 2 decimal places (did-cli already does this)
- When listing issues, be specific: "Monday has 0h logged" not "some days are missing"

## Comparing did and calendar

When the user asks to "review" or "check" their timesheet, do a side-by-side:

1. Fetch did report for the period
2. Fetch calendar events for the same date range
3. Compare and highlight:
   - Events in calendar but missing from did (category issue)
   - Hours mismatch between did and calendar
   - Uncategorized events
   - Days with suspiciously low hours (< 4h on a workday)

## Safety rules

1. **Never submit a period without explicit user confirmation**
2. **Calendar changes affect the timesheet** - always confirm before modifying events
3. **Don't modify other people's data** - did-cli can view other employees but can't change their calendars
4. **Warn before submitting periods with obvious issues** (0h days, uncategorized events)

## Quick reference

| Want to... | Command |
|---|---|
| See this week | `did-cli report --period current --pretty` |
| See last week | `did-cli report --period last --pretty` |
| Check status | `did-cli status --pretty` |
| Submit current week | `did-cli submit --period current` |
| See calendar for a day | `cal-cli events --date 2026-04-14 --pretty` |
| Fix a category | `cal-cli update --id <id> --category "Cat"` |
| List categories | `cal-cli categories` |
| Add missing event | `cal-cli create --subject "..." --date ... --start ... --end ... --category "..."` |
