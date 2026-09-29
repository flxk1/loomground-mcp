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
| `loomground-governance` | `>=0.11,<0.12` | `ff2afcd` |
| `loomground-versum` | `>=0.13,<0.15` | `eaf316d` |
| `loomground-deontic` | `>=0.1,<0.3` | `0f57e8d` |
| `loomground-factual` | `>=0.1,<0.3` | `ebf9fe1` |
| `loomground-epistemic` | `>=0.1,<0.3` | `10a3d69` |
| `loomground-norm` | `>=0.1,<0.2` | `9d5f68f` |
| `loomground-solver` | `>=0.5,<0.7` | `2cdf037` |
| `loomground-ingest` | `>=0.2,<0.4` | `9a99494` |
| `loomground-brief` | `>=0.1,<0.3` | `f9a092d` |
| `loomground-collapse` | `>=0.1,<0.3` | `8469398` |
| `loomground-escalation` | `>=0.1,<0.3` | `cd2a10a` |
| `loomground-falsifiability` | `>=0.1,<0.3` | `dc59847` |
| `loomground-proxy` | `>=0.1,<0.3` | `ba3598a` |
| `loomground-mandate` | `>=0.1,<0.3` | `d37cc61` |
| `oversight-certificate` | `>=0.2,<0.3` | `8dbb4fa` |
| `governance-certification` | `>=0.1,<0.3` | `3d7a112` |
| `norm-freshness` | `>=0.3,<0.4` | `e2951a6` |
| `obligation-discharge` | `>=0.1,<0.2` | `4030c2d` |
| `effect-reconciliation` | `>=0.2,<0.3` | `a5164fb` |
| `enforcement-posture` | `>=0.5,<0.6` | `5e0096c` |
| `5d-nd` | `>=0.1,<0.3` | `12fbde0` |
| `loomground-audit-chain` | `>=0.1,<0.2` | `7a6e7a4` |
| `loomground-lock` | `>=0.1,<0.3` | `f99e24b` |
| `loomground-lane` | `>=0.1,<0.2` | `9bac236` |
| `loomground-drift` | `>=0.1,<0.3` | `e8279ec` |
| `loomground-erasure` | `>=0.1,<0.2` | `df098be` |
| `policy-compiler` | `>=0.3,<0.4` | `d14e9a8` |
| `evidence-emitter` | `>=0.1,<0.2` | `07af3e3` |
| `privacy-shield` | `>=2,<3` | `dc71ff0` |
| `a2a-compliance` | `>=0.3,<0.4` | `fd22399` |

The five runtime-control pins are release tags. `loomground-lock-v0.2.0` and `loomground-drift-v0.2.0` tag
commits whose `_version.py` still reads `0.1.0` -- release-please bumped the manifest, not the version
source -- so their ranges follow the version pip installs, not the tag name. `loomground-workspace`
(`b022d61`, tag `v0.1.0`) is pinned in `requirements-dev.txt` as well: the audit chain, the lock and
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
