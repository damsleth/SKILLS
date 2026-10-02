---
name: cj-ab
description: Agent bridge — hand one task (plus an optional file) to another coding agent (claude, codex, copilot) via the bundled `agent-bridge` CLI and get its answer back. Use when the user says "send this to codex/claude/copilot", "ask codex", "/cj-ab"; to delegate a self-contained subtask to an agent better suited for it; to get a second opinion or cross-check your own answer, review or diff; to translate code between languages or syntaxes; or to get an alternative draft to compare against yours.
---

# cj-ab (agent bridge)

`agent-bridge` runs one headless prompt against another agent CLI and streams that agent's answer to stdout:

```bash
agent-bridge [-m light|medium|heavy|<model>] <claude|codex|copilot> "<prompt>"|- [file_path]
```

If `agent-bridge` is not on PATH, call it by path from this skill folder.

## Writing the prompt

The target agent starts cold: it sees only the prompt and the file, never your conversation. Write the prompt as a complete brief, with the goal, the constraints that matter, and the output format you want back ("output only the code", "list findings as bullets", "reply with a verdict and three reasons"). Pass a single `file_path` and let the bridge inline it. For several files, name their paths in the prompt; the target runs in your working directory and can read them itself.

Pass the prompt as `-` and feed it through a heredoc with a quoted delimiter, so the shell leaves quotes, `$()` and backticks in it alone:

```bash
agent-bridge codex - src/auth.py <<'EOF'
Convert this Python file to idiomatic Rust. Output only the code.
EOF
```

Any target is valid, including your own kind. `agent-bridge claude` from Claude gives a fresh-context second opinion.

## Choosing the model

If the user named a model, pass it with `-m` exactly as given. Otherwise pick the tier from the task's complexity:

- **medium**: the usual choice, for everyday work: a focused review, a single-module change, an alternative draft, a translation with real logic in it.
- **light**: only for trivially mechanical work with one right answer: reformatting, a quick lookup, a yes/no sanity check.
- **heavy**: work where depth decides the outcome: a cross-cutting review or audit, architecture or security judgement, a hard bug, a multi-file change.

When torn between two tiers, take the higher one. Omitting `-m` runs the CLI's configured default model. The tier names map to concrete models in the script's `TIERS` table.

## Running it

- **Timeout.** A call takes 1 to 5 minutes, longer on `heavy`. Set the shell tool's timeout to 10 minutes (600000 ms), or use the shell tool's own background mode, which keeps the output and reports completion. With a plain `&`, redirect stdout and stderr to a file and wait on the process before reading it.
- **Full access.** The target runs with no sandbox and no approval prompts: it can edit files, run commands and reach the network in your working directory. Say in the prompt whether you want edits made or only an answer back, and review `git diff` after a call that edits.
- **One hop.** The bridge refuses a call made from inside a bridged agent. The guard is an inherited env var, so it stops accidental ping-pong, not a child set on delegating.
- **Cancellation.** Killing the bridge (timeout, Ctrl-C) takes the target's whole process tree down with it.
- **Failures.** Errors start with `[agent-bridge]` on stderr: bad usage, an unreadable file, or a CLI missing from PATH. The bridge passes the target's own errors and exit code through as-is.

## Using the answer

The answer is input to your judgement. Check it, and any edits it made, against the code before building on it or relaying it, and tell the user which agent and model it came from. When you are cross-checking, report where the two answers agree and where they differ.
