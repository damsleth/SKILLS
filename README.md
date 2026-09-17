# SKILLS

A collection of public, reusable skills for AI coding agents (Claude Code, Codex, Copilot). Each skill is a self-contained folder with a `SKILL.md` prompt and optional references, assets, and agent configs.

## Public skills

| Skill | Description |
|-------|-------------|
| **cj-automate** | Audit a workflow and propose automations ordered by leverage — remove humans from transport steps first, collapse waits second, optimize speed last |
| **cj-cloudflare-worker** | Create or update Cloudflare Workers with GitHub Actions deployment and custom domains |
| **cj-code-review** | Confidence-filtered code review of a PR, branch, or local diff — several independent review passes, each finding scored and dropped below 80. Model-agnostic. |
| **cj-now** | One read-only view of everything open across repo `.plans/`, Things 3 and Azure DevOps, keyed on the owa-piggy profile. Bundled `now` CLI projects the three sources on demand, so there is nothing to sync and nothing to drift. |
| **cj-things** | Manage Things 3 tasks, projects, and areas from the terminal via the `things` CLI — full CRUD plus the Things-only reads (logbook, tags, queries) that cj-now leaves out. Pairs with cj-notes. ([things3-cli](https://github.com/ossianhempel/things3-cli)) |
| **cj-todo** | World's most lightweight repo-scoped todo & plan tracker. Bundled `todo` CLI does the CRUD; the skill decides todo-vs-plan and authors plans. |
| **cj-video-vision** | Watch and analyze videos (local files + YouTube) via the claude-video-vision MCP server — frame extraction, scene/silence/motion analysis, transcription. ([claude-video-vision](https://github.com/damsleth/claude-video-vision)) |
| **cj-ux-loop-onboarding** | Install, configure, and operate the @damsleth/ux-loop UX audit pipeline. ([ux-loop](https://github.com/damsleth/ux-loop)) |
| **cj-voice-dna** | Load and apply your writing voice profile before drafting public-facing text |

## Install

Run the interactive installer to symlink skills into your agent's skill directory:

```bash
./install-skill.sh
```

This creates symlinks in `~/.claude/skills/`, `~/.codex/skills/`, and `~/.copilot/skills/`.

Extra skill folders (e.g. a private repo) can be added from the menu with `a` and removed with `ctrl+d` on the folder header. They are stored in `~/.agents/install-skill.json`.

You can also install/uninstall non-interactively:

```bash
./install-skill.sh --install cj-todo
./install-skill.sh --uninstall cj-todo
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
