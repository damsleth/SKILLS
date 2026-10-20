---
name: cj-meetings
description: Interactive meeting notes skill for preparing, running, and documenting meetings with automatic participant research and live transcription from Microsoft Teams live captions, plus on-demand screenshots of the Teams meeting window (codeword `sc`). Use when the user asks for meeting notes, meeting minutes, meeting prep, "møtenotater", "møtereferat", wants to take notes during a meeting, transcribe a meeting, says "start møte", or wants to document what happened in a meeting. Also handles recap of an already-recorded meeting from a Teams/OneDrive recording URL. For generic calendar lookup, use cj-owa-tools instead.
---

# Meeting notes (cj-meetings)

Prepare, run, and document a meeting: fetch it from Outlook with `owa-cal`,
research the attendees, and write clean markdown notes, grounded in a live
transcript captured from Microsoft Teams live captions.

**Language.** All user-facing output, and the notes themselves, follow the
language the user invoked the skill in. If that is ambiguous, ask once and keep
it for the session. The prompts quoted below are examples; say them in the
user's language. Code and logs stay in English.

## Local overlay

If `~/.config/cj-skills/cj-meetings.md` exists, read it before acting. It holds this user's own profiles, paths and conventions, and it wins over the defaults here.

## Requirements

- **owa-piggy + owa-tools** (`owa-cal`, `owa-graph`, `owa-vids`). Check and
  install commands are in the `## Requirements` section of the cj-owa-tools
  skill; profile resolution, auth and troubleshooting follow that skill too.
- **macOS, for live capture and `sc`.** `teams-captions.py` reads Teams through
  the macOS Accessibility API (via `ctypes`, stdlib only, runs on the system
  `/usr/bin/python3`) and screenshots with `screencapture` and `sips`. It needs
  **Accessibility** permission for the terminal running the agent, plus
  **Screen Recording** for `sc` (both in System Settings → Privacy & Security).
  On other platforms, run the meeting on chat notes alone.
- **Recap mode:** `ffmpeg` (for `owa-vids get`) and `whisper-cpp`.

**Paths.** `<skill dir>` is the directory holding this SKILL.md (it differs
between Claude, Codex and Copilot installs); the bundled scripts are
`<skill dir>/teams-captions.py` and `<skill dir>/facilitator-recap.py`.
`MEETING_NOTES_DIR`, when set, is the default folder for new meeting notes;
otherwise the default is the current working directory.

## Phases

1. **Calendar lookup**: the user's meetings for the next 7 days via `owa-cal`
2. **Meeting selection**: the user picks one
3. **Participant research**: attendees from Graph, externals researched on the web
4. **File setup**: the notes file, optionally from a template
5. **Live meeting**: Teams captions mirrored to a transcript file while the user
   takes notes in chat; the agent refines and appends them
6. **Wrap-up**: end timestamp, summary and action items from the user's notes,
   the transcript, and the Teams Facilitator notes when the meeting had them

If calendar access fails, fall back to manual meeting input. For a meeting that
is already over and was recorded, use Recap mode instead of the live phases.

---

## Recap mode (recorded meeting)

Trigger: the user pastes a Teams/OneDrive recording URL, or asks to summarize a
recording.

```bash
owa-vids info "<recording-url>" --profile <alias> --pretty
owa-vids get "<recording-url>" --profile <alias> --audio-only --out meeting.m4a
whisper-cpp meeting.m4a
```

`owa-vids` writes binary output, so it runs on one explicit `--profile`, never
`-A`. Infer the profile per cj-owa-tools; the recording URL tells you the
tenant. If the recording has slides or screen-share worth reading and the
cj-video-vision skill is installed, run it on the full video download instead.

Feed the transcript into Phase 6 exactly as a live transcript, resolving speaker
references from the attendee list (`owa-graph GET "me/events/<id>"` if the
meeting is still in the calendar, otherwise ask). Confirm the summary with the
user before finalizing.

---

