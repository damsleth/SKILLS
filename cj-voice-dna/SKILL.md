---
name: cj-voice-dna
description: Pick the register (språkdrakt) and apply the user's voice profile before drafting prose others will read. Branches - blog posts and LinkedIn, work notes and incident write-ups, messages and PR descriptions, formal proposals, technical documentation and procedures (incl. ASD-STE100 Simplified Technical English). Also for calibrating or updating the voice profile.
---

# Voice DNA

Every text is written along three axes. Settle all three before the first sentence:

| Axis | Question | Source |
|---|---|---|
| **voice** | who is writing | the profile's `voice` block: persona, humor, vocabulary, avoid list |
| **register** (språkdrakt) | what kind of text this is | built-in registers below, extended by the profile's `registers` |
| **language** | which language | the context; language rules below plus the profile's `lang` |

The register decides how much voice gets through. A blog post carries the full voice. A procedure carries none of it.

Precedence when rules collide: global rules, then register, then language, then voice.

## Steps

1. **Load the profile** (see *Profile resolution*). Done when the profile is in context or calibration has started.
2. **Pick the register.** First match wins:
   1. The user names it ("skriv i STE", "som blogg", "som arbeidsnotat").
   2. The destination decides: a blog post or LinkedIn is `blog`; a note in a notes vault, a meeting summary, a running work note or an incident write-up is `work_note`; a chat, mail, Teams post or PR description is `message`; a proposal, recommendation or application upward is `formal`; a README, runbook, procedure, install guide or API doc is `tech_doc`.
   3. Otherwise pick the closest one and name it in one line to the user.

   Done when exactly one register is chosen.
3. **Pick the language** from the context. Load `lang.<code>` from the profile. Done when the language rules and the language's avoid list are in context.
4. **For `tech_doc`**, read [`ste.md`](ste.md) before writing. It holds the ASD-STE100 rules (English) and the klarspråk fallback (Norwegian).
5. **Draft**, applying the global rules, the register, the language, and the voice at the register's dial.
6. **Run the self-check.** Done when every check passes on every paragraph.

## Global rules (every register)

- Get to the point. The first sentence carries information.
- Make claims specific: numbers, names, dates, identifiers.
- Say plainly what you don't know, and where the uncertainty comes from.
- Write the shortest text that is accurate. Length follows content.
- Short paragraphs: 3 sentences at most.
- Numbers as digits.
- Punctuate with commas, periods, colons, semicolons and parentheses. Em dashes are banned.
- Bold sparingly, 1-2 key moments per section.
- Code blocks for commands, prompts and tool output, with a language hint.
- State the positive claim directly. **Fatal:** any sentence that negates one framing to assert a corrected one ("This isn't X. This is Y.", "Not X. Y.", "Forget X.", "Less X, more Y.", "ikke X, men Y"). One of these fails the output.
- The banned phrases below apply everywhere.

## Voice dial

Each register sets `voice` to one of three levels:

- **`full`**: persona, humor, rhythm, vocabulary and examples all apply.
- **`muted`**: the persona's word choice and the avoid lists apply. Humor, punchlines, dramatic framing and emotional words ("redd for", "worried", "scary") drop out. The writer sounds like themselves on a normal workday.
- **`off`**: only the global rules, the register rules and the avoid lists. Nobody in particular is writing.

## Built-in registers

The profile's `registers.<name>` merges over these. The profile can add new registers too.

**`blog`**, voice `full`
- Lead with the thesis. The title is the claim.
- Vary sentence length. Mix short lines with longer ones.
- Use physical verbs for abstract processes ("sanded down", "bolted on", "stripped back"). English only; other languages use their own idioms.
- Humor comes from specificity. Be unexpectedly precise.
- Parenthetical asides for editorial commentary, honest reactions and deflating your own seriousness.
- Close on a distilled line.

**`work_note`**, voice `muted`
- Lead with the result or the state: what happened, numbers, who.
- Each sentence carries a fact, a decision, a reason or an open question.
- Headings name the topic in plain words.
- Cite the source per claim (note link, ticket, date).
- State unknowns as facts: "ukjent", "ikke bekreftet", "no answer yet", with who should know.
- End on the last fact or the next step.

**`message`**, voice `muted`
- Open with the ask or the news.
- One ask per message where possible, with owner and deadline.
- PR descriptions and first-contact messages end on the last fact.

**`formal`**, voice `muted`
- Principle first, then a plain chain of reasoning, then a flat conclusion.
- Formality means precision. Keep the vocabulary plain.

**`tech_doc`**, voice `off`
- Follow [`ste.md`](ste.md).

## Language rules

