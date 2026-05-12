---
name: cj-yaams
description: This skill has moved to damsleth/SKILLS-private. Install it from there, or use cj-memory (public) for generic memory recall via the mnem suite.
moved-to: damsleth/SKILLS-private
status: stub
---

# cj-yaams (moved)

This skill has moved to **damsleth/SKILLS-private**.

It carried personal references (work accounts, organisations, hard-
coded paths) that fail the public SKILLS privacy bar. The
implementation is unchanged - only the location moved.

## Install from the new repo

```bash
git clone git@github.com:damsleth/SKILLS-private.git
cd SKILLS-private
./install-skill.sh --install cj-yaams
```

## Public alternative

- `cj-memory` routes generic memory recall through the mnem suite
  (which fans out to YAAMS) without baking in any user-specific
  examples. That's the right skill for any AI agent that wants
  cited recall over a user's history.
- The YAAMS tool itself is public and unchanged - install via
  `brew install damsleth/tap/yaams` or `pipx install yaams`.

This stub will be removed in the next public SKILLS release. The
installer refuses to install it so existing automation fails loudly
instead of pulling in a broken skill.
