<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# What the suite covers

99 tests:

- one per tool, across all 41;
- script parity for the seven solver skill tools;
- the loomground-topos examples corpus;
- catalogue and release-register parity against the loomground repository;
- skill parity against every repository at its pinned commit;
- the catalogue's skill list against the vendored skill index;
- stdio, SSE and streamable-HTTP smokes;
- the bearer-token gate on both HTTP transports;
- the hosts converter, for both targets.

## Fixtures that live outside the repository

The parity tests read checkouts the CI job fetches at the pinned commits and passes in by
environment variable: `LOOMGROUND_SOLVER_SKILLS` (the solver skill scripts, which ship in the
checkout rather than the wheel), `LOOMGROUND_TOPOS_EXAMPLES`, `LOOMGROUND_CATALOGUE`,
`LOOMGROUND_RELEASES` and `LOOMGROUND_SKILLS_ROOT`. When a checkout is absent the items that need
it skip; they are only ever skipped, never faked.
