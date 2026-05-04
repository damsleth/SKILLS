---
name: notes
description: Backward-compatibility alias for `cj-notes`. Use only when the user explicitly invokes `/skill:notes`; otherwise use `cj-notes`.
disable-model-invocation: true
---

# Alias: notes -> cj-notes

This skill name is kept as a backward-compatibility alias.

When this alias is invoked:

1. Immediately read `../cj-notes/SKILL.md`.
2. Follow `cj-notes` as the canonical implementation.
3. Treat `cj-notes` as the authoritative skill name in any follow-up guidance or cross-skill references.
