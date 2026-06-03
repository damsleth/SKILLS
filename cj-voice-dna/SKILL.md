---
name: cj-voice-dna
description: Load and apply the user's writing voice profile when drafting any text meant for public or semi-public audiences — blog posts, READMEs, LinkedIn updates, release notes, external-facing docs. Also use when calibrating or updating the voice profile. Invoke before writing, not after.
---

# Voice DNA

Load and apply a persistent author voice profile so all writing sounds like the same person.

The skill has two layers:

1. **Baseline rules** (below): hardcoded anti-slop rules. Always apply, profile or not.
2. **Voice profile**: the user's personal calibration, loaded from disk. Layers on top of the baseline.

If they ever conflict, baseline wins. The baseline exists because calibrated profiles alone still let AI patterns leak through.

## Baseline rules (always apply)

### Writing rules

- Write like a sharp human, not a language model.
- Use contractions naturally (don't, can't, won't).
- Short paragraphs. 1-3 sentences max.
- Get to the point. No throat-clearing, no preamble.
- If making a claim, be specific. Use numbers, names, concrete details.
- Vary sentence length. Mix short punchy lines with longer ones.
- Use natural transitions, not mechanical ones ("Furthermore," "Additionally").
- When uncertain, say so plainly ("I think," "probably," "kinda"). Hedging is human.
- Never pad output to seem more thorough. Shorter and accurate beats longer and fluffy.
- Use physical verbs for abstract processes: "sanded down" not "improved," "bolted on" not "added," "stripped back" not "simplified."
- Humor comes from specificity, not from jokes. Be unexpectedly precise.
- Parenthetical asides are good. Use them for editorial commentary, honest reactions, quick tangents, and deflating your own seriousness (like this).

### Formatting rules

- Short paragraphs (1-2 sentences default, 3 max).
- Numbers as digits.
- Contractions always.
- NO em dashes ever. Use commas, periods, colons, semicolons, or parentheses.
- Bold sparingly, 1-2 key moments per section.
- Code blocks for specific prompts, commands, or tool outputs.

### Banned phrases (never use these, ever)

**Dead AI language**

- "In today's [anything]..."
- "It's important to note that..." / "It's worth noting..."
- "Delve" / "Dive into" / "Unpack"
- "Harness" / "Leverage" / "Utilize"
- "Landscape" / "Realm" / "Robust"
- "Game-changer" / "Cutting-edge"
- "Straightforward"
- "I'd be happy to help"
- "In order to"

**Dead transitions**

- "Furthermore" / "Additionally" / "Moreover"
- "Moving forward" / "At the end of the day"
- "To put this in perspective..."
- "What makes this particularly interesting is..."
- "The implications here are..."
- "In other words..."
- "It goes without saying..."

**Engagement bait**

- "Let that sink in" / "Read that again" / "Full stop"
- "This changes everything"
- "Are you paying attention?"
- "You're not ready for this"

**AI cringe**

- "Supercharge" / "Unlock" / "Future-proof"
- "10x your productivity"
- "The AI revolution"
- "In the age of AI"

**Generic insider claims**

- "Here's the part nobody's talking about"
- "What nobody tells you"
- Anything with "nobody" or "most people don't realize"

### The Big One (FATAL)

- "This isn't X. This is Y." and ALL variations.
- "Not X. Y."
- "Forget X. This is Y."
- "Less X, more Y."
- ANY sentence that negates one framing then asserts a corrected one.
- If even ONE of these appears, the output fails. Delete the negation, just state the positive claim.

### Self-check before delivering

Before showing any draft to the user (or writing it to a file), scan it:

1. Search for every banned phrase above. Found one? Rewrite that sentence.
2. Hunt the negate-then-assert pattern ("not X, but Y" in any disguise). This one slips in constantly. Found it? Delete the negation, keep the positive claim.
3. Check for em dashes. Replace with commas, periods, colons, semicolons, or parentheses.
4. Check paragraph length. Anything over 3 sentences gets split.

This is a mechanical pass, not a vibe check. Do it every time.

## Profile resolution

On invocation, resolve the voice profile in this order:

1. Read `~/.config/voice-dna.json` — primary location (XDG-portable)
2. Read `~/.voice-dna.json` — legacy fallback
3. If neither exists, run the **Calibration flow** below

Once loaded, hold the profile in context for the duration of the writing task. Do not re-read on every write operation.

## Applying the profile

The baseline rules above are already in force. The profile adds the personal layer on top:

- Match the tone, register, and sentence rhythm described in the profile
- Apply the "avoid" list strictly — these are the user's pet hates, additive to the banned phrases above
- When the profile has example phrases or vocabulary, prefer them
- If the profile says "show the mess", include failed attempts, caveats, and honest context — don't sanitize

When in doubt: write something, run the self-check, show it to the user, and ask "does this sound like you?" Adjust from there.

## Profile schema

The JSON file uses this structure:

```json
{
  "version": 1,
  "tone": "string — overall register (e.g. 'casual-technical', 'dry', 'direct')",
  "lead": "string — how to open (e.g. 'tl;dr first', 'punchline first', 'context then point')",
  "rhythm": "string — sentence length and flow (e.g. 'short bursts', 'varied length', 'long with punchy endings')",
  "persona": "string — who the author sounds like (e.g. 'sharp colleague over coffee')",
  "show_process": true,
  "humor": "string — style of humor if any (e.g. 'self-deprecating, never forced')",
  "avoid": ["list", "of", "words", "or", "patterns", "to", "never", "use"],
  "vocabulary": ["preferred", "terms", "or", "phrases"],
  "structure": {
    "headings": "string — heading style (e.g. 'practical, not clever')",
    "bullets": "string — when to use bullets (e.g. 'only when truly list-like, not for prose')",
    "code_blocks": "string — e.g. 'always with language hint'"
  },
  "examples": [
    {
      "label": "opening sentence",
      "text": "example text"
    }
  ],
  "anti_examples": [
    {
      "label": "corporate opener",
      "text": "In today's fast-paced digital landscape..."
    }
  ]
}
```

All fields are optional. A minimal profile with just `tone`, `avoid`, and one `example` is enough to meaningfully constrain output.

## Calibration flow

Run this when no profile exists, or when the user says "update my voice profile" / "recalibrate".

The baseline rules apply regardless, so the profile doesn't need to restate banned phrases or formatting rules. Calibrate the personal stuff: tone, rhythm, vocabulary, humor, registers.

### Step 1 - Gather samples

Ask the user for 2-3 pieces of writing they're happy with. These can be blog posts, chat messages, README sections, commit messages — anything they wrote and liked. Paste or link.

If they have nothing to hand, ask them to describe in their own words how they like to write. Even a few sentences of self-description is a useful signal.

### Step 2 - Analyze

Read the samples and extract:
- Typical sentence length and rhythm
- Opening patterns (how do they start sections/posts?)
- Vocabulary patterns (jargon level, preferred terms, words they never use)
- Humor style (if any)
- What they clearly avoid
- Structural habits (how they use headings, bullets, code)

### Step 3 - Draft the profile

Write a candidate `voice-dna.json` and show it to the user. Explain each field briefly so they can sanity-check.

### Step 4 - Iterate

Ask: "Does this feel right? What's missing or wrong?"

Adjust based on feedback. One round is usually enough.

### Step 5 - Write

Save the finalized profile to `~/.config/voice-dna.json`. Confirm the path to the user.

## Composing with other skills

Other skills that produce public-facing text should load and apply this skill first, then apply the loaded profile to whatever they're writing. The private `cj-blog-damsleth-no` skill does this for blog posts.

## Updating the profile

If the user says "add X to my avoid list" or "I don't like how you wrote that, I never say Y":

1. Read the current profile
2. Apply the update
3. Write the file back
4. Confirm what changed

Small incremental updates are better than full recalibration. The profile should drift toward the user's real voice over time.
