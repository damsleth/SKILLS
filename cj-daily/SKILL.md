---
name: cj-daily
description: Create or refresh today's daily note in an Obsidian vault. Closes out the previous note with a retrospective headline and result bullets, then writes today's note as a short overview of what happened, routing reasoning to running notes. When installed, open work (`now`), today's calendar (owa-tools), recall (`yaams`) and the ledger feed a spoken "since yesterday" briefing. Use when the user says "ny daily note", "dagens note", "start dagen", "daily", "/cj-daily", or asks to set up or refresh today's journal entry. For ad-hoc capture during the day, use cj-notes instead.
---

# cj-daily

Morning ritual: assemble today's daily note from known sources, in a known format, with minimal judgment. The note records what *happened*; open work lives in its own tools and reaches the user as a spoken briefing.

## Local overlay

If `~/.config/agent-skills/cj-daily.md` exists, read it before acting. It holds this user's own profiles, paths and conventions, and it wins over the defaults here.

## Boot

0. **Probe optional sources** once with `command -v`: `now`, `owa-cal`, `yaams`, `ledger`, `things`. Only the journal folder is required. Each other source is used when its command exists, and a missing one is named once in the briefing. If `yaams` exists, start `yaams ingest --json` in the background now; it is slow, and Step 4 collects it.
1. **Resolve `{vault}`** the way the cj-notes skill's *Resolve the vault* section does: this overlay, then `NOTES_VAULT`, then `ledger paths --json`, then ask once and suggest saving the answer to `~/.config/agent-skills/cj-daily.md`. Read `{vault}/AGENTS.md` if it exists.
2. **Resolve the journal folder and filename:** overlay, then `{vault}/AGENTS.md`, then `{vault}/.obsidian/daily-notes.json` (`folder`, `format`), then `{vault}/journal/` with `YYYY-MM-DD.md`.
3. **Pick the mode:**

   | Mode | When | What it does |
   |---|---|---|
   | **closeout** | scheduled/unattended run, or the previous note has no headline | Step 1 only. Creates nothing for today. |
   | **generate** | interactive, today's note does not exist | Closeout if needed, then *Ensure today's note* and Steps 2–5. |
   | **refresh** | interactive, today's note exists | Merge into it, see *Refresh mode*. |

   The **headline is the closed-out flag**: a note with one is done, a note without one still needs Step 1. No marker files, no other state.

4. **Today's note is born when the user first touches the day** (through this skill, cj-notes or cj-meetings), never on a schedule. A pre-created empty note claims a day was recorded when nothing was.

### Ensure today's note

cj-notes, and any other skill that logs into today's note, defers here when the note does not exist yet, so every writer creates the same skeleton. Create exactly this (overlay may change the title format and headings):

```markdown
---
tags:
  - journal
  - daily
---
# YYYY-MM-DD

## Log
```

No headline line: tomorrow's closeout writes it, and its absence is what marks the day as open. No topic headings: they appear only when something happens (Step 5).

## Step 1 – Close out the previous note

Take the most recent note **strictly before today** whose name matches the journal's date pattern (stray files would otherwise sort last). Exactly that one:

- It already has a headline → nothing to close; say so.
- There is none → nothing to close; a day with no note stays without one.
- Leave older unclosed notes as history, and leave today's note open however empty it looks.

Close it from its log, writing into *that* note:

- The **headline**, directly under the title (default `## Summary: <headline>`): the day's result in one line, never blank. Obsidian shows it in search previews and the graph.
- **Three to five `-` result bullets** under it, each passing the test "I did X". A quiet day gets one bullet.

Then route what it leaves for today: an actionable item not tracked anywhere → the task manager (Step 2); reasoning worth keeping → the running note (Step 2b). Topic sections stay in their own day; copying them forward forks state that starts rotting the same day.

## Step 2 – Tasks

The note holds no task state: no `- [ ]` checkboxes and no copies of open work. Tasks live in their own tools.

- **Read:** if `now` exists, `now --agent` (load the cj-now skill for scopes, `_owa.warnings` and the `⧉` convention). Otherwise, if `things` exists, read today's list per cj-things. Use the result for the spoken briefing only.
- **Exception:** a deadline landing today or tomorrow may appear as a single `🎯` bullet, two at most, because it changes the shape of the day.
- **Write:** an actionable item from Step 1 or Step 4 that no source tracks yet (dedupe with `now --grep <keyword>` when available) goes to Things via cj-things. With no task manager installed, list it in the briefing for the user to file.
- Something the user says is done → complete it in its source and log it.
- Stale deadlines (long past) → flag once and offer to clear.

