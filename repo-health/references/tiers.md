# Tiers file: `.repo-tiers.json`

Single source of truth for the repo-routine family (repo-health, repo-groom,
repo-deps, repo-deep). It lives at the root of the code directory
(`$REPO_ROOT`, default `~/code`) and is optional.

```json
{
  "policy": { "S-priv": "free-text note per tier, informational" },
  "tiers": {
    "my-tool":      { "tier": "S-pub" },
    "CLI/other":    { "tier": "S-priv" },
    "work/service": { "tier": "W" }
  }
}
```

Keys under `tiers` are repo paths relative to the root (one or two levels
deep, e.g. `CLI/other`). Only `tiers.<path>.tier` is read; other fields are
ignored.

| Tier | Meaning | Agent autonomy |
|---|---|---|
| `S-priv` | solo private repo | commit and push |
| `S-pub` | solo public repo | commit and push; releases/tags need approval |
| `W` | work repo | new branch + local commits only; the user pushes |
| `W-ro` | work repo, read-only | reports only; no commits, branches or pushes |
| `archive` | dormant | no routine touches it |
| `external` | third-party clone | out of scope for all routines |

## Without the file

- repo-health sweeps every discovered repo and reports no tier column.
- repo-deps audits every discovered repo.
- repo-groom and repo-deep treat every repo as untiered and refuse to write,
  since the commit policy is unknown. Create the file (or add the repo) to
  enable them.
