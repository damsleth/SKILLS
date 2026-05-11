# SKILLS

A collection of C.J.'s personal-but-shareable skills for AI coding agents (Claude Code, Codex, Copilot). Each skill is a self-contained folder with a `SKILL.md` prompt and optional references, assets, and agent configs.

## Skills

| Skill | Description |
|-------|-------------|
| **cloudflare-worker** | Create or update Cloudflare Workers with GitHub Actions deployment and custom domains |
| **did** | Review and manage timesheets via did-cli, with calendar as source of truth. ([did](https://github.com/puzzlepart/did)) |
| **meeting-notes** | Interactive meeting lifecycle: prep, live notes, and summary with action items |
| **notes** | Capture notes to Obsidian and sync structured memory to a cognitive ledger. ([cognitive-ledger](https://github.com/damsleth/cognitive-ledger)) |
| **owa-tools** | Drive the Outlook / Microsoft 365 CLI suite (cal, mail, graph, doctor, people, sched, drive) and the owa-piggy auth broker. ([owa-tools](https://github.com/damsleth/owa-tools)) |
| **things3-read-tasks** | Read and search Things3 tasks via things-cli |
| **ux-loop-onboarding** | Install, configure, and operate the @damsleth/ux-loop UX audit pipeline. ([ux-loop](https://github.com/damsleth/ux-loop)) |
| **voice-dna** | Load and apply your writing voice profile before drafting public-facing text |
| **weekly-review** | Review and plan the week across tasks, calendar, timesheet, and open loops |
| **yaams** | Query personal memory for context about people, projects, decisions, and history. ([yaams](https://github.com/damsleth/yaams)) |

## Install

Run the interactive installer to symlink skills into your agent's skill directory:

```bash
./install-skill.sh
```

This creates symlinks in `~/.claude/skills/`, `~/.codex/skills/`, and `~/.copilot/skills/`.

You can also install/uninstall non-interactively:

```bash
./install-skill.sh --install cj-notes
./install-skill.sh --uninstall cj-notes
./install-skill.sh --list
```

## Structure

Each skill folder contains:

- `SKILL.md` — the main prompt (required)
- `references/` — supporting docs the skill can read at runtime
- `agents/` — agent configs (e.g. OpenAI agent YAML)
- `assets/` — templates, examples, config files

## License

MIT