## Step 2b – Reasoning goes to the running note

Reasoning (a checklist, a root cause, a decision and its why) goes to the topic's **running note** under a dated `## YYYY-MM-DD` heading, per the cj-notes skill's *Where things go*. Locate running notes via the overlay or `{vault}/AGENTS.md`; revive an existing one before creating another. Later entries win over earlier ones; leave the chronology as it is.

## Step 3 – Calendar (best-effort)

When `command -v owa-cal` fails, skip this step and point the user to the cj-owa-tools skill's `## Requirements` section. Otherwise make one call across every profile:

```bash
owa-cal -A events --date today | python3 -c "
import json,sys
for r in json.load(sys.stdin)['results']:
    for e in (r.get('data') or []):
        print(r['profile'], e['start'][11:16], e['end'][11:16], e['subject'], e['showAs'])
"
```

Most profiles are empty on a given day. On a partial failure use what returned and name the failed profiles in one line (fan-out exit codes: cj-owa-tools). Meetings shape the briefing's order.

## Step 4 – Recall and the "since yesterday" briefing

When `yaams` exists:

1. Collect the background ingest from Boot step 0. Its final `{"type":"result",...}` envelope gives `stats.totals` and per-source `stats.sources.*.new`; `error.failed_sources` lists sources to mention. If it runs well past a few minutes, query the existing index and say so.
2. Derive 2–3 themes from the previous note's headline and topic sections, the running notes in play, and today's meeting subjects.
3. `yaams query "<theme>" --top-k 5 --json` per theme.

When `ledger` exists, `ledger briefing` adds open loops near or past due. `08_indices/context.md` is a generated index and lags behind; verify a loop against `05_open_loops/` before mentioning it. Ledger content stays in the briefing; ledger writes go through cj-notes.

**Briefing**, in the language the user triggered with: new signals per source, failed sources, today's meetings, open work worth knowing, and the 2–4 threads recall surfaced that no note holds yet. An event worth logging seeds the log; reasoning goes to Step 2b; noise goes nowhere.

## Step 5 – Write the note

Match the journal's existing notes. Default shape:

```markdown
# YYYY-MM-DD
## Summary: <headline>        ← written by tomorrow's closeout

- <result bullet>

### <topic, only if something happened there today>
<prose: reasoning that exists nowhere else, or a pointer to the running note>

## Log
- **HH:MM** <what the user did>
```

- The headline and result bullets are written retrospectively (Step 1). During the day leave them out, unless the user gives a headline; then use it verbatim.
- A `### topic` heading appears only on a day something happened there, and holds prose or a one-line pointer to the running note. A fixed skeleton of topics invites filler.
- **The log is the user's day.** One line per thing the user did or that happened to them: `- **HH:MM** <text>`, timestamp rounded to 5 minutes, inserted chronologically (the user edits in Obsidian too). Whoever acted decides it: the user's own debugging of a tool belongs here; your lookups to build the note do not.
- **Agent log:** what this skill did to run itself (note created, refresh, source counts, failed sources) goes to the agent log folder the overlay names, one `- **HH:MM**` line each, append-only. Without one, it goes in the chat summary only.
- Load the cj-voice-dna skill before writing, if installed. Write in the journal's language; reply in the user's.
- Test every line: if it would be just as true tomorrow, it belongs in a task tool, the running note or the agent log.

## Refresh mode

When today's note exists, merge into it:

- The log is append-only: keep existing lines' wording; add new ones in chronological order.
- Result bullets may grow during the day; the next closeout finalises them.
- New reasoning → running note, plus a `###` pointer if today has no heading for that topic.
- Leave completed items completed.
- The refresh itself goes to the agent log.

## Behaviour

- **Writes:** the journal, running notes, the agent log, and task add/complete through cj-things. Calendar and ledger stay read-only; offer cj-notes for durable facts and cj-things for other task changes.
- **Curate hard:** when a source returns 50 items, none go in the note and one or two reshape the briefing.
- **Write without asking** in generate mode. Report the note path and a 3–5 line summary; ask only when the sources genuinely contradict each other.

## Related skills

- cj-notes: daytime capture into the same note and running notes, with the same log rules.
- cj-now / cj-things: task reads / task writes.
- cj-meetings: meeting notes that log into today's note.
- A weekly review skill, if installed, should read the headline and result bullets rather than whole notes.
