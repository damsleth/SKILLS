---
name: cj-weekly-review
description: This skill has moved to damsleth/SKILLS-private. Install it from there, or use cj-memory (public) for generic memory recall via the mnem suite.
moved-to: damsleth/SKILLS-private
status: stub
---

# cj-weekly-review (moved)

This skill has moved to **damsleth/SKILLS-private**.

It carried personal references (work accounts, organisations, hard-
coded paths) that fail the public SKILLS privacy bar. The
implementation is unchanged - only the location moved.

## Install from the new repo

```bash
git clone git@github.com:damsleth/SKILLS-private.git
cd SKILLS-private
./install-skill.sh --install cj-weekly-review
```

## Public alternative

- `cj-memory` routes generic memory recall through the mnem suite
  without baking in any user-specific examples.
- The underlying tools live at:
  - mnem: https://github.com/damsleth/mnem
  - yaams: https://github.com/damsleth/yaams
  - cognitive-ledger: https://github.com/damsleth/cognitive-ledger
  - owa-tools: https://github.com/damsleth/owa-tools

This stub will be removed in the next public SKILLS release. The
installer refuses to install it so existing automation fails loudly
instead of pulling in a broken skill.
