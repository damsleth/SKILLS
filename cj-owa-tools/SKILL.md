---
name: cj-owa-tools
description: This skill has moved to damsleth/SKILLS-private. Install it from there, or use cj-memory (public) for generic memory recall via the mnem suite.
moved-to: damsleth/SKILLS-private
status: stub
---

# cj-owa-tools (moved)

This skill has moved to **damsleth/SKILLS-private**.

It carried personal references (work accounts, organisations, hard-
coded paths) that fail the public SKILLS privacy bar. The
implementation is unchanged - only the location moved.

## Install from the new repo

```bash
git clone git@github.com:damsleth/SKILLS-private.git
cd SKILLS-private
./install-skill.sh --install cj-owa-tools
```

## Public alternative

- For generic mail/calendar/Graph access, use the underlying CLIs
  directly (they have no personal flavor): `owa-cal`, `owa-mail`,
  `owa-graph`, `owa-people`, `owa-sched`, `owa-drive`, `owa-doctor`,
  and the `owa-piggy` auth broker. See:
  - https://github.com/damsleth/owa-tools
  - https://github.com/damsleth/owa-piggy
- `cj-memory` routes generic memory recall through the mnem suite
  without baking in any user-specific examples.

This stub will be removed in the next public SKILLS release. The
installer refuses to install it so existing automation fails loudly
instead of pulling in a broken skill.
