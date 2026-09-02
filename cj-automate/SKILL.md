---
name: cj-automate
description: Audit a workflow or process and propose automations, ordered by leverage — remove humans from transport steps first, collapse waits second, optimize speed last. Use when the user describes something repetitive, asks "can this be automated?", complains about a manual process, or wants to find automation candidates across their setup.
---

# Automation auditor

Decompose a workflow into steps, then propose automations in a fixed order of leverage.

Most automation advice starts with "make the slow step faster." That is the last move, not the
first. A step that a machine can do at all should not have a human in it, and a step that waits
three days for a human is a latency problem that no amount of optimization touches.

## Rule zero: get a real trace, not a description

Never audit an abstraction. "My invoicing process" is not auditable; a numbered list of what
actually happened the last three times is. If the user describes the workflow in the abstract,
ask for one concrete run before analyzing anything.

For each step, you need:

| Field | Why |
|---|---|
| **What happens** | The actual action, in verbs. "Copies the total into the spreadsheet", not "reconciliation". |
| **Actor** | Human, machine, or a human waiting on a machine. |
| **Trigger** | Scheduled, event-driven, or someone remembering. |
| **Duration** | Hands-on time. |
| **Wait** | Elapsed time before the next step starts. Usually much larger than duration, and usually ignored. |
| **Frequency** | Per day/week/month. |

Estimates are fine. Precision is not the point; the ratios are. If the user does not know a
number, guess out loud and mark it as a guess.

Where you can observe the workflow directly instead of asking — shell history, git log, a
scripts directory, an inbox, cron/launchd entries, the Things database — do that first and bring
a draft trace to the conversation. A trace you derived and they corrected beats a trace they had
to write from memory.

## Rule one: classify what the human is actually doing

For every human step, decide which of these it is. This single distinction drives most of the
findings:

- **Transport** — moving data between systems. Copy/paste, re-typing, downloading then
  uploading, reformatting, forwarding, "checking if X happened yet". The human is a network
  cable. *Always automatable. Start here.*
- **Judgment** — a decision that needs context the machine does not have. *Not directly
  automatable, but usually reducible; see rule two.*
- **Ceremony** — the step exists because it always has. Sign-offs nobody reads, statuses nobody
  queries, reports nobody opens. *Delete, do not automate.*

State the classification for each step explicitly. If you cannot tell whether something is
judgment or transport, ask: "what would go wrong if this were done automatically?" A vague
answer means transport. A specific failure means judgment.

## Rule two: the ladder, in this order

Work down. Do not skip to the bottom because the bottom is the fun part.

### 1. Delete the step
Does it need to exist at all? Ceremony steps die here. So do steps that exist only to feed a
later step you are about to automate away. Deleting a step beats automating it every time,
and it is the only move with negative maintenance cost.

### 2. Remove the human from the step
Every transport step. This is where the bulk of real savings live and it is usually the least
interesting work, which is why people skip it.

### 3. Collapse the wait
A step with 2 minutes of duration and 2 days of wait is a 2-day step. Waits come from batching,
from approvals, from "I'll do it tonight", and from polling something that could push instead.
Attack the wait before the duration — a 2-day wait cut to 2 hours dwarfs any speedup of the
2 minutes.

For judgment steps that cannot be automated, this is where they get reduced instead:
- **Batch** the decisions so the wait happens once, not per item.
- **Narrow** the decision — present three options instead of a blank page.
- **Invert the default** — act automatically, let the human veto. Only safe when the action is
  reversible; say so explicitly when you propose it.

### 4. Then optimize speed
Only now. Caching, parallelism, a faster tool, a better algorithm. If you find yourself here on
step one of the analysis, go back to the top.

## Rule three: weight by frequency, and say what you are not doing

Sort findings by `duration × frequency` saved, plus wait eliminated. A 5-minute monthly task is
1 hour a year and is almost never worth automating — say so plainly rather than proposing
something polite. Explicitly list the steps you looked at and chose to leave alone; a report
that only contains proposals reads as if everything needs work.

Flag anything where automation adds risk the manual version did not have: irreversible actions,
things touching money or credentials, anything where a silent failure looks like success. Those
need a check, not just a script.

## Output

```markdown
## Trace
[numbered steps, one line each: what · actor · duration · wait · frequency · class]

Total: [X] min hands-on per [period], [Y] elapsed.

## Findings
### 1. [What to change] — [delete | de-human | collapse wait | speed up]
Step(s): [n]. Saves: [X min/period, or "Y days of wait"].
How: [one or two sentences, concrete enough to start]
Risk: [only if there is one]

## Left alone
- Step [n]: [one-line reason]
```

Order findings by leverage, not by step number.

## Anti-patterns

- **Proposing a tool before tracing the workflow.** The tool is the last decision, not the first.
- **Automating the interesting step.** The interesting step is usually judgment. The boring one
  is usually transport, and transport is where the hours are.
- **A pipeline that needs babysitting.** An automation with a human watching it is a transport
  step wearing a costume.
- **Ignoring the wait column** because duration is easier to measure.
- **Proposing an LLM for something a `for` loop does.** If the step is deterministic, keep it
  deterministic — it is cheaper, faster, and it fails loudly instead of plausibly.
- **Automating something the user does twice a year.** Say no.

## Notes for this setup

The user has substantial existing automation surface; check whether a proposal is already
covered before proposing it:

- `owa-piggy` + `owa-tools` — 16 `owa-*` CLIs over M365 (cal, mail, graph, drive, todo, planner,
  sites, teams, places, people, sched, ado, vids). Auth needs no app registration. JSON by
  default, so they pipe. See the `cj-owa-tools` skill.
- `things3-cli` (`things`) — read/write access to Things 3, including a JSON mode.
- `teaminal` — Teams TUI.
- launchd is the established scheduler here (owa-piggy already uses it), not cron.
- Existing `cj-*` skills cover daily notes, meetings, weekly review, blogging, and voice.

Prefer wiring these together over building anything new. A proposal that is three existing CLIs
in a pipe is a better finding than one that needs a new repo.