**English (`en`)**
- Use contractions (don't, can't, won't), except in `tech_doc`.
- Plain transitions ("so", "but", "then").

**Other languages** have no built-in rules. The profile's `lang.<code>` supplies them: rules, avoid list, preferred vocabulary and examples.

## Banned phrases

**Dead AI language**: "In today's [anything]...", "It's important to note that..." / "It's worth noting...", "Delve" / "Dive into" / "Unpack", "Harness" / "Leverage" / "Utilize", "Landscape" / "Realm" / "Robust", "Game-changer" / "Cutting-edge", "Straightforward", "I'd be happy to help", "In order to".

**Dead transitions**: "Furthermore" / "Additionally" / "Moreover", "Moving forward" / "At the end of the day", "To put this in perspective...", "What makes this particularly interesting is...", "The implications here are...", "In other words...", "It goes without saying...".

**Engagement bait**: "Let that sink in" / "Read that again" / "Full stop", "This changes everything", "Are you paying attention?", "You're not ready for this".

**AI cringe**: "Supercharge" / "Unlock" / "Future-proof", "10x your productivity", "The AI revolution", "In the age of AI".

**Generic insider claims**: "Here's the part nobody's talking about", "What nobody tells you", anything with "nobody" or "most people don't realize".

The profile's avoid lists (`voice.avoid`, `lang.<code>.avoid`) add to these.

## Self-check

Before showing a draft or writing it to a file, run this pass. It is mechanical.

1. Every banned phrase and every avoid-list entry: found one, rewrite the sentence.
2. Negate-then-assert in any disguise, in every language: delete the negation, keep the positive claim.
3. Em dashes: replace them.
4. Paragraphs over 3 sentences: split them.
5. Register fit: every sentence belongs to the chosen register. In `work_note` and `message`, cut punchlines, dramatic headings and emotional words. In `tech_doc`, run the checks in `ste.md`.

## Profile resolution

1. Read `~/.config/voice-dna.json` (primary, XDG-portable).
2. Read `~/.voice-dna.json` (legacy fallback).
3. If neither exists, run the *Calibration flow*.

Hold the profile in context for the whole writing task.

A `version: 1` profile (flat fields, no `voice` block) is read as: all flat fields form `voice`, and `lead`, `rhythm` and `examples` also form `registers.blog`.

## Profile schema (version 2)

All fields are optional. Extra string fields in any block (for example `risk_flagging` in `voice`) are free-form guidance.

```json
{
  "version": 2,
  "language": "how to choose between languages, e.g. 'match the context'",
  "voice": {
    "tone": "overall tone",
    "persona": "who the author sounds like",
    "humor": "humor style, used at voice 'full'",
    "show_process": true,
    "avoid": ["language-neutral patterns to avoid"],
    "vocabulary": ["preferred terms"],
    "structure": { "headings": "...", "bullets": "...", "code_blocks": "..." },
    "anti_examples": [{ "label": "...", "text": "..." }]
  },
  "registers": {
    "<name>": {
      "voice": "full | muted | off",
      "use_for": "destinations that pick this register",
      "lead": "how to open",
      "rhythm": "sentence length and flow",
      "rules": ["register-specific rules"],
      "examples": [{ "label": "...", "text": "..." }],
      "anti_examples": [{ "label": "...", "text": "..." }]
    }
  },
  "lang": {
    "<code>": {
      "rules": ["language-specific rules"],
      "avoid": ["phrases to avoid in this language"],
      "vocabulary": ["preferred terms in this language"],
      "examples": [{ "label": "...", "text": "..." }]
    }
  }
}
```

## Calibration flow

Run this when no profile exists, or when the user says "update my voice profile" / "recalibrate". The global rules and built-in registers apply regardless, so calibrate the personal layer: voice, the user's own registers, and language-specific habits.

1. **Gather samples.** Ask for 2-3 texts the user is happy with, ideally from different registers (a blog post, a work note, a message). If they have none, ask them to describe how they write.
2. **Analyze** each sample for register, language, sentence length and rhythm, openings, vocabulary, humor, what they avoid, and structural habits.
3. **Draft the profile.** Put what holds across samples in `voice`, what differs by text type in `registers`, and what differs by language in `lang`. Show it and explain each field briefly.
4. **Iterate** once on feedback.
5. **Write** it to `~/.config/voice-dna.json` and confirm the path.

## Updating the profile

When the user says "add X to my avoid list", "I never say Y", or reacts to a draft ("this is cringe"):

1. Read the current profile.
2. Place the update on the right axis: every text goes in `voice`, one kind of text goes in `registers.<name>`, one language goes in `lang.<code>`. Put a sentence the user rejected in that register's `anti_examples`.
3. Write the file back and confirm what changed.

Small incremental updates beat recalibration.

## Composing with other skills

Skills that produce text for others to read load this skill first and name the register they write in. The private `cj-blog-damsleth-no` skill writes in `blog`.
