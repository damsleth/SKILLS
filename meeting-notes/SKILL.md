---
name: meeting-notes
description: Interactive meeting notes skill for preparing, running, and documenting meetings with automatic participant research. Use this skill whenever the user mentions meeting notes, meeting minutes, meeting prep, "møtenotater", "møtereferat", "møte", wants to prepare for a meeting, take notes during a meeting, or document what happened in a meeting. Also trigger when the user says "start møte", asks about upcoming meetings/calendar, or wants to look up info about meeting participants. This skill handles the full meeting lifecycle — from calendar lookup through live note-taking to final summary with action items.
---

# Møtenotater (meeting-notes)

An interactive skill for preparing, conducting, and documenting meetings. The skill fetches meetings via `owa-cal` (Outlook / Microsoft 365), collects participant info from the user, researches externals, and produces clean markdown meeting notes with live note-taking support.

All user-facing communication MUST be in Norwegian (Bokmål). Internal comments, code, and SKILL.md itself are in English.

## Overview

The workflow has these phases:

1. **Calendar lookup** — Fetch the user's meetings for the next 7 days via `owa-cal`
2. **Meeting selection** — User picks which meeting to document
3. **Participant research** — Collect attendees from the user, then look up externals via web search
4. **File setup** — Create the markdown meeting notes file (with optional template)
5. **Live meeting** — User takes notes in chat, Claude refines and appends them
6. **Wrap-up** — Meeting end timestamp, summary, and action items

If calendar access fails, fall back to manual meeting input.

---

## Phase 1: Get Calendar Data

### Step 1: Identify the user's email domain

The user's email is available in the session context (typically a `userEmail` block in CLAUDE.md). Extract the domain part (after `@`) — this is the organization domain used to classify attendees as intern/ekstern. If unavailable, ask the user.

### Step 2: Infer profile and fetch meetings with owa-cal

Infer the owa-cal profile from the user's request:

| User says...                              | Profile flag        |
|-------------------------------------------|---------------------|
| "Norconsult", "Crayon", "NOCOS"           | `--profile crayon`  |
| "BRKH", "Røde Kors", "vaktgruppe"         | `--profile brkh`    |
| "SoftwareOne", "SWON", no hint            | (none, default)     |

If the user's request is ambiguous and they have meetings in multiple calendars, ask:

> Hvilken kalender skal jeg hente møter fra? (SWON, Crayon, BRKH, eller alle?)

Compute the date range (today through today + 7 days) and run:

```bash
owa-cal [--profile <alias>] events --from <YYYY-MM-DD> --to <YYYY-MM-DD> --limit 50
```

Output is a JSON array. Each event has: `id`, `subject`, `start`, `end`, `categories`, `location`, `showAs`, `isAllDay`.

**Note:** `owa-cal` does not return attendees. Participant info is collected from the user in Phase 3.

### Step 3: Filter the results

Exclude events where any of the following are true:
- `isAllDay` is true (calendar blockers, out-of-office)
- `showAs` is `Free` or `Tentative`
- `categories` contains `IGNORE`
- Subject clearly indicates a personal block (e.g. "Focus time", "Lunch", "[Calendar Blocker] ...")

The remaining events are the candidates for the meeting picker.

### Manual Fallback

If `owa-cal` fails or returns no usable meetings, tell the user (in Norwegian):

> Kunne ikke hente kalenderdata. La oss legge inn møteinfo manuelt.

Then ask for:
- Møtetittel
- Dato og klokkeslett (fra-til)
- Sted (fysisk / Teams / annet)
- Deltakere (navn og e-post)

---

## Phase 2: Meeting Selection

Present the filtered meetings to the user as a numbered list, in Norwegian. Include:
- Date and time
- Subject/title
- Location (if any)

Example output:

> Her er møtene dine de neste 7 dagene:
>
> 1. **Prosjektmøte med Acme AS** - mandag 27. mars kl. 10:00-11:00, Teams
> 2. **Statusmøte Q2** - tirsdag 28. mars kl. 14:00-15:00, Møterom 4
> ...

Ask: "Hvilket møte skal vi ta notater for?"

Present the choices interactively so the user can pick one by number or title.

---

## Phase 3: Participant Research

