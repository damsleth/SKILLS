# Question Playbook

Ask only the high-value questions below that the input leaves open, then write one clear note.

## Core intake

1. What is the note for (meeting, decision, plan, idea, journal, or reference)?
2. Where should it live in the vault?
3. What must be captured exactly (facts, dates, names, links)?
4. What outcome should this note support?

## By intent

### Meeting

1. Who attended?
2. What decisions were made?
3. What are the next actions, owners, and due dates?

### Project update

1. What changed since the last update?
2. What is blocked, and by whom?
3. What is the next milestone and date?

### Decision

1. What was decided?
2. Why?
3. Which alternatives were rejected?

### Idea

1. What problem does it solve?
2. What is the smallest test?
3. What would make it worth revisiting?

### Journal

1. What happened?
2. What mattered?
3. What follow-up is needed, if any?

## Folder routing

The overlay or `{vault}/AGENTS.md` names the vault's folders; otherwise read the top-level folders and map them to these roles. The default layout uses numbered folders, so topic folders sort first and system folders last:

| Role | Default folder |
|---|---|
| Temporary scratch | `00-tmp/` |
| Personal and home topics | `01-home/` |
| Work topics, one subfolder per customer or employer | `02-work/<customer>/` |
| Development topics | `04-dev/` |
| Daily journal: dated events only (week notes `YYYY-Www.md` sit beside the dailies) | `90-journal/` |
| Agent and tool logs, one `YYYY-MM-DD.md` per day, kept out of the journal | `93-log/` |
| Plans under discussion | `95-plans/` |

Other top-level folders (a volunteer organisation, an archive) follow the same numbering; read them off the vault.

Durable reasoning goes in a running note under the topic folder, not in the dated journal entry (see *Where things go* in SKILL.md). When the destination is ambiguous, propose one folder and ask once.

Durable items extracted from the note map to ledger artifacts per *Intent → artifact* in SKILL.md.