## Phase 1: Get calendar data

### Step 1: The user's email domain

Take the domain of the user's email from session context to classify attendees
as internal or external. Ask if it is unavailable.

### Step 2: Is the meeting in Outlook?

Ask: "Is this meeting in your Outlook calendar?" Yes → Step 3. No (ad-hoc,
external invite, informal) → Manual fallback. When the opening message already
answers it (a pasted title and time, "I have a meeting with X in 10 minutes"),
go straight to Manual fallback.

### Step 3: Fetch meetings

Compute today through today + 7 days and pull every active profile in one call,
without asking which calendar:

```bash
owa-cal -A events --from <YYYY-MM-DD> --to <YYYY-MM-DD> --limit 50
```

`-A` labels each meeting with the profile it belongs to, so a meeting on an
unexpected profile still shows up. The output is
`{"results": [{"profile", "ok", "data"}]}` with the events in **`data`** (there
is no `events` key); with a single `--profile` it is the bare events array. Each
event has `id`, `subject`, `start`, `end`, `categories`, `location`, `showAs`,
`isAllDay`, `type`, `seriesMasterId`.

```bash
owa-cal -A events --from <d> --to <d> | jq -c '.results[] | {profile, e: [.data[]? | {id, subject, start, end, location}]}'
```

Every profile coming back empty means suspect the filter: look at the raw
output before falling back to manual input. A `[]?` on a wrong key silently
returns nothing.

Attendees come later, from `owa-graph` (Phase 3).

### Step 4: Filter

Drop events where:
- `isAllDay` is true (blockers, out-of-office)
- `showAs` is `Free` or `Tentative`
- `categories` contains `IGNORE`
- the subject is a personal block ("Focus time", "Lunch", "[Calendar Blocker] ...")

### Manual fallback

Tell the user calendar data could not be fetched, then ask for: title, date and
time (from–to), location (physical / Teams / other), attendees (name and email).

---

## Phase 2: Meeting selection

Show the filtered meetings as a numbered list with date and time, subject, and
location:

> 1. **Project meeting with Acme Inc** – Monday 27 March 10:00–11:00, Teams
> 2. **Q2 status** – Tuesday 28 March 14:00–15:00, Room 4

Ask which meeting to take notes for; accept a number or a title.

---

## Phase 3: Participant research

### Step 1: Attendees from Graph

For a meeting picked from Outlook, fetch the event with the `id` from `owa-cal`:

```bash
owa-graph GET "me/events/<event_id>" --audience outlook
```

Take every `attendees[]` entry of type `required` or `optional` (skip
`resource`): `emailAddress.name`, `emailAddress.address`. If the call fails or
the list is empty, ask the user to paste names and emails.

### Step 2: Classify

**Internal** = same email domain as the user; **external** = any other domain,
or flagged external by the user. Ask about attendees without an email. Show the
list so the user can confirm or correct it.

### Step 3: Choose whom to research

Offer: externals, everyone, nobody, or a custom pick (multi-select).

### Research

For each selected person, search the web for current role and employer, a brief
professional background, a LinkedIn profile, and what their employer does (size,
relevant context). Start with `"Full Name" company/domain`; for a generic email
domain (gmail, outlook, hotmail) search `"Full Name" LinkedIn`. On an ambiguous
match, ask the user for a LinkedIn URL or more context.

Keep the results in context: the live phase uses them to resolve references.
Summarize for the user:

> **Ola Nordmann** (external) – Project lead, Acme Inc. Acme is a 50-person consultancy focused on digital transformation.
> **Kari Hansen** (internal) – Developer, your team.

---

## Phase 4: File setup

### Template

List `<skill dir>/templates/*.md`. If any exist, ask whether to use one (or
blank). For a chosen template, fill its frontmatter (e.g. customer, project,
date auto-filled from the meeting, meeting type) and ask for fields that cannot
be auto-filled. `templates/standard.md` is a Norwegian example; add a `.md` file
there to create a new template.

