# Cloudflare Worker Patterns

## Official Notes To Preserve

- Cloudflare documents that custom domains create the DNS record and certificate for a hostname inside a Cloudflare-managed zone.
- Cloudflare documents that you cannot create a custom domain on a hostname with an existing CNAME record or on a zone you do not own.
- Cloudflare's API token template reference shows the Workers template includes `Workers Scripts Write` at the account level and `Workers Routes Write` at the zone level.
- For DNS changes, add `DNS Write` on the relevant zones.
- Cloudflare recommends SQLite-backed Durable Objects for new Durable Object classes.
- New Durable Object classes need a migration entry such as `new_sqlite_classes`.

## Worker Configuration Pattern

Use `wrangler.jsonc` instead of `wrangler.toml` unless the repository already standardizes on TOML.

Keep this shape:

```jsonc
{
  "$schema": "node_modules/wrangler/config-schema.json",
  "name": "app-name",
  "main": "src/worker.ts",
  "compatibility_date": "2026-03-19",
  "workers_dev": true,
  "routes": [
    {
      "pattern": "app.example.com",
      "custom_domain": true
    }
  ],
  "env": {
    "preview": {
      "name": "app-name-preview",
      "workers_dev": true
    }
  }
}
```

Add `"assets": { "directory": "./dist" }` when the repository builds static output that the Worker should serve.

Use a custom domain when the Worker is the origin for an entire hostname. Use a route pattern only when the Worker must sit in front of an existing origin, and remember that route-based Workers require a proxied DNS record for the hostname.

## Durable Object Pattern

Add a binding and a migration together:

```jsonc
{
  "durable_objects": {
    "bindings": [
      {
        "name": "APP_STATE",
        "class_name": "AppState"
      }
    ]
  },
  "migrations": [
    {
      "tag": "v1",
      "new_sqlite_classes": ["AppState"]
    }
  ]
}
```

Use a new migration tag each time the Durable Object schema or class layout changes.

## GitHub Actions Pattern

- Production deploy: push to `main` plus `workflow_dispatch`.
- Preview deploy: `pull_request` plus `workflow_dispatch`.
- Skip preview deploys from forks when secrets are required.
- Comment the preview `workers.dev` URL back on the pull request only after a successful deploy.

## Token Guidance

Minimum typical permissions:

- `Workers Scripts Write` on the Cloudflare account.
- `Workers Routes Write` on the zones that will host the Worker.
- `DNS Write` on the zones where the skill should manage DNS entries.

Scope the token to the smallest practical account and zones.
