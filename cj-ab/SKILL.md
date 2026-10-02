---
name: cj-ab
description: Agent bridge — send one prompt (plus an optional file) to another coding agent (claude, codex, copilot) via the bundled `agent-bridge` CLI and get its answer back as text. Use when the user says "send this to codex/claude/copilot", "ask codex", "/cj-ab"; to delegate a self-contained subtask to an agent better suited for it; to get a second opinion or cross-check your own answer, review or diff; to translate code between languages or syntaxes; or to get an alternative draft to compare against yours.
---

# cj-ab (agent bridge)

`agent-bridge` runs one headless prompt against another agent CLI and prints that agent's answer to stdout:

```bash
agent-bridge <claude|codex|copilot> "<prompt>" [file_path]
```

Example: "send src/auth.py to codex and have it convert it to Rust" becomes

```bash
agent-bridge codex "Convert this Python file to idiomatic Rust. Output only the code." src/auth.py
```

If `agent-bridge` is not on PATH, call it by path from this skill folder.

## Writing the prompt

The target agent starts cold: it sees only the prompt and the file, never your conversation. Write the prompt as a complete brief, with the goal, the constraints that matter, and the output format you want back ("output only the code", "list findings as bullets", "reply with a verdict and three reasons"). Pass a single `file_path` and let the bridge inline it. For several files, name their paths in the prompt; the target runs in your working directory and can read them itself.

Any target is valid, including your own kind. `agent-bridge claude` from Claude gives a fresh-context second opinion.

## Running it

- **Timeout.** A call takes 1 to 5 minutes. Set the shell tool's timeout to 10 minutes (600000 ms), or run it in the background, so a slow answer is not lost.
- **Full access.** The target runs with no sandbox and no approval prompts: it can edit files, run commands and reach the network in your working directory. Say in the prompt whether you want edits made or only an answer back, and review `git diff` after a call that edits.
- **One hop.** A call made from inside a bridged agent is refused, which stops agents bouncing prompts between each other.
- **Failures.** Errors start with `[agent-bridge]` on stderr: bad usage, an unreadable file, or a CLI missing from PATH. The bridge passes the target's own errors and exit code through as-is.

## Using the answer

The answer is input to your judgement. Check it, and any edits it made, against the code before building on it or relaying it, and tell the user which agent it came from. When you are cross-checking, report where the two answers agree and where they differ.