Once a meeting is selected, ask the user for the attendee list (since `owa-cal` doesn't expose attendees):

> Hvem deltar på møtet? Lim inn navn og e-postadresser, eller bare navn hvis du ikke har e-post.

Parse the reply into a list of attendees. Classify each as:
- **Intern** - same email domain as the user
- **Ekstern** - different email domain (or explicitly flagged as external by the user)

If an attendee has no email, ask the user whether they are intern or ekstern.

Present the attendees to the user and ask who they want background info on. Offer these options:
- "Eksterne" (all external participants)
- "Alle" (everyone)
- "Ingen" (skip research)
- "Egendefinert" (let me pick)

If "Egendefinert" is selected, let the user multi-select which participants to research (checkboxes, numbered picks, whatever the environment supports).

### Research Execution

For each selected participant, search the web to find:
- Current role/title and employer
- Brief professional background
- LinkedIn profile (if findable)
- Their employer's business (what the company does, size, relevant context)

**Search strategy:**
- Start with `"Full Name" company/domain` based on their email domain
- If they use a generic email (gmail, outlook, hotmail etc.), search `"Full Name" LinkedIn`
- If results are ambiguous (common name, multiple matches), ask the user to clarify — e.g. provide a LinkedIn URL or additional context

Store the research results in your context — you'll need them during the live meeting phase to understand references to participants.

### Research Output

After researching, present a brief summary to the user in Norwegian:

> **Deltakeroversikt:**
>
> **Ola Nordmann** (ekstern) — Prosjektleder, Acme AS. Acme er et konsulentselskap med 50 ansatte som spesialiserer seg på digital transformasjon.
>
> **Kari Hansen** (intern) — Utvikler, ditt team.

If you couldn't identify someone clearly, say so and ask:

> Jeg fant flere personer med navnet "Lars Olsen" hos Contoso. Kan du dele LinkedIn-profilen eller gi meg mer kontekst?

---

## Phase 4: File Setup

### Template Selection

Check if templates exist in the skill's `templates/` subdirectory (relative to wherever this skill is installed - the path differs between Claude, Codex, and Copilot). List available templates with the equivalent of:

```bash
ls "$SKILL_DIR/templates"/*.md 2>/dev/null
```

Resolve `$SKILL_DIR` from the skill's invocation context.

If templates exist, ask the user (in Norwegian):

> Vil du bruke en møtenotatmal?

Present available templates plus "Blank (ingen mal)" as options.

If a template is selected, read it and fill in any frontmatter/metadata fields. Common fields:
- `kundenavn` (customer name)
- `prosjektnavn` (project name)
- `dato` (date — auto-fill from meeting)
- `type` (meeting type — e.g. "statusmøte", "workshop", "kick-off")

Ask the user to provide values for any template fields that can't be auto-filled.

### File Location

Ask the user where to save the file:

> Hvor skal møtenotatene lagres? (Standard: current working directory)

Default filename format: `YYYY-MM-DD-møtetittel.md` (sanitize the title for filesystem use — lowercase, hyphens instead of spaces, no special chars).

### Create the Initial File

The markdown file should start with:

```markdown
# [Meeting Title]

**Dato:** YYYY-MM-DD
**Tid:** HH:MM – HH:MM
**Sted:** [Location]
**Deltakere:**
- Navn (rolle/selskap) — intern/ekstern

---

## Deltakerbakgrunn

[Brief participant summaries from the research phase]

---

## Møtenotater

[Notes will be appended here during the meeting]
```

If using a template, follow the template's structure instead, but ensure the participant info and research is included.

---

## Phase 5: Live Meeting

Ask the user: "Klar til å starte møtet?"

When they confirm (or say "start møte"), append to the file:

```markdown
**Møtet startet:** YYYY-MM-DD HH:MM
```

### During the Meeting

The user will send messages in chat. These can be:

1. **Raw notes** — messy, shorthand notes about what's being discussed
2. **Questions** — asking about a participant, their company, a topic, etc.
3. **Instructions** — "legg til aksjonspunkt", "noter at vi ble enige om X"

**For raw notes:**
- Clean them up: fix typos, expand abbreviations, add structure
- Use context about participants to resolve ambiguous references. For example, if the user writes "hun sier vi må levere raskere" and there's only one female external participant, attribute the statement to her by name
- Append the refined notes to the markdown file under the `## Møtenotater` section
- Group notes by topic/theme when natural, using `###` subheadings

**For questions:**
- Answer using your researched participant data, doing additional web lookups if needed
- Don't append Q&A to the meeting notes unless the user explicitly asks

**For instructions:**
- Execute them (add action items, record decisions, etc.)
- Append to the appropriate section in the file

### Writing Style for Notes

- Use clear, professional Norwegian
- Write in past tense for what was said/decided ("Ola presenterte...", "Det ble besluttet at...")
- Mark decisions clearly: **Beslutning:** ...
- Mark action items clearly: **Aksjon:** [Hvem] — [Hva] — [Frist]
- Keep participant attributions where relevant

---

## Phase 6: Wrap-up

When the user says "møtet er ferdig" (or equivalent), do the following:

### 1. Add end timestamp

```markdown
**Møtet avsluttet:** YYYY-MM-DD HH:MM
```

### 2. Generate summary and action items

Append these sections to the file:

```markdown
---

## Oppsummering

[2-5 bullet points summarizing the key topics and outcomes]

## Beslutninger

[List of decisions made, if any]

## Aksjonspunkter

| # | Ansvarlig | Oppgave | Frist |
|---|-----------|---------|-------|
| 1 | Ola       | ...     | ...   |

## Neste steg

[Any agreed follow-ups, next meeting, etc.]
```

### 3. Review with user

Present the summary to the user and ask:

> Her er oppsummeringen og aksjonspunktene. Stemmer dette? Er det noe som bør endres eller legges til?

Refine based on their feedback, then confirm the final file is saved.

---

## Important Behaviors

- **Language:** All user-facing output in Norwegian (Bokmål). Code, logs, and internal comments in English.
- **Context awareness:** Keep participant research in active context throughout the meeting. Use it to resolve "han/hun/de" references and company mentions.
- **File updates:** After each batch of notes, append to the markdown file. Edit or append to it - don't rewrite the entire file each time.
- **Timestamps:** Use local time (user's timezone). Default to Europe/Oslo if not specified.
- **Tone:** Professional but approachable in Norwegian. Short sentences, no fluff.
- **Proactive:** If the user's notes are ambiguous, ask a clarifying question rather than guessing wrong. But if context makes it obvious (like gender-based pronoun resolution), just handle it.

---

## Templates

Templates live in this skill's `templates/` directory as `.md` files. Each template can have YAML frontmatter with fields that get filled in before the meeting starts. See the included `standard.md` template as an example.

To create a new template: add a `.md` file to the `templates/` directory following the same pattern.