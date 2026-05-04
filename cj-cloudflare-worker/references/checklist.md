# Cloudflare Worker Checklist

Use this checklist when adding a Worker to an existing repository.

## 1. Inventory

- Find `package.json`, lockfiles, build scripts, and output directories.
- Search for existing Cloudflare files: `wrangler.json`, `wrangler.jsonc`, `wrangler.toml`, `.dev.vars`, `.env`.
- Search `.github/workflows/` for existing CI or deploy jobs.
- Confirm whether the Worker fronts static assets, exposes APIs, or both.

## 2. Gather Inputs

- Production Worker name.
- Preview Worker name.
- Worker entrypoint path.
- Static assets directory, if any.
- Production branch. Default: `main`.
- Hostnames to attach.
- Which hostnames live in Cloudflare-managed zones.
- Whether a Durable Object is required.
- Whether preview deploys should comment the preview URL on pull requests.

## 3. Pick the Base Pattern

- Normal Worker with static assets or APIs: `../assets/wrangler.custom-domain.jsonc`
- Worker with a new Durable Object: `../assets/wrangler.durable-object.jsonc`

## 4. Wire Deployment

- Add production workflow at `.github/workflows/deploy-worker.yml`.
- Add preview workflow only when needed.
- Adapt install steps to the package manager actually used by the repo.
- Reuse the repository's existing test/build jobs when practical.

## 5. Wire Secrets

- Local `.env` or `.dev.vars`, kept out of git.
- GitHub secret: `CLOUDFLARE_API_TOKEN`
- GitHub secret: `CLOUDFLARE_ACCOUNT_ID`

If the deployment flow uses custom API calls beyond Wrangler, add zone-specific secrets only when they are truly required.

## 6. Verify

- Confirm workflow triggers match the intended branches.
- Confirm preview concurrency includes the PR number or ref.
- Confirm production and preview Worker names differ.
- Confirm every custom domain is unique and belongs to a valid zone.
- Confirm every new Durable Object class has a matching migration entry.
