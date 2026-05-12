# SKILLS

A collection of public, reusable skills for AI coding agents (Claude Code, Codex, Copilot). Each skill is a self-contained folder with a `SKILL.md` prompt and optional references, assets, and agent configs.

## Public skills

| Skill | Description |
|-------|-------------|
| **cj-cloudflare-worker** | Create or update Cloudflare Workers with GitHub Actions deployment and custom domains |
| **cj-memory** | Generic memory-recall routed through the [mnem](https://github.com/damsleth/mnem) suite (yaams + cognitive-ledger). No user-specific references baked in. |
| **cj-things3-read-tasks** | Read and search Things3 tasks via things-cli |
| **cj-ux-loop-onboarding** | Install, configure, and operate the @damsleth/ux-loop UX audit pipeline. ([ux-loop](https://github.com/damsleth/ux-loop)) |
| **cj-voice-dna** | Load and apply your writing voice profile before drafting public-facing text |

## Install

Run the interactive installer to symlink skills into your agent's skill directory:

```bash
./install-skill.sh
```

This creates symlinks in `~/.claude/skills/`, `~/.codex/skills/`, and `~/.copilot/skills/`.

You can also install/uninstall non-interactively:

```bash
./install-skill.sh --install cj-memory
./install-skill.sh --uninstall cj-memory
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
