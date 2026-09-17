<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# What the suite covers

167 tests:

- one per tool, across all 55;
- the graceful degradation of each optional plane, with its package absent;
- script parity for the seven solver skill tools;
- the loomground-topos examples corpus;
- catalogue and release-register parity against the loomground repository;
- skill parity against every repository at its pinned commit, directory for directory;
- the vendored skill tree against `skills/vendored.json`, both directions, and the packaging globs
  against the same list;
- `skills_lint` over the vendored tree, for the rules only it holds;
- every dependency this server declares against the release register's edges;
- the catalogue's skill list against the vendored skill index;
- stdio, SSE and streamable-HTTP smokes;
- the bearer-token gate on both HTTP transports;
- the hosts converter, for both targets.

## Fixtures that live outside the repository

The parity tests read checkouts the CI job fetches at the pinned commits and passes in by
environment variable: `LOOMGROUND_SOLVER_SKILLS`, `LOOMGROUND_TOPOS_EXAMPLES`,
`LOOMGROUND_CATALOGUE`, `LOOMGROUND_RELEASES`, `LOOMGROUND_SKILLS_ROOT`, and `REPO_STANDARDS` for
`skills_lint`. When a checkout is absent the items that need it skip; they are only ever skipped,
never faked. A skip is a local convenience only: under `CI`,
`test_ci_has_every_pinned_source` requires every one of them and fails by name, so a lost fetch
cannot quietly stop a parity test from asserting anything.

What a vendored skill ships is not among them: the manifest check, the package-data check and the
solver scripts now run against the package itself, so the completeness of a vendored skill is
decided inside this repository with nothing fetched.
