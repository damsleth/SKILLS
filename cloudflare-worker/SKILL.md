---
name: cloudflare-worker
description: Create or update a Cloudflare Worker inside an existing GitHub repository and deploy it to one or more custom domains. Use when Codex needs to add or revise `wrangler.jsonc`, wire GitHub Actions deployment on `main` or preview branches, configure custom domains or DNS-backed hostnames, request Cloudflare account credentials and GitHub secrets, or add optional Durable Objects with SQLite-backed storage for a public or private repo.
---

# Cloudflare Worker

Create Workers in-place inside an existing repository. Preserve the repo's package manager, language, build system, and directory layout instead of replacing the project with a starter.

## Retrieval First

Cloudflare configuration changes often. Retrieve current docs before making or reviewing production changes for:

- Wrangler configuration: `https://developers.cloudflare.com/workers/wrangler/configuration/`
- Custom domains: `https://developers.cloudflare.com/workers/configuration/routing/custom-domains/`
- Durable Object migrations: `https://developers.cloudflare.com/durable-objects/reference/durable-objects-migrations/`
- API token templates and permissions: `https://developers.cloudflare.com/fundamentals/api/reference/template/`

Load `./references/checklist.md` for the execution flow. Load `./references/patterns.md` for file patterns and token guidance.

## Workflow

1. Inspect the repository first.
- Detect the package manager from the lockfile.
- Find the app entrypoint, build command, static output directory, and any existing Cloudflare files.
- Read existing GitHub workflows before adding new ones.
- Prefer adapting the current project over introducing a parallel structure.

2. Resolve the minimum missing deployment inputs.
- Production Worker name.
- Preview Worker name or preview environment name.
- `main` script path and optional static assets directory.
- Production branch. Default to `main`.
- Hostnames to attach and which zones are managed in Cloudflare.
- Whether preview deploys should run on pull requests, a preview branch, or both.
- Whether Durable Objects are needed and what state they hold.

3. Add or update `wrangler.jsonc`.
- Use `./assets/wrangler.custom-domain.jsonc` for a normal Worker.
- Use `./assets/wrangler.durable-object.jsonc` when the Worker needs a Durable Object.
- Keep the repo's real entrypoint and build output paths.
- Set `compatibility_date` to the current date unless the repo already pins an older baseline for compatibility reasons.
- Use one route object per hostname.
- Use `custom_domain: true` only for hostnames inside Cloudflare-managed zones.
- If the Worker should sit in front of an existing origin on only part of a hostname, use a route pattern instead of a custom domain.
- Keep `env.preview` separate from production so preview deploys do not overwrite the primary Worker.

4. Add the Worker runtime changes.
- Preserve the repository's JS or TS conventions.
- If the app is mostly static, route the Worker to the built assets directory instead of replacing the build system.
- If a Durable Object is requested, use SQLite-backed Durable Objects for new classes by default.
- Add a migration entry whenever introducing a Durable Object class.
- Do not attempt to convert an already deployed KV-backed Durable Object to SQLite in place.

5. Add GitHub Actions deployment.
- Start from `./assets/deploy-worker.yml`.
- Add `./assets/deploy-worker-preview.yml` only when preview deploys are requested.
- Keep Node on GitHub Actions as the default runtime unless the repo clearly uses something else.
- Adapt install commands to the lockfile: `npm ci`, `pnpm install --frozen-lockfile`, `yarn install --frozen-lockfile`, or the repo's existing install wrapper.
- Reuse existing composite actions or shared setup steps when the repo already has them.
- Keep the preview workflow guard that skips pull requests from forks so secrets are not exposed.

6. Request credentials and wire secrets.
- Ask for a Cloudflare API token with the minimum needed permissions for Workers and DNS changes.
- Default local storage to a gitignored `.env` file in the repo because this user asked for that path.
- Create or update `.env.example` using `./assets/cloudflare.env.example`.
- Mirror the same values in GitHub Actions secrets: `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`.
- Never commit live secrets.

7. Verify without assuming deploy access.
- Validate JSONC shape, workflow syntax, and package scripts locally.
- Only run `wrangler deploy` when the user explicitly wants a live deploy or credentials are already provided.
- If a preview workflow is added, verify that the PR comment step updates an existing bot comment instead of spamming new comments.

## Decision Rules

- Prefer custom domains over legacy wildcard routes when the Worker should own the entire hostname.
- Prefer `workers.dev` preview deployments unless the user explicitly asks for preview custom domains.
- If a hostname belongs to a zone not managed in the current Cloudflare account, stop short of claiming automatic DNS setup and explain the external DNS action needed.
- If the repository already contains deploy workflows, extend them rather than adding a conflicting second pipeline.
- If multiple hostnames are needed, keep them in one `routes` array unless there is a clear need for separate Workers.
- For private repositories, bias toward GitHub Actions with repo secrets over local-only deployment steps.

## Assets

- `./assets/wrangler.custom-domain.jsonc`
- `./assets/wrangler.durable-object.jsonc`
- `./assets/deploy-worker.yml`
- `./assets/deploy-worker-preview.yml`
- `./assets/cloudflare.env.example`

## Response Shape

When finishing a task with this skill, report:

- Files created or changed.
- Required GitHub secrets.
- Any unresolved hostname, zone, or credential assumptions.
- What was verified locally and what was not run.