### Location

Ask where to save, offering `$MEETING_NOTES_DIR` (or the current directory) as
the default. Filename: `YYYY-MM-DD-<title>.md`, the title lowercased with
hyphens and no special characters.

The live transcript goes in a **second file beside it**, same stem plus
`.transcript.md` (`2026-03-27-project-acme.transcript.md`).
`teams-captions.py` owns that file and rewrites it on every poll; notes go only
in the notes file.

### Create the file

Apply *Writing style* before this first write. Start the file with (headings in
the user's language):

```markdown
# [Meeting title]

**Date:** YYYY-MM-DD
**Time:** HH:MM – HH:MM
**Location:** [Location]
**Attendees:**
- Name (role/company) – internal/external

---

## Attendee background

[Brief summaries from the research phase]

---

## Notes

[Appended during the meeting]
```

With a template, follow its structure instead, keeping the attendee info and
research.

---

## Phase 5: Live meeting

The meeting yields two things in parallel: a **transcript** from Teams live
captions, and the user's **own notes** typed in chat. Both feed Phase 6.

### Step 1: Start capture in the background

Start it as soon as the notes file exists, before the meeting begins. It waits
for Teams and the caption panel on its own.

```bash
<skill dir>/teams-captions.py --out "<notes-stem>.transcript.md"
```

Run it as a **background** command with the longest timeout the harness allows
(2 hours in Claude Code). When the harness stops it at its time limit, restart
it at once with the same `--out` and say so in one line; a meeting over 2 hours
needs one restart per 2 hours. Restarting with the same `--out` always resumes
from the existing file and never truncates it, so that is the fix whenever
capture stops mid-meeting.

It polls every 5 s (`--interval`) and exits by itself once the caption panel
has been gone for 12 polls (`--stop-after-missing`), so leaving the meeting
stops it. If the user never turns captions on, stop it with
`pkill -TERM -f teams-captions.py`.

Append to the notes file:

```markdown
**Meeting started:** YYYY-MM-DD HH:MM
```

### Step 2: Have the user turn on captions

Only the user can turn captions on. Ask them to:

1. **... More** → **Language and speech** → **Turn on live captions**
2. Pop the caption panel out into its own window and leave the meeting and
   caption windows unminimized. (Capture also reads a docked panel; `sc` uses
   the popped-out window to find the meeting window.)
3. Set **Language and speech** → **Spoken language** to the language the meeting
   is actually in.

Give the menu labels in the language of the user's **Teams UI**, which may
differ from the conversation language. For a non-English Teams UI, pass the
caption panel's localised accessibility name with `--anchor` (default
`Live Captions`).

**Ask the spoken language for every meeting.** Teams keeps whatever was set
last, and speech captioned in the wrong language comes out as gibberish. When
the attendee list makes the language obvious, say which you expect and let the
user correct it. If the transcript tail turns to nonsense mid-meeting (someone
switched language), tell the user in one line to change Spoken language, and
note the garbled window in the notes so nobody trusts it later.

### Step 3: Check the panel is readable

A diagnostic, not a gate: capture is already running.

```bash
<skill dir>/teams-captions.py --check
```

- `OK: caption panel found, N line(s) currently visible` → done. `N` may be `0`
  until someone speaks, or while Teams wakes its accessibility tree; leave
  capture running.
- `NOT FOUND` → it lists the open Teams windows; captions are off or the
  `--anchor` does not match. Have the user redo Step 2.
- `no Accessibility permission` → the user grants it to the terminal (one-time).

Then tell the user capture is running, that typing **`sc`** screenshots the
meeting window into the notes, and that they should still type the notes that
matter: the transcript is raw material, their judgement is the record.

### When capture stops on its own

Each exit is a meeting minute being lost, so act on it the moment it arrives:

