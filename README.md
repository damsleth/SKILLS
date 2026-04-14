# SKILLS

A collection of skills for AI coding agents (Claude Code, Codex, Copilot). Each skill is a self-contained folder with a `SKILL.md` prompt and optional references, assets, and agent configs.

## Skills

| Skill | Description |
|-------|-------------|
| **blog-damsleth-no** | Write blog post drafts with proper frontmatter and manifest updates |
| **calendar** | Manage Outlook/Microsoft 365 calendar events via cal-cli |
| **cloudflare-worker** | Create or update Cloudflare Workers with GitHub Actions deployment and custom domains |
| **did** | Review and manage timesheets via did-cli, with calendar as source of truth |
| **meeting-notes** | Interactive meeting lifecycle: prep, live notes, and summary with action items |
| **notes** | Capture notes to Obsidian and sync structured memory to a cognitive ledger |
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
