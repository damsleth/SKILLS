---
name: cj-ux-loop-onboarding
description: Install, configure, onboard, and operate the @damsleth/ux-loop npm package (`uxl`) in Node/npm repositories. Use when asked to set up `uxl`, create or edit `uxl.config.mjs`, map required user flows (`capture.flowInventory` to `capture.flowMapping`), run CLI commands (`uxl init|flows|shots|review|implement|run`), or troubleshoot UX loop pipeline issues.
---

# cj-ux-loop-onboarding

## Overview

Use this skill to get `@damsleth/ux-loop` installed, fully onboarded, and running reliably in a project.
Prioritize strict flow coverage so `uxl shots` is unblocked and the full `shots -> review -> implement` loop can run.

## Follow This Workflow

1. Confirm project readiness.
- Ensure the repository has a `package.json` and uses Node 20+.
- Run all `uxl` commands from the repo root (same folder as `uxl.config.mjs`).

2. Install dependencies.
- Install `uxl`: `npm i -D @damsleth/ux-loop`
- Install Playwright for capture: `npm i -D playwright`
- Install OpenAI SDK only for OpenAI review runner: `npm i openai`

3. Initialize config.
- Run `uxl init`
- Use `uxl init --non-interactive` for automation/CI.
- Use `uxl init --force` only when intentionally replacing an existing config file.

4. Complete user-flow onboarding (mandatory for screenshots).
- Run `uxl flows check`.
- If coverage is incomplete, repair mapping with:
- `uxl flows list`
- `uxl flows add --id <id> --label <label> [--path <path>] [--to <flowName>]`
- `uxl flows map --id <inventoryId> --to <flowName[,flowName]>`
- `uxl flows import-playwright --yes` (seed suggestions, then verify manually)
- Repeat `uxl flows check` until coverage is 100% for all required inventory entries.

5. Run the UX loop pipeline.
- Capture screenshots: `uxl shots`
- Create review report: `uxl review`
- Apply implementation changes: `uxl implement`
- Or run end-to-end: `uxl run`

6. Handle runner and target overrides when needed.
- Review runner:
- Codex runner (default): `uxl review --runner codex`
- OpenAI runner: `uxl review --runner openai --model <model>` with `OPENAI_API_KEY` set
- Implement target:
- `uxl implement --target current`
- `uxl implement --target branch --branch <name>`
- `uxl implement --target worktree --worktree <path>`

7. Verify expected artifacts.
- Screenshot manifest: `.uxl/shots/manifest.json`
- Review output: `.uxl/report.md`
- Logs: `.uxl/logs`

## Guardrails

- Enforce strict mapping: do not bypass incomplete required flow coverage.
- Keep `capture.flowMapping` aligned with real `capture.playwright.flows[].name` values.
- Use slug-case IDs for flow inventory entries (for example `checkout-confirmation`).
- Prefer `uxl flows import-playwright` for bootstrap, then review and fix names/paths manually.
- Keep onboarding status as `pending` until `uxl flows check` reports complete coverage.

## References

- Use [references/commands.md](references/commands.md) for command quick reference.
- Use [references/config-and-onboarding.md](references/config-and-onboarding.md) for config shape and mapping semantics.
- Use [references/troubleshooting.md](references/troubleshooting.md) for common error-to-fix playbook.
