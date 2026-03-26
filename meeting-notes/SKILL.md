---
name: meeting-notes
description: Interactive meeting notes skill for preparing, running, and documenting meetings with automatic participant research. Use this skill whenever the user mentions meeting notes, meeting minutes, meeting prep, "møtenotater", "møtereferat", "møte", wants to prepare for a meeting, take notes during a meeting, or document what happened in a meeting. Also trigger when the user says "start møte", asks about upcoming meetings/calendar, or wants to look up info about meeting participants. This skill handles the full meeting lifecycle — from calendar lookup through live note-taking to final summary with action items.
---

# Møtenotater (meeting-notes)

An interactive skill for preparing, conducting, and documenting meetings. The skill fetches meetings from Microsoft Graph, researches participants, and produces clean markdown meeting notes with live note-taking support.

All user-facing communication MUST be in Norwegian (Bokmål). Internal comments, code, and SKILL.md itself are in English.

## Overview

The workflow has these phases:

1. **Calendar lookup** — Fetch the user's meetings for the next 7 days via MS Graph
2. **Meeting selection** — User picks which meeting to document
3. **Participant research** — Look up external participants via web search
4. **File setup** — Create the markdown meeting notes file (with optional template)
5. **Live meeting** — User takes notes in chat, Claude refines and appends them
6. **Wrap-up** — Meeting end timestamp, summary, and action items

If calendar access fails (token issues, no meetings, etc.), fall back to manual meeting input.

---

## Phase 1: Get Calendar Data

### Step 1: Get the MS Graph token

Run the `get-token` CLI tool to obtain a JWT token with Microsoft Graph scopes:

```bash
TOKEN=$(get-token)
```

The tool returns a raw JWT token string. If it fails or returns empty, move to the **Manual Fallback** section below.

### Step 2: Get the user's profile

Fetch the user's profile to identify their email domain (needed to distinguish internal vs external participants):

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://graph.microsoft.com/v1.0/me?$select=displayName,mail,userPrincipalName" 
```

Extract `mail` or `userPrincipalName` — the domain part (after @) is the user's organization domain.

### Step 3: Fetch meetings for the next 7 days

```bash
START=$(date -u +"%Y-%m-%dT%H:%M:%S.0000000Z")
END=$(date -u -d "+7 days" +"%Y-%m-%dT%H:%M:%S.0000000Z" 2>/dev/null || date -u -v+7d +"%Y-%m-%dT%H:%M:%S.0000000Z")

curl -s -H "Authorization: Bearer $TOKEN" \
  "https://graph.microsoft.com/v1.0/me/calendarView?\$select=subject,start,end,location,attendees,organizer,isOnlineMeeting,onlineMeetingUrl&\$filter=start/dateTime ge '$START' and end/dateTime le '$END'&\$orderby=start/dateTime&\$top=50"
```

Filter the results: only include meetings where there is at least 1 attendee whose email address is different from the user's own email. Solo calendar blocks, focus time, etc. should be excluded.

### Manual Fallback

If token retrieval or Graph API calls fail, tell the user (in Norwegian):

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
- Number of other attendees

Example output:

> Her er møtene dine de neste 7 dagene:
>
> 1. **Prosjektmøte med Acme AS** — mandag 27. mars kl. 10:00-11:00, Teams (3 deltakere)
> 2. **Statusmøte Q2** — tirsdag 28. mars kl. 14:00-15:00, Møterom 4 (5 deltakere)
> ...

Ask: "Hvilket møte skal vi ta notater for?"

Use the `ask_user_input` tool to present the choices when practical.

---

## Phase 3: Participant Research

Once a meeting is selected, list the attendees. Classify each as:
- **Intern** — same email domain as the user
- **Ekstern** — different email domain

Present the attendees to the user and ask who they want background info on. Use `ask_user_input` with these options:
- "Eksterne" (all external participants)
- "Alle" (everyone)
- "Ingen" (skip research)
- "Egendefinert" (let me pick)

If "Egendefinert" is selected, present checkboxes (multi-select) with each participant's name.

### Research Execution

For each selected participant, use `web_search` to find:
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

Check if templates exist in the skill's `templates/` directory. Read available templates:

```bash
ls /path/to/skill/templates/*.md 2>/dev/null
```

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
- Answer using your researched participant data and web search if needed
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
- **File updates:** After each batch of notes, append to the markdown file. Use `str_replace` or append operations — don't rewrite the entire file each time.
- **Timestamps:** Use local time (user's timezone). Default to Europe/Oslo if not specified.
- **Tone:** Professional but approachable in Norwegian. Short sentences, no fluff.
- **Proactive:** If the user's notes are ambiguous, ask a clarifying question rather than guessing wrong. But if context makes it obvious (like gender-based pronoun resolution), just handle it.

---

## Templates

Templates live in this skill's `templates/` directory as `.md` files. Each template can have YAML frontmatter with fields that get filled in before the meeting starts. See the included `standard.md` template as an example.

To create a new template: add a `.md` file to the `templates/` directory following the same pattern.