| Exit | Message | Cause | Tell the user, then restart with the same `--out` |
|---|---|---|---|
| 2 | `panel found but reading empty` | Accessibility tree went cold: 3 min of empty reads with the panel open | close and re-pop the captions panel |
| 3 | `panel frozen` | Same lines for 3 min: a minimized Teams window stops updating | restore the meeting and caption windows |

If the meeting was simply silent, restart with a larger `--stop-after-blind` /
`--stop-after-frozen` (or `0` to disable). When the user announces a **break**,
restart right away with `--stop-after-blind 240` (20 min) before it trips, and
say so in one line.

### During the meeting

The user's messages are raw notes, questions, or instructions ("add an action
item", "note that we agreed on X").

**Raw notes:**
- Clean them up: fix typos, expand abbreviations, add structure.
- Read the tail of the transcript to ground them: who said what, exact figures,
  names and dates the user only half-typed.
- Resolve ambiguous references with the participant research (one external
  woman in the meeting + "she says we must deliver faster" → attribute it to
  her by name).
- Append under the notes heading, grouped by topic with `###` subheadings.

**Questions:**
- Answer from the participant research, with extra web lookups as needed. Add
  Q&A to the notes only when asked.
- **Investigations go to a background subagent, so note-taking never stops.** A
  question needing more than one quick read (code, a tenant, telemetry, a work
  item) is handed to a background subagent: a cheaper model for a bounded
  lookup, the strongest model for root-cause work across sources. Give it the
  established facts and ask for read-only work with evidence. Keep taking notes
  while it runs, and add its answer to the notes when it reports back.

**Instructions:** carry them out in the right section of the file.

### Reading the transcript

Read the file each time rather than holding it in context; it grows all
meeting. Lines look like:

```markdown
**11:52 Hansen, Kari:** This is a test of speaking a long sentence.
```

- **In a hybrid meeting the room is one speaker.** Everyone physically present
  is captioned under the room device's name; only remote participants get their
  own. Ask the user who said what when it matters.
- **Captions are evidence, never quotable text.** Live ASR mangles names,
  numbers, acronyms and words from a second language. Where the transcript and
  the user disagree, the user wins.
- **The file is rewritten each poll**, because Teams revises caption lines after
  showing them. Read it; leave writing to the script.
- **A stale-looking tail is normal.** The panel clears on its own timer, not when
  people go quiet. Judge capture health by the file's mtime; real stalls end
  capture loudly (see the exit table).

### Screenshots: the `sc` codeword

When the user types **`sc`** (alone, or leading a note), screenshot the meeting
window right away, without asking. It captures only the meeting window, on
whichever display, silently and without stealing focus:

```bash
<skill dir>/teams-captions.py --shot "<notes-file>.md"
```

The script picks the location: inside an Obsidian vault it follows the vault's
attachment setting (`.obsidian/app.json`) and embeds with a wikilink; elsewhere
the image lands beside the notes with a relative markdown link. It prints:

```
png: <saved image>
preview: <downscaled copy, read this one>
embed: <line to paste into the notes>
```

Read the preview, write up what it shows, and put the embed line under the
topic it belongs to. Pair it with the transcript tail for what was said around
it. Without Screen Recording permission macOS returns only the wallpaper.

### Writing style

If the cj-voice-dna skill is installed, load it before the first write to disk
and keep applying it to every append and to all of Phase 6.

Punctuate with an en-dash (`–`), a comma, a colon or parentheses, and check the
text for em-dashes (`—`) before writing it: the em-dash is the most obvious tell
of machine-written text.

- Past tense for what was said and decided ("Ola presented...", "It was decided that...")
- Decisions: **Decision:** ...
- Action items: **Action:** [who], [what], due [date]
- Keep attributions where relevant

### Without captions

The user forgot, the tenant blocks them, the meeting is on a phone, or the
machine is not a Mac: say so once and run the meeting on chat notes alone.
Every other phase is unchanged.

---

## Phase 6: Wrap-up

When the user says the meeting is over:

### 0. Gather the sources

Stop capture so the transcript is final, then read it in full:

