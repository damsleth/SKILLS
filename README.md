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

## Moved to SKILLS-private

These skills carried personal-infra references (work accounts, organisations, specific paths) that didn't pass the public privacy bar. They moved to a private sibling repo with the same names and unchanged behaviour:

| Skill | Where it went |
|-------|---------------|
| **cj-did** | damsleth/SKILLS-private |
| **cj-meeting-notes** | damsleth/SKILLS-private |
| **cj-notes** | damsleth/SKILLS-private |
| **cj-owa-tools** | damsleth/SKILLS-private |
| **cj-timereg** | damsleth/SKILLS-private |
| **cj-weekly-review** | damsleth/SKILLS-private |
| **cj-yaams** | damsleth/SKILLS-private (use **cj-memory** here for a generic alternative) |

Each name above still has a stub `SKILL.md` in this repo for one release - the stub explains where the skill went and the installer refuses to install it. The stubs will be removed in the next public release.

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

If you try to install a moved skill by its old name, the installer prints the new location:

```
$ ./install-skill.sh --install cj-did
Refusing to install 'cj-did': this skill is a stub redirect.
  The real implementation lives in: damsleth/SKILLS-private
  Install it from there:
    git clone git@github.com:damsleth/SKILLS-private.git && cd SKILLS-private && ./install-skill.sh --install cj-did
```

## Structure

Each skill folder contains:

- `SKILL.md` — the main prompt (required)
- `references/` — supporting docs the skill can read at runtime
- `agents/` — agent configs (e.g. OpenAI agent YAML)
- `assets/` — templates, examples, config files

## License

MIT
