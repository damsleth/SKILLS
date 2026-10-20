# SKILLS

A collection of public, reusable skills for AI coding agents (Claude Code, Codex, Copilot). Each skill is a self-contained folder with a `SKILL.md` prompt and optional references, assets, and agent configs.

## Public skills

| Skill | Description |
|-------|-------------|
| **cj-ab** | Agent bridge — hand one prompt (plus an optional file) to claude, codex or copilot and get the answer back as text: delegation, second opinions, code translation, alternative drafts. Bundled `agent-bridge` CLI. |
| **cj-ambition** | Raise the ambition of a task along one axis before executing — altitude (goal beyond the goal), depth (deeper not bigger, expert instruments, outside judge), range (assemble the crew from other fields). Distilled from Felix Rieseberg's "How to be more ambitious". |
| **cj-automate** | Audit a workflow and propose automations ordered by leverage — remove humans from transport steps first, collapse waits second, optimize speed last |
| **cj-cloudflare-worker** | Create or update Cloudflare Workers with GitHub Actions deployment and custom domains |
| **cj-code-review** | Confidence-filtered code review of a PR, branch, or local diff — several independent review passes, each finding scored and dropped below 80. Model-agnostic. |
| **cj-meetings** | Prepare, run and document meetings — Outlook lookup via owa-tools, attendee research, live transcript from Teams captions (macOS), `sc` meeting-window screenshots, Teams Facilitator recap, and recap of recorded meetings |
| **cj-notes** | Capture notes to an Obsidian vault first, ask targeted questions before writing, and sync durable facts, decisions and open loops to the cognitive ledger when it is installed. ([cognitive-ledger](https://github.com/damsleth/cognitive-ledger)) |
| **cj-now** | One read-only view of everything open across repo `.plans/`, Things 3 and Azure DevOps, keyed on the owa-piggy profile. Bundled `now` CLI projects the three sources on demand, so there is nothing to sync and nothing to drift. |
| **cj-owa-tools** | Judgment layer for the owa-tools M365 CLI suite and owa-piggy auth: install requirements, profile model with `-A` fan-out for reads, audiences, auth recovery. ([owa-tools](https://github.com/damsleth/owa-tools)) |
| **cj-things** | Manage Things 3 tasks, projects, and areas from the terminal via the `things` CLI — full CRUD plus the Things-only reads (logbook, tags, queries) that cj-now leaves out. Pairs with cj-notes. ([things3-cli](https://github.com/ossianhempel/things3-cli)) |
| **cj-todo** | World's most lightweight repo-scoped todo & plan tracker. Bundled `todo` CLI does the CRUD; the skill decides todo-vs-plan and authors plans. |
| **cj-ux-loop-onboarding** | Install, configure, and operate the @damsleth/ux-loop UX audit pipeline. ([ux-loop](https://github.com/damsleth/ux-loop)) |
| **cj-video-vision** | Watch and analyze videos (local files + YouTube) via the claude-video-vision MCP server — frame extraction, scene/silence/motion analysis, transcription. ([claude-video-vision](https://github.com/damsleth/claude-video-vision)) |
| **cj-voice-dna** | Pick the register (språkdrakt) and apply your voice profile before drafting: blog, work notes, messages, formal, technical docs (STE) |
| **repo-deep** | On-demand deep code-quality pass over one repo, orchestrating ponytail-audit and code-review (both optional) plus a test-gap check, then applying only approved fixes. |
| **repo-deps** | Security and dependency pass over active repos: audits, outdated deps, secret scan, unpinned Actions; safe minor/patch remediation per tier. |
| **repo-groom** | Bring one repo up to the quality baseline (CI, AGENTS.md, LICENSE, README, lint), writing only what is missing and respecting tier policy. |
| **repo-health** | Read-only weekly sweep over every repo under the code root: dirty worktrees, unpushed commits, broken git state, stale branches, missing CI/AGENTS.md/LICENSE; writes REPO-HEALTH.md and nominates repos for the fixer skills. |

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
