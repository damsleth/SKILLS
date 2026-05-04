---
name: cj-voice-dna
description: Load and apply the user's writing voice profile when drafting any text meant for public or semi-public audiences — blog posts, READMEs, LinkedIn updates, release notes, external-facing docs. Also use when calibrating or updating the voice profile. Invoke before writing, not after.
version: 1.0.0
author: damsleth
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
tags:
  - writing
  - voice
  - style
---

# Voice DNA

Load and apply a persistent author voice profile so all writing sounds like the same person.

## Profile resolution

On invocation, resolve the voice profile in this order:

1. Read `~/.config/voice-dna.json` — primary location (XDG-portable)
2. Read `~/.voice-dna.json` — legacy fallback
3. If neither exists, run the **Calibration flow** below

Once loaded, hold the profile in context for the duration of the writing task. Do not re-read on every write operation.

## Applying the profile

When writing on behalf of the user:

- Match the tone, register, and sentence rhythm described in the profile
- Apply the "avoid" list strictly — these are the user's pet hates
- When the profile has example phrases or vocabulary, prefer them
- Do not blend in generic AI writing patterns (hedging, bullet overload, "it's worth noting that")
- If the profile says "show the mess", include failed attempts, caveats, and honest context — don't sanitize

When in doubt: write something, show it to the user, and ask "does this sound like you?" Adjust from there.

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

Other skills that produce public-facing text should invoke this skill first:

```
Use the Skill tool: skill: "cj-voice-dna"
```

Then apply the loaded profile to whatever they're writing. The `/cj-blog-damsleth-no` skill does this for blog posts.

## Updating the profile

If the user says "add X to my avoid list" or "I don't like how you wrote that, I never say Y":

1. Read the current profile
2. Apply the update
3. Write the file back
4. Confirm what changed

Small incremental updates are better than full recalibration. The profile should drift toward the user's real voice over time.
