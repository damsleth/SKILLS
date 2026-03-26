---
name: notes-ledger-sync
description: Capture and refine notes while synchronizing durable memory through the cognitive-ledger skill. Use when asked to create, update, summarize, or structure notes and keep associated facts, preferences, concepts, decisions, goals, or open loops in sync by asking targeted follow-up questions before writing.
---

# Notes + Ledger Sync

Coordinate two repositories in one flow:

- Human-facing notes: `$NOTES_DIR` (default: `~/Code/notes`)
- Structured memory ledger: `$LEDGER_DIR` (default: `~/Code/cog-led`, via `cognitive-ledger`)

> **Setup:** Set `NOTES_DIR` and `LEDGER_DIR` environment variables or edit the defaults above to match your directory layout.

Keep notes readable for humans and ledger entries atomic for retrieval.

## Follow This Workflow

1. Classify the request.
- Detect note intent: meeting, project update, decision, idea, plan, journal, or cleanup.
- Decide write scope: `notes-only` or `notes+ledger` (default to `notes+ledger` when durable memory is implied).

2. Ask targeted questions before writing.
- Ask only what is missing.
- Use at most 5 questions in one batch.
- Pull prompts from `references/question-playbook.md`.
- Prefer specific prompts over generic "anything else?" prompts.

3. Choose the note destination in `$NOTES_DIR`.
- Route using `references/question-playbook.md`.
- Search for existing notes first and prefer updating over creating duplicates.
- When uncertain between two folders, propose one default and ask for confirmation.

4. Write or update the note in `$NOTES_DIR`.
- Keep content concise and scannable.
- Use practical headings; avoid template bloat.
- Include decisions, next steps, owners, and dates when present.

5. Sync durable items to `$LEDGER_DIR`.
- Use `cognitive-ledger` for all ledger writes.
- Distill only durable memory from the note; do not copy full note text.
- Map extracted items to artifact types in `references/question-playbook.md`.
- Let `cognitive-ledger` handle timeline updates and frontmatter conventions.

6. Return a short completion summary.
- List files changed in both repositories.
- Highlight unresolved questions that blocked full sync.

## Operational Rules

- Read `$NOTES_DIR/AGENTS.md` before first write to notes when context is unclear (if it exists).
- Ask before creating many new notes from one request; default to one canonical note plus atomic ledger updates.
- Never invent facts; mark uncertain interpretations as inferred when writing to the ledger.
- If a request is pure drafting with no durable memory, skip ledger writes and state that explicitly.

## Quick Commands

Use these commands to minimize duplicate notes:

```bash
rg "<topic>" $NOTES_DIR -l
rg "<topic>" $LEDGER_DIR/notes -l
```

For ledger actions, follow `cognitive-ledger` workflows and defaults.
