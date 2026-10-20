---
name: cj-daily
description: Create or refresh today's daily note in an Obsidian vault. Closes out the previous note with a retrospective headline and result bullets, then writes today's note as a short overview of what happened, routing reasoning to running notes. When installed, open work (`now`), today's calendar (owa-tools), recall (`yaams`) and the ledger feed a spoken "since yesterday" briefing. Use when the user says "ny daily note", "dagens note", "start dagen", "daily", "/cj-daily", or asks to set up or refresh today's journal entry. For ad-hoc capture during the day, use cj-notes instead.
---

# cj-daily

Morning ritual: assemble today's daily note from known sources, in a known format, with minimal judgment. The note records what *happened*; open work lives in its own tools and reaches the user as a spoken briefing.

## Local overlay

If `~/.config/cj-skills/cj-daily.md` exists, read it before acting. It holds this user's own profiles, paths and conventions, and it wins over the defaults here.

## Boot

0. **Probe optional sources** once with `command -v`: `now`, `owa-cal`, `yaams`, `ledger`, `things`. Only the journal folder is required. Each other source is used when its command exists, and a missing one is named once in the briefing. If `yaams` exists, start `yaams ingest --json` in the background now; it is slow, and Step 4 collects it.
1. **Resolve `{vault}`** the way the cj-notes skill's *Resolve the vault* section does: this overlay, then `NOTES_VAULT`, then the ledger config, then ask once and suggest saving the answer to `~/.config/cj-skills/cj-daily.md`. Read `{vault}/AGENTS.md` if it exists.
2. **Resolve the journal folder and format:** overlay, then `{vault}/AGENTS.md`, then `{vault}/.obsidian/daily-notes.json` (`folder`, `format`) when its format names a day rather than a week, then the defaults in *Note format*.
3. **Pick the mode:**

   | Mode | When | What it does |
   |---|---|---|
   | **closeout** | scheduled/unattended run, or the previous note has no headline | Step 1 only. Creates nothing for today. |
   | **generate** | interactive, today's note does not exist | Closeout if needed, then *Ensure today's note* and Steps 2–5. |
   | **refresh** | interactive, today's note exists | Merge into it, see *Refresh mode*. |

   The **headline is the closed-out flag**: a note with one is done, a note without one (or with a blank `## ~/ ` line) still needs Step 1. No marker files, no other state.

   A scheduled morning run (e.g. a 07:00 cron job calling a headless agent) is closeout mode: it writes yesterday's headline and bullets, runs the Step 4 briefing as a notification without the background ingest, and never creates today's note.

4. **Today's note is born when the user first touches the day** (through this skill, cj-notes or cj-meetings), never on a schedule. A pre-created empty note claims a day was recorded when nothing was.

### Note format

Defaults, for a vault whose overlay and `AGENTS.md` set nothing else:

