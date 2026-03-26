# SKILLS

A collection of skills for AI coding agents (Claude Code, Codex, Copilot). Each skill is a self-contained folder with a `SKILL.md` prompt and optional references, assets, and agent configs.

## Skills

| Skill | Description |
|-------|-------------|
| **cloudflare-worker** | Create or update Cloudflare Workers with GitHub Actions deployment and custom domains |
| **cognitive-ledger** | File-based, self-maintaining memory substrate for long-term structured memory across agents |
| **meeting-notes** | Interactive meeting lifecycle: prep, live notes, and summary with action items |
| **notes-ledger-sync** | Capture notes and sync durable memory through the cognitive-ledger |
| **things3-read-tasks** | Read and search Things3 tasks via things-cli |
| **ux-loop-onboarding** | Install, configure, and operate the @damsleth/ux-loop UX audit pipeline |

## Install

Run the interactive installer to symlink skills into your agent's skill directory:

```bash
./install-skill.sh
```

This creates symlinks in `~/.claude/skills/`, `~/.codex/skills/`, and `~/.copilot/skills/`.

You can also install/uninstall non-interactively:

```bash
./install-skill.sh --install cognitive-ledger
./install-skill.sh --uninstall cognitive-ledger
./install-skill.sh --list
```

## Structure

Each skill folder contains:

- `SKILL.md` — the main prompt (required)
- `references/` — supporting docs the skill can read at runtime
- `agents/` — agent configs (e.g. OpenAI agent YAML)
- `assets/` — templates, examples, config files

## License

WTFPL
