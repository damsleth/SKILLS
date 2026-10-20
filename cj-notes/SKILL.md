---
name: cj-notes
description: Capture human-facing notes and maintain structured long-term memory. Writes notes to an Obsidian vault first when the user wants to take notes, journal, capture a conversation, or keep ephemeral context; syncs to a long-term memory store (the cognitive ledger, when installed) only when there are durable facts, preferences, decisions, goals, concepts, or open loops. Asks targeted questions before writing. Use when the user wants to take notes, log decisions, capture ideas, journal, or remember something.
---

# Notes

Two layers, written in this order:

- **Notes** (human-facing): markdown files in the user's Obsidian vault. Always the first write.
- **Long-term memory** (agent-facing): atomic, searchable notes in the [cognitive ledger](https://github.com/damsleth/cognitive-ledger). Written only when the input carries a durable signal, and only when the `ledger` CLI is installed. See *Ledger sync*.

## Local overlay

If `~/.config/cj-skills/cj-notes.md` exists, read it before acting. It holds this user's own profiles, paths and conventions, and it wins over the defaults here.

## Resolve the vault

Take the first that answers, then use the literal absolute path (`{vault}` below) in every command:

1. The overlay names the vault.
2. `printenv NOTES_VAULT`.
3. `command -v ledger` succeeds: `ledger paths --json`, key `source_notes_dir`.
4. Ask the user once for the vault path, and suggest saving it to `~/.config/cj-skills/cj-notes.md` so the question never comes back.

Read `{vault}/AGENTS.md` before the first write if it exists; it holds the vault's own folder and naming rules. Run commands with absolute paths from the current directory rather than `cd {vault} && <write>`.

## Write modes

- **`notes-only`**: write the note, skip memory. The default for informal conversations ("prat med X", "snakket med X", "talked with X"), work sessions, observations, journal entries and raw context capture.
- **`notes+ledger`**: write the note, then sync the durable items it contains. Use when the input states a lasting preference, records a decision or commitment, defines a concept, sets a goal, or leaves an explicit unresolved follow-up.
- **`ledger-only`**: skip the note. Use for "just log this", "remember that…", or a bare preference or fact with no note value.

A durable signal is a stable preference, a decision or commitment, a reusable fact about a person, project or system, an open loop with a concrete next action, a goal, or a definition. Names, projects, tools and events in the text are not signals by themselves; "I talked with X", activity logs, topic lists and transient troubleshooting stay in the note.

## Where things go

Decide first whether you hold a dated event or durable reasoning. They go to different files, and reasoning written into a dated file is how a journal rots into a project tracker.

| What you have | Destination |
|---|---|
| Something the user did, or that happened, at a time | one line in today's daily note, if the vault keeps one |
| Reasoning, a checklist, a root cause, a decision and its why | the topic's **running note**, under a dated `## YYYY-MM-DD` heading |
| An actionable item | the user's task manager (load the cj-things skill if installed), not a checkbox in the note |
| Your own operational chatter (a tool ran, a source failed) | the vault's agent log folder if it has one, otherwise nowhere |
| A durable fact, preference, decision, goal or loop | long-term memory, per *Ledger sync* |

- A daily-note entry is one line. When it needs sub-bullets it is a report and belongs in the running note.
- The test for a daily-note entry is who acted: the user's own work stays; your lookups on their behalf do not.
- Insert a new entry chronologically. The user edits these files by hand, so leave existing lines as they are.
- A running note survives only while something writes to it. Revive an existing one before creating another, keep the year out of its name, and split it when a topic earns its own file.

## Workflow

### 1. Classify

Detect the intent (meeting, conversation, project update, decision, idea, plan, journal, reference, preference, cleanup) and pick a write mode.

### 2. Ask before writing

Ask only what is missing, at most 5 questions in one batch, drawn from `references/question-playbook.md`. Skip the questions when the input is already complete.

When the user asks an investigative question mid-capture ("why is X missing?") that needs more than one quick read, hand it to a background subagent if your harness has one: give it the established facts, ask for read-only work with evidence, keep capturing, and write its answer into the note when it reports back. A lighter model suits a bounded lookup; root-cause work across code or systems wants the strongest one.

### 3. Choose the destination

- Search first: `rg -l "<topic>" {vault}`. Update an existing note over creating a duplicate.
- Route by the vault's folder layout (overlay, `{vault}/AGENTS.md`, or a quick look at the top-level folders), using the playbook's routing section.
- Between two candidate folders, propose one and ask once.

### 4. Write the note

- Load the cj-voice-dna skill before every write, if installed.
- Write in the language the user opened with, and stay in it unless they switch.
- Concise and scannable: practical headings, and the decisions, next steps, owners and dates the input carries.

### 5. Sync durable items

Only in `notes+ledger` or `ledger-only`, and only when `ledger` is installed. Distill atomic items; never copy the note body. See *Ledger sync*.

### 6. Report

List the files changed and any unresolved question that blocked a full sync. "Logged." is enough when the context is obvious.

### Planning and triage

When the user asks to plan their day or week, or what is due, read the open picture before planning: `now` (cj-now skill) covers repo `.plans/`, Things and Azure DevOps in one read-only call (`now --agent` for JSON, `now --grep <keyword>`, `now --full` for the backlog, `now --upcoming` for deferred work). Writing tasks back goes through cj-things.

---

## Ledger sync (optional)

Everything below applies only when `command -v ledger` succeeds. When it fails, run `notes-only`, mention once that durable memory needs the cognitive ledger, and offer the install:

```bash
brew tap damsleth/tap && brew install cognitive-ledger
ledger init --ledger-notes-dir <dir> --source-notes-dir <vault>
```

`ledger init` writes `~/.config/ledger/config.yaml`. If that file is missing or `ledger paths` errors on a machine that has `ledger`, surface the broken install to the user before reinstalling anything.

### Boot

1. `ledger paths --json` gives `ledger_root` (code, `templates/`, `schema.yaml`), `ledger_notes_dir` (the corpus, `{ledger}` below) and `source_notes_dir`. Use the literal resolved paths in commands; `$VAR` syntax triggers permission prompts.
2. Read `{ledger}/08_indices/context.md`: the essential facts, active loops and key preferences. For deeper lookups use `{ledger}/08_indices/index.md` or `index.json`, loaded on demand.
3. Before any write, run `sheep status`; when it says sleep is due, run `sheep sleep` and `sheep index` first. Pure queries skip this.

`ledger` and `sheep` read the config from any directory; stay in the user's working directory and leave unrelated repositories alone.

### Rules

- Write and update silently; audit with `git status` / `git diff` in `ledger_root` and show diffs only when asked.
- When conventions are unclear, read `{ledger_root}/AGENTS.md`, `schema.yaml`, `templates/`, and `{ledger}/08_indices/README.md`.
- Search before writing; prefer updating over creating.
- One idea per file; no transcripts. If several triggers occur, write several small notes.
- Never invent facts. Mark uncertainty with `source: inferred` and `confidence` below 0.7.
- Bump `updated` on every edit.
- Store note identifiers as logical `notes/<folder>/<file>.md` paths, wherever the corpus actually lives.
- Ask before creating many notes from one request; the default is one human note plus a few atomic ledger updates.

### Intent → artifact

| Signal | Artifact |
|---|---|
| Identity, mission, beliefs ("My mission is…", "I see myself as…") | `notes/01_identity/id__*.md` |
| Fact or decision ("We'll do X", "I decided…") | `notes/02_facts/fact__*.md` |
| Stable preference ("I prefer…", "Going forward…") | `notes/03_preferences/pref__*.md` |
| Goal or commitment with an outcome | `notes/04_goals/goal__*.md` |
| Unresolved, revisit later | `notes/05_open_loops/loop__*.md` |
| Concept or definition ("Let's define…") | `notes/06_concepts/concept__*.md` |

### Create or update

1. Search: `rg -l "<topic>" {ledger}` and `fd "<type>__|<slug>" {ledger}`.
2. New note: `ledger notes add --type <fact|pref|loop|concept|goal|id> --no-inbox --scope <scope> --tag <tag> --link <path> "<body>"`. It picks the slug, applies the template, files the note and logs the `created` timeline entry. Drop `--no-inbox` to stage in `00_inbox/` for triage.
3. Existing note: edit the file, bump `updated`, then log the change (below).

An open loop needs a `status` and a concrete `Next action` checkbox. When `things3_sync_enabled` is on in the ledger config, `ledger loops sync` mirrors loops to Things, routed by scope; set `things_list_id: <area-uuid>` in a loop's frontmatter to route it explicitly (`things areas --json` lists the ids).

### Timeline logging

`timeline.jsonl` is the source of truth and `sheep index` regenerates `timeline.md` from it, so log through the API, never by appending to `timeline.md`. For edits, closes, snoozes and archive moves, run the helper with the interpreter behind the `ledger` launcher:

```bash
"$(sed -n '1s/^#!//p' "$(command -v ledger)")" -c \
  "from ledger.embeddings import append_timeline_entry; \
   append_timeline_entry('updated', 'notes/<folder>/<file>.md', '<description>')"
```

Action is one of `created|updated|archived|deleted|closed|sleep`. Then `sheep sync --apply` resets the drift baseline. `ledger notes add` and `sheep index` log their own entries.

### Query

- Ranked retrieval first: `ledger query "<topic>" --scope all --limit 8` (`--scope personal|work|dev|home|meta` to narrow, `--bundle` for a compact cited pack), then `rg` / `fd` in the typed folder (`02_facts/` for history and decisions, `03_preferences/`, `05_open_loops/`, `06_concepts/`).
- Answer with citations to note paths. A pure query writes nothing.
- Before assuming anything about the user, search the ledger.
- When an answer drew on two or more notes and produced an insight none of them holds, ask whether to file it. On yes (or with `auto_file_synthesis` on), write a `concept__` or `fact__` note tagged `synthesized`, linked to its sources, `source: assistant`, `confidence: 0.8`.

### Signals

Log feedback only on clear evidence:

```bash
ledger signal add --type retrieval_hit --query "<query>" --note <path>
ledger signal add --type correction --note <path> --detail "<what's wrong>"
ledger signal add --type affirmation --note <path>
```

### Ingest a source

On "ingest this", "distill this article/meeting/doc": run `ledger ingest scan`, read the source, write 3 to 8 atomic notes tagged `ingested`, then `ledger ingest record <source> <note1> [note2...]`.

### Briefing

On "brief me", "what's on my plate", "what should I work on": `ledger briefing` (or `--weekly`). It lists open loops by staleness, the last day's changes, inbox items to triage and maintenance status.

### Maintenance

`sheep status` · `sheep sync --check` / `--apply` · `sheep sleep` (checklist) · `sheep lint` · `sheep index` (logs its own timeline events).

### Session wrap-up

Only when the user asks to capture, remember or wrap up the session: scan the session for decisions, stated preferences, new patterns, configuration choices, and diagnosed problems with their fixes. Search the ledger for each, then create or update the matching note. File a fact note for a completed multi-step task (what and why) and an open loop for unfinished work, with a concrete next action.
