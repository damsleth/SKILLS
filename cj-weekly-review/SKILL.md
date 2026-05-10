---
name: cj-weekly-review
description: Structured weekly planning and review ritual. Combines Things3 tasks, Outlook calendar (multiple profiles), did timesheet status, and cognitive ledger open loops into one coherent picture. Use when the user asks to plan their week, review their week, "what's on my plate", or wants a weekly brief.
version: 1.0.0
author: damsleth
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Skill
tags:
  - planning
  - review
  - weekly
  - productivity
---

# cj-weekly-review

A structured ritual that pulls together tasks, calendar, timesheet, and open loops into one picture.

**Adjacent:** `cj-owa-tools` for any calendar / mail / scheduling
command (profile inference, auth troubleshooting, install). Don't
re-derive those rules here.

Works in two modes:

- **Plan** (Monday / start of week) — what's coming, what needs scheduling, what to prioritize
- **Review** (Friday / end of week) — what happened, what slipped, what carries forward

Infer the mode from context or the day of the week. If unclear, ask: "Er dette en planlegging (start av uka) eller en gjennomgang (slutt av uka)?"

---

## Boot

Check that the required CLIs are available:

```bash
which things-cli
which owa-cal
which did-cli
```

For the cognitive ledger, check that `~/.config/cognitive-ledger/config.yaml` is readable (Read tool, no Bash). Missing tools: skip that section and note what was unavailable at the end.

---

## Step 1 - Things3

Pull the task picture:

```bash
things-cli today          # what's explicitly due today / this week
things-cli upcoming       # what's coming up
things-cli deadlines      # hard deadlines
```

If the week is already underway (Wednesday+), also pull:

```bash
things-cli logtoday       # what was completed today
```

Extract:
- Tasks due this week (hard deadlines)
- Overdue tasks (past deadline, still open)
- Tasks in the "Today" bucket
- High-signal upcoming tasks (next 7 days)

Don't dump the full backlog. Surface the 10-15 most actionable items.

---

## Step 2 - Calendar

Fetch this week's events for each relevant profile (per `cj-owa-tools`
inference rules - if the user only mentions work, skip BRKH; when in
doubt, pull both work profiles).

```bash
owa-cal events --week <n> --pretty                       # default (swon)
owa-cal --profile crayon events --week <n> --pretty
owa-cal --profile brkh events --week <n> --pretty        # if relevant
```

Get the current ISO week number with `date +%V`.

Extract:
- Meetings and commitments that consume significant time
- Days that are over-booked vs days with open space
- Events without categories (timesheet gaps)
- Any events the user may have forgotten about

For planning mode: flag days with < 2h of unstructured time so the user knows where focus blocks can go.

---

## Step 3 - Timesheet (did)

```bash
did-cli status --pretty
did-cli report --period current --pretty
```

Extract:
- Current submission status (submitted / open)
- Total hours logged this week vs expected
- Uncategorized events (will drop off the timesheet)
- If it's Thursday or Friday and the period isn't submitted: surface this prominently

If the Crayon calendar is included: note that did reads from one account - confirm which one to avoid confusion.

---

## Step 4 - Open loops (cognitive ledger)

Read the ledger context file (no Bash - use the Read tool):

```
~/.config/cognitive-ledger resolves to LEDGER_ROOT
Read {LEDGER_NOTES_DIR}/08_indices/context.md
```

Extract open loops that are:
- Overdue (next action date in the past)
- Stale (no update in 2+ weeks)
- Blocking other work (has dependents or is listed as a blocker)

Limit to 5-7 loops. Don't enumerate every open loop - only the ones that need attention this week.

---

## Output format

Present as a single structured brief. Keep it scannable — this is a tool, not a report.

### Plan mode (Monday)

```
## Uke <n> — Planlegging

### Denne uken
- [deadline-drevne oppgaver fra Things3]

### Kalender
- [dag: tid brukt på møter, ledige blokker]

### Timeføring
- Uke <n-1>: [innlevert / ikke innlevert, X timer]
- Uke <n>: [0h lagt inn]

### Åpne tråder som trenger oppmerksomhet
- [loop]: [neste steg] ([sist oppdatert])

### Forslag
- [dag] ser ut som en god dag for fokusarbeid (X timer ledig)
- Husk å kategorisere "[event]" for timeføring
```

### Review mode (Friday)

```
## Uke <n> — Gjennomgang

### Hva ble gjort
- [completions from Things3 logtoday/logbook]

### Hva slapp unna
- [overdue or not-done tasks]

### Timeføring
- [status + hours + uncategorized events]

### Åpne tråder — status
- [loop]: [done / progressed / stalled]

### Carry-forward til neste uke
- [top 3-5 priorities]
```

Adapt the language to what the user uses — Norwegian if they're speaking Norwegian, English if not.

---

## Behavior rules

- **Don't enumerate everything.** Curate. If Things3 has 80 tasks, show the 10 that matter this week.
- **Don't duplicate.** If something appears in both Things3 and the calendar, mention it once.
- **Flag blockers explicitly.** If a loop or task is blocking something visible in the calendar, say so.
- **Timesheet first on Thursday/Friday.** If the period isn't submitted and it's late in the week, lead with that nudge before the rest of the review.
- **Offer to act.** After the brief, ask: "Vil du at jeg skal hjelpe med noe av dette nå?" This skill surfaces the picture — taking action uses the relevant sub-skills (`cj-owa-tools`, `cj-did`, `cj-notes`).

---

## Integration with other skills

After the brief, the user may want to:
- Fix calendar entries → invoke `/cj-owa-tools`
- Submit timesheet → invoke `/cj-did`
- Log a decision or update an open loop → invoke `/cj-notes`
- Take meeting notes for an upcoming meeting → invoke `/cj-meeting-notes`

Don't invoke these automatically. Offer them as next steps.
