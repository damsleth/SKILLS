# Troubleshooting Playbook

## `uxl init` fails because file exists

Cause: `uxl.config.mjs` already exists.
Fix: rerun with `uxl init --force` only if replacement is intended.

## `uxl shots` says flow mapping is incomplete

Cause: required flow inventory coverage is below 100%.
Fix:

1. Run `uxl flows check`.
2. Run `uxl flows list` to find unmapped/invalid entries.
3. Repair with `uxl flows add` / `uxl flows map`.
4. Re-run `uxl flows check` until complete.

## `uxl review` complains about missing manifest

Cause: screenshots were not captured yet.
Fix: run `uxl shots` first and confirm `.uxl/shots/manifest.json` exists.

## `uxl review --runner openai` fails

Common causes:

- Missing model: add `--model <model>` or set `review.model`.
- Missing API key: export `OPENAI_API_KEY`.
- Missing package: install with `npm i openai`.

## `uxl review` or `uxl implement` fails with codex command errors

Cause: Codex CLI binary is not available in PATH or configured path.
Fix: ensure `codex` is installed and executable, or set `review.codex.bin` / `implement.codex.bin` in config.

## `uxl implement` says report is missing

Cause: `.uxl/report.md` does not exist yet.
Fix: run `uxl review` first.

## Imported Playwright flows still leave onboarding pending

Cause: `uxl flows import-playwright` provides suggestions and keeps onboarding pending by design.
Fix: inspect imported entries, refine mapping, then run `uxl flows check` until complete.