```bash
pkill -INT -f teams-captions.py
```

Then fetch the **Facilitator notes**, if the meeting ran the Teams Facilitator
agent. Facilitator writes a Loop page, `<subject> <date>.loop`, to the
organizer's OneDrive and shares it with attendees, so the profile that attended
can read it:

```bash
<skill dir>/facilitator-recap.py --profile <alias> "<subject>" <YYYY-MM-DD>
```

It prints a snapshot and a replay of the edit ops, each line tagged with its
author: `[AI-generated]` is Facilitator, a name is a human edit. Read both;
where they differ, the snapshot is the reconciled one. On "no ... in
sharedWithMe" (no Facilitator, or not shared with that profile), ask in one line
whether the user wants to paste the recap from Loop; otherwise continue with two
sources.

Rank the sources **user notes > Facilitator notes > captions**. The transcript
supplies coverage (topics touched, figures, names, commitments the user did not
type); Facilitator heard the whole meeting, so it covers minutes before capture
started and any stalled or garbled stretch; the user's notes supply what
mattered and win every disagreement. Both generated sources are evidence: never
paste a caption line or Facilitator text into the summary verbatim.

### 1. End timestamp

```markdown
**Meeting ended:** YYYY-MM-DD HH:MM
```

### 2. Summary and action items

The longest stretch of generated prose: apply *Writing style* and sweep for `—`
before writing. Append (headings in the user's language):

```markdown
---

## Summary

[2-5 bullets: key topics and outcomes]

## Decisions

[Decisions made, if any]

## Action items

| # | Owner | Task | Due |
|---|-------|------|-----|
| 1 | Ola   | ...  | ... |

## Next steps

[Agreed follow-ups, next meeting, etc.]
```

### 3. Review with the user

Present the summary and ask whether it is right and complete. List what came
only from the transcript ("From the transcript I included: [X]. Correct?") and
only from Facilitator ("From Facilitator I included: [Y]. Correct?") so the user
can confirm or drop it. Refine, then confirm the final file is saved.

### 4. Delete the transcript

Once the user has answered the review, delete the transcript file without asking
and say so in one line: it is long, verbatim and full of chatter, and the notes
are the record. Keep it only if the user asked for that before wrap-up.

---

## Standing rules

- **Notes file:** edit or append after each batch of notes rather than
  rewriting the whole file. The transcript file belongs to `teams-captions.py`.
- **Context:** keep the participant research active all meeting to resolve
  pronouns and company mentions.
- **Timestamps:** the user's local time.
- **Tone:** professional, approachable, short sentences.
- **Ambiguity:** ask a clarifying question when a note is ambiguous; resolve it
  silently when context makes it obvious.

---

## `teams-captions.py` reference

Mirrors the Teams caption panel into a markdown file. Read-only towards Teams:
it never clicks, types or steals focus, and needs no API, recording or audio
pipeline.

```bash
teams-captions.py --check                           # is the caption panel readable?
teams-captions.py --out transcript.md               # mirror it, 5 s polls, until captions close
teams-captions.py --out transcript.md               # same file again = resume, never truncate
teams-captions.py --out t.md --interval 10          # slower polling
teams-captions.py --out t.md --stop-after-blind 0   # disable the cold-tree watchdog
teams-captions.py --out t.md --stop-after-frozen 0  # disable the frozen-panel watchdog
teams-captions.py --out t.md --anchor <name>        # non-English Teams UI
teams-captions.py --shot notes.md                   # screenshot the meeting window, exit
teams-captions.py --demo                            # self-check, no Teams needed
```

It is stdlib-only by design (the Accessibility API is plain C, reached with
`ctypes`); keep it free of `pip`/`uv` dependencies. The merge, the
two-static-text entry shape, the resume, and the three watchdogs each handle a
Teams behaviour observed in live meetings; the reasons are in the script's
docstrings, `--demo` covers each one, and simplifications are marked
`ponytail:`. Read those before changing any of it.
