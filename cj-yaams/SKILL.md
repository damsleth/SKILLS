---
name: cj-yaams
description: Query personal memory via YAAMS for context about people, projects, topics, and decisions. Use before working on tasks where background knowledge would help — recurring projects, known contacts, past decisions, or anything the user has mentioned before. Returns grounded, cited answers from a two-tier memory store (raw signals + curated notes).
version: 1.0.0
author: damsleth
allowed-tools:
  - Bash
tags:
  - memory
  - recall
  - context
  - personal-knowledge
---

# cj-yaams

Personal memory recall. Query before starting tasks involving people, projects, or recurring topics. YAAMS ingests iMessage, email, Teams, Obsidian notes, and curated atomic notes — and returns cited answers grounded in the user's actual history.

## When to use

- Starting work on a project the user has mentioned before
- The user references a person, org, or project by name and you want context
- The user asks "what do you know about X" or "remind me about Y"
- You're writing something and want to check past decisions or preferences
- After a conversation, when something worth remembering came up

## Query

```bash
yaams query "what do I know about NOCOS" --answer
yaams query "who is Vibeke"
yaams query "latest GTH deployment status" --since 2026-01-01 --answer
yaams query "BRKH decisions last quarter" --top-k 20 --answer
yaams query "Kim's preferences for meeting formats"
```

`--answer` asks the LLM to synthesize a cited response. Omit it to get raw results you can reason over yourself.

### Key flags

| Flag | Default | Use for |
|------|---------|---------|
| `--answer` | off | Grounded synthesis with citations |
| `--top-k N` | 10 | Broader topics needing more signal |
| `--since YYYY-MM-DD` | - | Recency-filtered queries |
| `--source NAME` | - | One ingest source only (imessage, email, teams, notes) |
| `--tier {1,2,both}` | both | 1 = raw signals, 2 = curated notes only |

### Reading results

- `source: tier2_ledger` - curated atomic note, high confidence, treat as fact
- `source: imessage / email / teams / notes` - raw signal, use as context but verify before asserting
- Each result shows `sender`, `timestamp`, and a content snippet
- `--answer` output includes inline citations `[1]`, `[2]` linked to the result list

## Context priming pattern

Before starting a non-trivial task involving a known entity, prime context first:

```bash
# Who is involved, what's the history?
yaams query "everything about <project or person>" --answer --top-k 20

# Then proceed with the task, informed by the output
```

This is especially useful for: project work with history, emails to known contacts, meeting prep, code reviews on known systems.

## Entity dictionary

Entities are the lens YAAMS uses to cluster signals into promotion candidates. If someone or something comes up repeatedly and isn't tracked yet:

```bash
yaams entities list                         # what's currently tracked, with hit counts
yaams entities add "GTH" --type project
yaams entities add "Vibeke" --type person --alias "Vibeke Sørensen"
yaams entities discover                     # interactive: scan NER tags and approve candidates
yaams entities discover --min-count 3       # lower bar, more suggestions
```

Changes take effect immediately - no reingest needed.

## Promotion

When enough signals accumulate around an entity, YAAMS can draft an atomic note for Tier 2:

```bash
yaams promote generate           # draft candidates via LLM (~30s per entity, shows progress)
yaams promote generate --days 90 --entity "NOCOS"   # single entity, wider window
yaams promote list               # what's pending review
yaams promote review             # interactive: accept / edit / reject
```

Accepted notes land in `~/brain/ledger/00_inbox/` for final human sign-off before entering Tier 2. Nothing is promoted without explicit acceptance.

## Stats and maintenance

```bash
yaams stats                      # item counts, DB size, last ingest per source
yaams ingest                     # re-ingest all enabled sources
yaams ingest --source imessage   # single source
```

## Notes

- Installed via pipx - `yaams` runs anywhere without venv activation
- DB is at `~/brain/yaams/data.db` (single SQLite file, append-only)
- Config is at `~/code/YAAMS/config.yaml`
- Two-tier architecture: YAAMS = Tier 1 (high volume), cognitive-ledger = Tier 2 (curated). Fused at query time with a small Tier 2 boost.
