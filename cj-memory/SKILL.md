---
name: cj-memory
description: Generic memory-recall skill that routes through the hugr suite (yaams + cognitive-ledger). Use before answering questions about people, projects, decisions, or recurring topics the user has discussed before. Returns grounded, cited answers if hugr is configured; gracefully no-ops if not. No personal references baked in — the suite reads whatever the user ingested.
version: 1.0.0
author: damsleth
allowed-tools:
  - Bash
tags:
  - memory
  - recall
  - context
  - hugr
---

# cj-memory

Personal memory recall via the hugr suite. Use this skill before
answering questions that touch the user's history: people, projects,
past decisions, recurring topics. hugr aggregates two tiers of memory:

- **Tier 1 (yaams)**: raw signals - iMessage, email, calendar,
  GitHub, notes. High volume, full recall.
- **Tier 2 (cognitive-ledger)**: curated atomic notes. Lower volume,
  higher precision, immutable history.

## When to use

- The user references a person, project, or topic by name and you want
  context before responding.
- "What do you know about X?" / "remind me about Y" / "have I worked
  on Z?"
- Starting work on something the user has mentioned in a past
  conversation.
- Drafting a message and you want to check past tone / decisions.

## Quick verbs

```bash
# Doctor first - confirms hugr and its components are healthy.
hugr doctor

# Recall (the most common verb)
hugr query "what did we decide about X" --answer
hugr query "Y" --top-k 20 --answer
hugr query "Z" --tier ledger     # only curated notes
hugr query "Z" --tier raw        # raw signals only

# Ingest fresh signals before asking, if recall came up empty
hugr ingest

# List candidates the user could promote to the curated layer
hugr promote list
```

`--answer` synthesizes a grounded response with citations. Omit it
to get raw results you can reason over yourself.

## Setup check

If `hugr doctor` reports `no hugr config found`, walk the user
through:

```bash
hugr init
```

The wizard probes for iMessage, Apple Mail, Signal, GitHub,
owa-piggy profiles, Obsidian vaults, and the cognitive-ledger - it
writes a config under `~/.config/hugr/yaams/config.yaml` with
`enabled: true/false` per detected source, then runs a dry-run
ingest so the user can see what's about to land.

## Output contract

Every `hugr` verb follows the hugr CONVENTIONS contract:

- `--json` puts output in machine mode.
- Data commands emit raw JSON documents (no top-level `ok`).
- Action commands emit `{ok, stats, error, ...}` envelopes.
- `hugr ingest --json` streams NDJSON: progress lines + a final
  `{type:"result", ...}` envelope.
- Exit codes: 0 ok, 1 user error, 2 transient, 3 auth, 4 not found,
  5 partial success.

## When NOT to use this skill

- Pure code tasks with no reference to user history.
- The user is asking you to do something fresh (write, refactor,
  debug) without needing prior context.
- hugr isn't installed (`which hugr` returns nothing). Don't try to
  install it inline; suggest `brew install damsleth/tap/hugr` or
  `pipx install hugr-suite` and move on.
