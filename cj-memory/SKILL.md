---
name: cj-memory
description: Generic memory-recall skill that routes through the mnem suite (yaams + cognitive-ledger). Use before answering questions about people, projects, decisions, or recurring topics the user has discussed before. Returns grounded, cited answers if mnem is configured; gracefully no-ops if not. No personal references baked in — the suite reads whatever the user ingested.
version: 1.0.0
author: damsleth
allowed-tools:
  - Bash
tags:
  - memory
  - recall
  - context
  - mnem
---

# cj-memory

Personal memory recall via the mnem suite. Use this skill before
answering questions that touch the user's history: people, projects,
past decisions, recurring topics. mnem aggregates two tiers of memory:

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
# Doctor first - confirms mnem and its components are healthy.
mnem doctor

# Recall (the most common verb)
mnem query "what did we decide about X" --answer
mnem query "Y" --top-k 20 --answer
mnem query "Z" --tier ledger     # only curated notes
mnem query "Z" --tier raw        # raw signals only

# Ingest fresh signals before asking, if recall came up empty
mnem ingest

# List candidates the user could promote to the curated layer
mnem promote list
```

`--answer` synthesizes a grounded response with citations. Omit it
to get raw results you can reason over yourself.

## Setup check

If `mnem doctor` reports `no mnem config found`, walk the user
through:

```bash
mnem init
```

The wizard probes for iMessage, Apple Mail, Signal, GitHub,
owa-piggy profiles, Obsidian vaults, and the cognitive-ledger - it
writes a config under `~/.config/mnem/yaams/config.yaml` with
`enabled: true/false` per detected source, then runs a dry-run
ingest so the user can see what's about to land.

## Output contract

Every `mnem` verb follows the mnem CONVENTIONS contract:

- `--json` puts output in machine mode.
- Data commands emit raw JSON documents (no top-level `ok`).
- Action commands emit `{ok, stats, error, ...}` envelopes.
- `mnem ingest --json` streams NDJSON: progress lines + a final
  `{type:"result", ...}` envelope.
- Exit codes: 0 ok, 1 user error, 2 transient, 3 auth, 4 not found,
  5 partial success.

## When NOT to use this skill

- Pure code tasks with no reference to user history.
- The user is asking you to do something fresh (write, refactor,
  debug) without needing prior context.
- mnem isn't installed (`which mnem` returns nothing). Don't try to
  install it inline; suggest `brew install damsleth/tap/mnem` or
  `pipx install mnem-suite` and move on.
