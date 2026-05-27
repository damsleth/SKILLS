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

Storage (per git repo). It's **filesystem-first** — plans are just files, so
hand-maintained `.plans/` dirs work without conversion:
- `.plans/TODO.md` — open one-line todos (`- [ ]` checkboxes)
- `.plans/DONE.md` — completed todos, archived with a date
- `.plans/<name>.md` — one file per plan; the file *is* the unit of work
- `.plans/done/` — completed plans (files moved here)

`todo` lists every `.plans/*.md` file as a plan, whether the script created it
or someone dropped it in by hand. It deliberately does **not** parse prose
bullets or numbered lists into todos, so a narrative `TODO.md` that just indexes
or orders plan files is left untouched.

## The script

Invoke the bundled script. If `todo` is on PATH use it directly; otherwise call the
script by path (`./todo.sh` inside this skill folder, or wherever it's installed).

```bash
todo                  # list open todos & plans (default)
todo add "<text>"     # add a todo
todo plan "<name>"    # create a plan file (.plans/<slug>.md); prints the path
todo done <n>         # complete #n (todo → DONE.md, plan file → .plans/done/)
todo rm <n>           # delete #n (todo line, or plan file)
todo log              # show completed todos & plans
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
2. **Add a plan** — `todo plan "<name>"` creates `.plans/<slug>.md`; open the printed
   file and fill in the `## Goal` / `## Steps` / `## Notes` sections with a real,
   actionable plan based on what the user described. Leave a useful skeleton, not lorem
   ipsum. (Completing a plan later moves the whole file into `.plans/done/`.)
3. **Complete / remove** — run `todo` to see numbers, then `todo done <n>` (or `rm`).
4. **Review** — `todo` for open work, `todo log` for finished work.

## Guardrails

- Don't hand-edit `TODO.md` / `DONE.md` for add/done/rm — use the script so numbering
  and archiving stay consistent. You *may* edit a plan's own `.plans/<name>.md` freely.
- `todo rm <n>` on a plan **deletes the file**; `todo done <n>` archives it to
  `.plans/done/`. Prefer `done` unless the user wants it gone for good.
- Keep responses tight: confirm the action in a line or two, don't restate the whole list
  unless asked.
- The store is per-repo (resolved via `git rev-parse --show-toplevel`, falling back to the
  current directory). If the user expects a list and it's empty, they may be in the wrong
  repo — say so rather than assuming.
