---
name: cj-ambition
description: Raise the ambition of the current task along one axis before executing it — altitude (zoom out to the goal beyond the goal), depth (deeper not bigger, the way the best in the field would), or range (bring in other disciplines, assemble the crew). Use when the user says "be more ambitious", "zoom out", "go deeper", "bring in other fields", "/cj-ambition <axis>", or hands over a task that reads like a template to fill in.
---

# Ambition

Rewrite the task along one axis, show the rewrite, then execute it. Distilled from
[How to be more ambitious](https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/)
by Felix Rieseberg. Speed (same work, less time) is the default already and gets no section.

Pick the axis from the argument (`altitude`, `depth`, `range`). No argument: pick by the tells
below and say which one you picked. One axis per pass; stack passes if the user asks.

## Altitude — the goal beyond the goal

The task as given is the user's best guess at how to reach an outcome. Work on the outcome.

Tell: there will be a meeting about this. A deck, a report, a status update, a fix for one
crash. Creative work resists altitude; leave it alone there.

1. Name the outcome the task serves, and what should happen next once it is delivered.
2. Rewrite the task at that level. Each step up is a real jump:
   - *Fix this crash* → *keep the app crash-free*.
   - *Fill the QBR template* → *say what changed, why, and what to do about it* → *name the
     three most urgent decisions and work out for/against* → *design a better way for
     leadership to catch problems early, prove from our own history it would have, run it
     beside the current one*.
3. Name the durable loop that keeps the human out: what data access, tools, or environment
   the agent needs to own the outcome repeatedly, not once. Ask for it.

Done when the rewrite names the outcome, the next action it unlocks, and the loop.

## Depth — deeper, not bigger

Do the task the way a field-leading expert would, touching the raw material and the real
instruments, until the expert would learn something from the result.

Tell: the first draft reached for a summary, a markdown table, or expert vocabulary without
expert method.

Answer four questions, then rewrite the task to ask for exactly that:

1. What would a top professional in this field do here that is not being asked for?
2. What is the rawest material they would start from, instead of what has been digested
   already? Get that material.
3. Which specific methods and tools would they use? Use those: a database and a statistical
   model, not a table; a simulation, not a guess. Install what is missing.
4. What, other than the agent or the user, shows the result is right? Name a runnable
   external check before starting. Self-review is not verification.

Techniques while executing:

- **Set the target an order of magnitude past the ask** and treat it as solvable. 10s → 5s
  becomes 200ms. Keep going when it looks impossible.
- **Challenge what is believed.** "We think churn is an onboarding problem": reproduce that
  from raw data, adversarially.
- **Produce new knowledge** once inside the data: build a model that reproduces last year,
  find the earliest signal nobody has named, show it predicts on unseen data.

Done when the rewrite names the raw source, the instrument, and the external judge. Three
named things, or it is not depth.

## Range — assemble the crew

Look at the task from more fields than would have been economical before.

Tell: the task is being done entirely inside its home discipline.

1. **Replace the nouns with verbs.** A QBR is not "a deck"; it is "getting busy people to
   believe a story about cause and effect and decide under uncertainty in 30 minutes". The
   verbs reveal which fields have something to say.
2. **Assemble the crew.** Earth depends on this task; who does humanity send? For a deck:
   an analyst, a journalist, an editor, a motion designer; for a red team: a short seller and
   a forensic accountant. Two to four fields, each with the concrete method it contributes.
3. **Perform the method, not the role.** Do what a short seller does to research a position;
   the transcript stays in the agent's own voice. A transcript that reads like roleplay is
   the failure signal. Subagents per field are fine when the methods are independent.

Done when the rewrite lists the verbs, the fields, and one concrete technique per field.

## After the rewrite

Show the rewritten ask in a few lines, with the axis named. Then execute it. Stop after the
rewrite only when the user asked for the rewrite alone.
