---
name: cj-things3-read-tasks
description: Read and search Things3 tasks with the installed things-cli in read-only mode. Use when asked to list tasks, inspect Today, run keyword search, export todos as JSON, filter by project/area/tag, or summarize task state from Things3 data.
---

# cj-things3-read-tasks

## Overview

Use the installed `things-cli` to retrieve and analyze Things3 tasks without modifying data.
Prefer text output for quick human-readable lists and JSON output for structured analysis.

## Quick Start

Run the core commands first:

```bash
things-cli today
things-cli search "query text"
things-cli -j todos
```

Use `things-cli --help` when the request needs a less common command.

## Workflow

1. Confirm CLI access.
2. Select the narrowest command that answers the request.
3. Add filters (`-p`, `-a`, `-t`) when scope is unclear or too broad.
4. Switch to JSON (`-j`) when you need counts, grouping, or field-aware summaries.
5. Return a concise summary and include notable task metadata (project/area, dates, status).

## Command Selection

Use these commands by intent:

- `things-cli today`: Current focus list.
- `things-cli search "<text>"`: Find tasks by keyword.
- `things-cli -j todos`: Export all todos as JSON for parsing and summarization.
- `things-cli inbox|upcoming|anytime|someday|completed|deadlines`: Read a specific bucket.
- `things-cli projects|areas|tags`: Inspect organization metadata.
- `things-cli logtoday|createdtoday|logbook`: Review recent activity.

See `references/commands.md` for the full catalog and flags.

## Output Handling

When using JSON output, expect task objects with fields such as:

- `uuid`, `type`, `title`, `status`
- `project` / `project_title` or `area` / `area_title`
- `notes`, `tags`
- `start`, `start_date`, `deadline`, `stop_date`
- `created`, `modified`

Handle missing keys gracefully because fields vary by task type and location.

## Guardrails

- Keep operations read-only. Do not attempt mutation commands.
- Avoid dumping very large JSON directly; summarize and include only relevant slices.
- Redact or minimize personal details when sharing task output unless explicitly requested.
