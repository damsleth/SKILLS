# Lesson routing

Use for corrections, recurring mistakes, or a requested session wrap-up.
Route each lesson before writing memory. Search existing notes and inspect
the relevant procedure or code first.

| Lesson | Destination | Completion criterion |
|---|---|---|
| Mechanically detectable mistake | `structural_check` | Name the test, lint rule, script, or runtime guard and target |
| Incorrect skill procedure | `skill` | Identify the skill section and concrete correction |
| Durable fact, preference, decision, goal, or definition | `note` | Identify an existing note or the appropriate atomic note type |
| Unfinished work | `task` | Name a next action and the task system required by the user's routing policy |
| Temporary, unsupported, or already captured information | `skip` | State why no new artifact is useful |

Prefer a structural check when it can enforce the whole lesson. A skill
correction belongs in the skill rather than a second copy of its procedure
in memory. A separate durable rationale may still warrant its own note.
Preserve existing human-note and task-routing rules.

Return one object per lesson:

```json
{
  "lesson": "The commit helper must reject an empty message before staging.",
  "destination": "structural_check",
  "target": "path/to/helper",
  "reason": "Argument validation can enforce this before any Git write.",
  "evidence": ["user correction in the current session"],
  "status": "proposed"
}
```

Evidence is a short source locator, never a transcript. Use logical
`notes/...` identifiers for ledger notes. For `skip`, the target may be null.
State uncertainty instead of inventing evidence.

Apply changes within the user's authorised scope. Otherwise leave a concrete
proposal; capturing a lesson does not authorise edits to unrelated projects.
When an improvement queue item exists, link the resulting artifact with
`ledger improvements resolve <id> --artifact <reference>`. Use an explanation
when no file artifact exists. Keep the item open while work remains.
