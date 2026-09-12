<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# Family

`loomground-mcp` exposes the planes over MCP. Its pipeline position is beside
`source -> loomground-ingest -> loomground-versum -> loomground-solver -> applied or diagnostic
planes`, reachable from any MCP client.

## Consumes

`pyproject.toml` declares the range; `requirements-dev.txt` git-pins the commit that range
resolves against while the planes are off an index. Those two files are the source of truth --
the table below is a reading of them.

| dependency | range | dev pin |
|---|---|---|
| `mcp` | `>=2,<3` | PyPI |
| `loomground-governance` | `>=0.11,<0.12` | `270e11d` |
| `loomground-versum` | `>=0.13,<0.15` | `15e7bfc` |
| `loomground-deontic` | `>=0.1,<0.3` | `35f8eab` |
| `loomground-factual` | `>=0.1,<0.2` | `db60a05` |
| `loomground-epistemic` | `>=0.1,<0.2` | `2c1dc8e` |
| `loomground-norm` | `>=0.1,<0.2` | `104a3ca` |
| `loomground-solver` | `>=0.5,<0.7` | `5b72f71` |
| `loomground-ingest` | `>=0.2,<0.4` | `ce9639b` |
| `loomground-brief` | `>=0.1,<0.3` | `80a4fc4` |
| `loomground-collapse` | `>=0.1,<0.3` | `f0214d9` |
| `loomground-escalation` | `>=0.1,<0.3` | `e97f1fb` |
| `loomground-falsifiability` | `>=0.1,<0.3` | `98e60ed` |
| `loomground-proxy` | `>=0.1,<0.3` | `dccef6f` |
| `loomground-mandate` | `>=0.1,<0.3` | `e96c59d` |
| `oversight-certificate` | `>=0.2,<0.3` | `8dbb4fa` |
| `governance-certification` | `>=0.1,<0.2` | `acc7741` |
| `norm-freshness` | `>=0.3,<0.4` | `e2951a6` |
| `obligation-discharge` | `>=0.1,<0.2` | `45058bc` |
| `effect-reconciliation` | `>=0.2,<0.3` | `a5164fb` |
| `enforcement-posture` | `>=0.5,<0.6` | `5e0096c` |
| `5d-nd` | `>=0.1,<0.2` | `5d71a78` |
| `loomground-audit-chain` | `>=0.1,<0.2` | `fd9b604` |
| `loomground-lock` | `>=0.1,<0.2` | `b8a2693` |
| `loomground-lane` | `>=0.1,<0.2` | `9bac236` |
| `loomground-drift` | `>=0.1,<0.2` | `f7de945` |
| `loomground-erasure` | `>=0.1,<0.2` | `df098be` |

The five runtime-control pins are release tags. `loomground-lock-v0.2.0` and `loomground-drift-v0.2.0` tag
commits whose `_version.py` still reads `0.1.0` -- release-please bumped the manifest, not the version
source -- so their ranges follow the version pip installs, not the tag name. `loomground-workspace`
(`e6e5e7d`, tag `v0.1.0`) is pinned in `requirements-dev.txt` as well: the audit chain, the lock and
erasure consume it, and there is no index to resolve it from.

The `loomground` catalogue and release register are consumed as data, not as a package:
`CATALOGUE.json` and `RELEASES.json` are vendored as `catalogue.json` and `releases.json`, and
checked byte for byte against the loomground repository at the commit they were taken from. The
loomground-topos `.lt` grammar is read the same way, by `tools/topos.py`, without a package. The
family's SKILL.md files are vendored under `skills/` at pinned commits (see
[`skills.md`](skills.md)).

## Consumed by

Any MCP client: Claude, Codex, the n8n MCP Client Tool, Langdock remote MCP.

## Third-party

`mcp >=2,<3`, the official SDK -- the one dependency outside the family.