- **Folder:** `{vault}/90-journal/` (the numbered layout in cj-notes' question playbook). It also holds week notes (`YYYY-Www.md`) and stray files.
- **Filename:** `YYYY-MM-DD-<ukedag>.md`, Norwegian weekday in lowercase (`2026-06-03-onsdag.md`). Map it from `date +%u` (1 mandag, 2 tirsdag, 3 onsdag, 4 torsdag, 5 fredag, 6 lørdag, 7 søndag); `date +%A` depends on the locale.
- **Title:** `# DD.måned YYYY - ukedag` (`# 03.juni 2026 - onsdag`).
- **Headline:** `## ~/ <dagens overskrift>`, directly under the title.
- **Log heading:** `## 🪵`, always last.
- **Agent log:** `{vault}/93-log/YYYY-MM-DD.md` (the journal filename minus the weekday), when that folder exists.

### Ensure today's note

cj-notes, and any other skill that logs into today's note, defers here when the note does not exist yet, so every writer creates the same skeleton. Create exactly this, in the resolved title format:

```markdown
---
tags:
  - journal
  - daily
---
# DD.måned YYYY - ukedag

## 🪵
```

No headline line: tomorrow's closeout writes it, and its absence is what marks the day as open. Never write a blank `## ~/ ` line. No topic headings: they appear only when something happens (Step 5).

## Step 1 – Close out the previous note

Take the most recent note **strictly before today** whose name matches the journal's date pattern (`YYYY-MM-DD-*.md` by default; week notes and stray files would otherwise sort last). Exactly that one:

- It already has a headline → nothing to close; say so.
- There is none → nothing to close; a day with no note stays without one.
- Leave older unclosed notes as history, and leave today's note open however empty it looks.

Close it from its log, writing into *that* note:

- The **headline**, directly under the title: the day's result in one line, never blank. Obsidian shows it in search previews and the graph.
- **Three to five `-` result bullets** under it, each passing the test "I did X". A quiet day gets one bullet.

Then route what it leaves for today: an actionable item not tracked anywhere → the task manager (Step 2); reasoning worth keeping → the running note (Step 2b). Topic sections stay in their own day; copying them forward forks state that starts rotting the same day.

## Step 2 – Tasks

The note holds no task state: no `- [ ]` checkboxes and no copies of open work. Tasks live in their own tools.

- **Sync first:** when `ledger` exists, run `ledger loops sync`. With `things3_sync_enabled: false` in the ledger config it reports "sync disabled" and the run moves on; when it reports actions, the flag was turned on deliberately, so leave it.
- **Read:** if `now` exists, `now --agent` (load the cj-now skill for `_owa.warnings` and the `⧉` convention). Add `--all` when the day spans the personal areas. Scope only with `--all` or `--profile`: `--source` silently drops ADO and plans. `--full` only when the curated view looks thin. Otherwise, if `things` exists, read today's list per cj-things. Use the result for the spoken briefing only.
- **Four stores, four jobs:** Azure DevOps holds work items others assign and is authoritative for their status; Things holds the user's own next steps and brain dumps; ledger loops hold reasoning and the ambient todo list agents pick up; repo `.plans/` holds repo-scoped todos and long-form plans.
- **Things vs ADO:** a Things task never *is* an ADO work item. It may carry an ADO id in its title, and is then a personal sub-step closed on its own terms. Say nothing about `⧉` rows unless a Things task duplicates the work item outright (same title, no personal step): cancel it. Personal sub-steps stay out of ADO, and any ADO comment needs the user's explicit OK.
- **Exception:** a deadline landing today or tomorrow may appear as a single `🎯` bullet, two at most, because it changes the shape of the day.
- **Write:** an actionable item from Step 1 or Step 4 that no source tracks yet (dedupe with `now --grep <keyword>` when available) goes to Things via cj-things, in the area `things areas --json` matches; a dated item gets `--deadline`, a blocked one `--tags Avventer`. With no task manager installed, list it in the briefing for the user to file.
- Something the user says is done → complete it in its source and log it.
- Stale deadlines (long past) → flag once and offer to clear.

## Step 2b – Reasoning goes to the running note

Reasoning (a checklist, a root cause, a decision and its why) goes to the topic's **running note** under a dated `## YYYY-MM-DD` heading, per the cj-notes skill's *Where things go*. One running note per customer or category, no year in the name; split when a topic earns its own file, never on length. Locate running notes via the overlay or `{vault}/AGENTS.md`; revive an existing one before creating another. Later entries win over earlier ones; leave the chronology as it is. A running note stays alive only while something writes to it, so run this step every time.

## Step 3 – Calendar (best-effort)

When `command -v owa-cal` fails, skip this step and point the user to the cj-owa-tools skill's `## Requirements` section. Otherwise make one call across every profile, never naming one (an event often sits on a profile you would not guess):

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

1. Collect the background ingest from Boot step 0. It takes about 2 minutes (Teams channels dominate); wait up to about 3 before querying the existing index, and say so. Its final `{"type":"result",...}` envelope gives `stats.totals` and per-source `stats.sources.*.new`; `error.failed_sources` lists sources to mention, not block on (a source failing on macOS permissions, such as `imessage`, is routine).
2. Derive 2–3 themes from the previous note's headline and topic sections, the running notes in play, and today's meeting subjects.
3. `yaams query "<theme>" --top-k 5 --json` per theme.

When `ledger` exists, read `{ledger}/08_indices/context.md` and run `sheep status`; `ledger briefing` adds open loops near or past due. The index is generated and lags: compare its `Latest source update:` line with `sheep status`, and when sleep is overdue the loop files in `05_open_loops/` win. Verify a loop there before mentioning it. Open-loop counts and sleep status go in the briefing only, never the note; ledger writes go through cj-notes.

**Briefing**, in the language the user triggered with: new signals per source, failed sources, today's meetings, open work worth knowing, and the 2–4 threads recall surfaced that no note holds yet. An event worth logging seeds the log; reasoning goes to Step 2b; noise goes nowhere.

## Step 5 – Write the note

Match the journal's existing notes. Default shape:

```markdown
---
tags:
  - journal
  - daily
---
# DD.måned YYYY - ukedag
## ~/ <dagens overskrift>        ← written by tomorrow's closeout

- <hva som faktisk ble gjort>
- <neste>

### <tema, kun hvis noe skjedde der i dag>
<prosa: resonnementet som ikke fins noen annen plass, eller en peker dit det bor>

## 🪵
- **HH:MM** <hva brukeren gjorde>
```

- The headline and result bullets are written retrospectively (Step 1). During the day leave them out, unless the user gives a headline; then use it verbatim.
- The note is a daily overview per customer and per category (home, work, a volunteer organisation, self), only where there is something to say. A `### topic` heading appears only on a day something happened there, and holds prose or a one-line pointer to the running note. A fixed skeleton of topics invites filler: an unattended run fills it with "no change since yesterday". When the user takes up a new topic during the day, append its `###` heading.
- **The log is the user's day.** One line per thing the user did or that happened to them: `- **HH:MM** <text>`, timestamp rounded to 5 minutes, inserted chronologically (the user edits in Obsidian too). Whoever acted decides it: the user's own debugging of a tool belongs here; your lookups to build the note do not. A long entry may nest one level of sub-bullets rather than grow into a paragraph:

  ```markdown
  - **09:10** loop-triage (/cj-daily): 12 åpne loops ned til 6.
    - Seks lukket, én snoozet. To flyttet til løpende notat.
  ```

- **Agent log:** what this skill did to run itself (note created, refresh, loops-sync counts, `owa-cal -A` results, ingest statistics, "recall hit nothing") goes to the agent log, append-only, never the journal. It may be more detailed than a log line; the next run is its reader. Without an agent log folder, it goes in the chat summary only. A new agent log starts:

  ```markdown
  # YYYY-MM-DD

  Agent-logg for [[YYYY-MM-DD-ukedag]].

  - **HH:MM** <det skillet gjorde>
  ```

- **Voice:** the journal voice is Norwegian (Bokmål) by default, compact, fragments OK, bold for emphasis, wikilinks for cross-references; chat replies mirror the trigger language. Load the cj-voice-dna skill before writing, if installed. Dashes follow the typography rule in cj-notes' *Write the note*, for the note, log lines, Things titles and chat alike; check for `—` before writing, even when cj-voice-dna is not loaded.
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
- A weekly review skill, if installed, reads the headline and result bullets rather than whole notes, never writes to a daily note, and writes its brief to the week note (`YYYY-Www.md` in the journal folder) under the same typography rule.
