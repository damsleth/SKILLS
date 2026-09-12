---
name: cj-now
description: One canonical, read-only view of everything open across repo .plans/, Things 3 and Azure DevOps work items, keyed on owa-piggy profile. Use when the user asks "hva er aktuelt nå", "hva jobber jeg med", "vis alle oppgaver", "status på tvers", "/cj-now", or when you need to know whether a piece of work already has a task somewhere before creating a new one. Read-only: it never writes to any source.
---

# cj-now

`now` projects three task surfaces into one list. It is a projection, not a
store. Nothing is written and nothing is synced, so nothing can drift.

```
now                     open work, grouped by profile, 10 rows each
now --profile une       one profile, uncapped
now --source plans      one source (plans | things | ado), repeatable
now --grep 18520        search title and id, every profile, unfiltered
now --full              no row cap, and no Things relevance filter
now --dupes             only the rows that duplicate an ADO work item
now --upcoming          only Things tasks scheduled to start later
now --all               include non-work profiles (brkh, dno, fdep)
now --agent             JSON, owa-suite envelope
now --no-cache          force a fresh ADO fetch
```

## Sources

| Source | Read from | Cost | Authority |
| --- | --- | --- | --- |
| `plans` | `<repo>/.plans/TODO.md` + `<repo>/.plans/*.md` | filesystem | repo work, 1:1 with a git repo; `ado:` frontmatter links a plan to its work item |
| `things` | `things all --json` | local sqlite | personal tasks, human-owned |
| `ado` | `owa-ado wi --agent --mine` | network, cached 15 min | team work items, **not yours** |

Each source stays authoritative for its own domain. `now` never reconciles them
and never picks a winner.

The ADO adapter is a plain passthrough to `owa-ado wi --mine`, which follows
assignment across every project in the organisation. It used to carry its own
cross-project WIQL, because `--mine` was pinned to the single project in
`~/.config/owa-ado/config` and hid everything else. That belonged one layer
down and was fixed in owa-ado, so `now` no longer knows anything about how ADO
scopes a query.

Closed, Removed and Done are dropped here rather than in the query. Resolved is
not: it means fixed but still sitting on the board waiting to be verified, which
is exactly the item that needs a last push.

## The join key is the profile

A repo, an ADO project and a Things area all map to one owa-piggy profile. That
is the only axis all three share, and it is what makes a merged list coherent.

The mappings are personal wiring, not tool logic, so they live in
`~/.config/cj-now/config.json` (stowed from `dotfiles-private/cj-now/`):

```json
{
  "work_profiles":    ["acme", "acme-misc"],
  "fallback_profile": "personal",
  "ado_profile":      "acme",
  "repo_profiles":    [["code/acme/api/", "acme"], ["code/acme/", "acme-misc"]],
  "area_profiles":    {"ACME": "acme"}
}
```

`repo_profiles` is a list of pairs rather than an object because first match
wins, so order carries meaning: put the specific prefixes above the general
ones. `ado_profile` is the single profile `owa-ado` is configured against.

With no config file every profile counts as work and every repo falls back to
`local`, so the tool runs anywhere. Nothing here knows a customer name: the ADO
organisation is read off the work item urls that `owa-ado` already returns.

## Reading the output

Sort order is how a human triages. A deadline inside 14 days jumps the queue;
everything else falls back to most recently touched. `2026-09-11` in the last
column is a deadline, `17d` is how long since anything moved.

Things reports Today and Upcoming only as group titles: the items inside still
say start=Anytime or Someday. Both are read from the group, so `status` says
`today` or `upcoming`, and an upcoming task carries `starts` with the date it
arrives. An upcoming task earns a row in the normal view the same way anything else
does, so one deliberately scheduled for the 21st stays out until its deadline or
its start brings it in. `--upcoming` is how you look ahead on purpose: it skips
the relevance filter, since that filter is precisely what hides deferred work,
and leads each row with the date the task arrives.

A Things task shows up only if it has a deadline, sits in Today, or duplicates
an ADO work item. Anything and Someday with no date is backlog Kim keeps in
Things on purpose, and it used to bury the work items. `--full` brings it back.

A `.plans/` directory is a document library as much as a task list, so the same
rule applies: `TODO.md` lines are tasks and always show, a plan file is the
document *about* work and shows when its `ado:` frontmatter names an open work
item. Across every repo that is 90 plan files against 76 todo lines. `--full`
and `--grep` bring them back.

## Size

`now --agent` is the work view, around 26 KB. `now --agent --all` adds every
personal profile and roughly triples that, which is `--all` doing its job rather
than a problem to work around. Scope with `--profile` or the default work view;
reaching for `--source things` to control size silently drops ADO and plans.

`⧉` marks a row that points at an ADO work item also in the list, via a plan's
`ado:` frontmatter or an id in the title that is also in the list, and
the footer counts them. Both rows stay visible: the duplicate comes from
tracking one piece of work in two places, and seeing it is what prompts closing
the Things copy. Expect these to fade as work items stop being copied into
Things.

`--grep` is a search, so it runs before the relevance filter and across every
profile: naming a needle means look everywhere. `--full --all` is not needed to
make a search work.

`--dupes` lists them and names the work item each one shadows, which is the
cleanup list. From an agent, prefer `--agent`: every record carries `dupe_of`
with the id it duplicates, so the duplicates are a filter away and never need
grepping out of the rendered table.

Drift shows up on its own, no detector needed. A plan touched 2 days ago sitting
next to its Things task untouched for 17 days in Someday is the signal. Read it
and close the stale side.

## For agents

- Use `--agent` and read `data[]`. Every record has `id`, `source`, `title`,
  `profile`, `status`, `updated`, `deadline`, `url`, plus source-specific extras.
- Ids are stable and source-prefixed: `plans:<repo>/<slug>`, `things:<uuid8>`,
  `ado:<id>`.
- **Check `_owa.warnings` before trusting a gap.** A source that is down is
  reported there, never silently dropped. An expired profile token yields
  `owa-piggy reseed --profile <name>`, which only the user can run.
- Before creating a task, run `now --grep <keyword>` to see whether one exists.
  The search already spans every profile and the filtered-out backlog, so no
  flags are needed to make a dedupe check see everything.
- After finishing work, close it in the source that owns it, not here.
- **Writes and the logbook live in the source skill.** Creating, completing or
  editing a Things task, and any completed-work view, is `cj-things`; a work
  item is `cj-owa-ado`; a plan or todo line is `cj-todo`.

## Deliberately not built

Write-back, pinning, a link file between related records, and drift as a
subcommand. Add them when the read-only view proves it needs them, not before.
