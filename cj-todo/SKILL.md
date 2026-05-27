---
name: cj-todo
description: Quick, repo-scoped todo & plan tracker driven by the bundled `todo` script. Use when the user wants to jot down a task, mark work done, see what's open, or capture a larger piece of work as a plan — anything like "add a todo", "what's on my list", "mark that done", "/cj-todo", or "make a plan for X". Defaults to a one-line todo; only writes a plan file when the work is large or the user asks for one.
---

# cj-todo

## Overview

The world's most lightweight repo-scoped todo app. A bundled bash script (`todo.sh`)
does all the mechanical CRUD against `<repo-root>/.plans/`; your job is to (1) call it
with the right command and (2) decide whether something is a quick todo or warrants a
plan. Stay terse — the whole point is speed.

Storage (per git repo):
- `.plans/TODO.md` — open work (todos + one index line per plan)
- `.plans/DONE.md` — completed items, archived with a date
- `.plans/<slug>.md` — a detail file per plan

## The script

Invoke the bundled script. If `todo` is on PATH use it directly; otherwise call the
script by path (`./todo.sh` inside this skill folder, or wherever it's installed).

```bash
todo                  # list open todos & plans (default)
todo add "<text>"     # add a todo
todo plan "<name>"    # create a plan file + index it; prints the file path
todo done <n>         # complete item #n (moves it to DONE.md)
todo rm <n>           # delete item #n without archiving
todo log              # show completed items
todo where            # print the .plans directory
todo install          # symlink the script as `todo` on PATH (~/.local/bin)
```

Item numbers come straight from `todo` / `todo list` output — always list first if you
need a number you don't already have.

## Todo vs. plan — the one judgment call

Default to a **todo** (`todo add`). Reach for a **plan** (`todo plan`) only when:

- the user explicitly says "plan", "make a plan", "write a plan", or similar, **or**
- the work is large/multi-step enough that it should be thought through before doing it
  (e.g. "rewrite the auth layer", "migrate to the new API") rather than a single action.

When in doubt, add a todo — it's cheaper to promote later than to over-ceremony a
one-liner.

## Workflow

1. **Add a todo** — `todo add "<concise task>"`. Keep the text short and imperative.
2. **Add a plan** — `todo plan "<name>"`, then open the printed file and fill in the
   `## Goal` / `## Steps` / `## Notes` sections with a real, actionable plan based on
   what the user described. Leave a useful skeleton, not lorem ipsum.
3. **Complete / remove** — run `todo` to see numbers, then `todo done <n>` (or `rm`).
4. **Review** — `todo` for open work, `todo log` for finished work.

## Guardrails

- Don't hand-edit `TODO.md` / `DONE.md` for add/done/rm — use the script so numbering
  and archiving stay consistent. You *may* edit a plan's own `.plans/<slug>.md` freely.
- Keep responses tight: confirm the action in a line or two, don't restate the whole list
  unless asked.
- The store is per-repo (resolved via `git rev-parse --show-toplevel`, falling back to the
  current directory). If the user expects a list and it's empty, they may be in the wrong
  repo — say so rather than assuming.
