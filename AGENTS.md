# AGENTS.md

Public, reusable agent skills (Claude Code, Codex, Copilot). One folder per
skill: `<skill>/SKILL.md` plus optional `references/`, `assets/`, `agents/`
and a bundled CLI. See README.md for the skill table and installer usage.

## Check

```bash
scripts/lint.sh   # SKILL.md frontmatter, paths, tool names, shellcheck, README table, agent YAML
scripts/test.sh   # cj-todo + install-skill.sh behaviour
git config core.hooksPath scripts/hooks   # run lint.sh on every commit
```

CI (`.github/workflows/ci.yml`) runs the same two scripts.

## Ground rules

- No hardcoded user paths (`/Users/<name>`, `/home/<name>`) in SKILL.md; lint fails on them.
- No agent-specific tool names (`ask_user_input`, `web_search`, `str_replace`, …) in SKILL.md prose; skills must port across agents.
- Adding or renaming a skill means updating the README skill table; lint checks it.
- Personal or machine-specific skills go in the private SKILLS-private repo, not here.
