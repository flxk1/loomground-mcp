<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# loomground-mcp

One MCP server exposing the Loomground planes as tools: versum, the four languages, solver and its skills, ingest, operators, assurance; stdio or HTTP.

## Problem

Each plane is a Python package with its own call, out of reach for Claude, Codex, n8n or Langdock. One server, one tool per plane function, JSON in and out; an error comes back as a structured error.

## Install

```bash
pip install -r requirements-dev.txt   # git-pinned planes
pip install .                         # installs the `loomground-mcp` command
```

## Usage

```bash
loomground-mcp serve --transport stdio|sse|streamable-http [--port 8765]
loomground-mcp tools      # the tool table as JSON
```


## Example

`policy.lg`: the six-line patch from the `loomground` README; `transport.json`: token `t1`, risk `high`, at gate `transfer`.

```
$ loomground-mcp serve --transport sse --port 8765 &
$ curl -sN --max-time 1 http://127.0.0.1:8765/sse
event: endpoint
data: /messages/?session_id=d6f25abfea2945d49abb1cd724fc1100

$ python example.py      # sse_client + ClientSession: list_tools, call_tool("solver_evaluate", …), call_tool("solver_strategy", …)
41 tools: loomground_catalogue … nd_digest
{"plane": "loomground-solver", "ok": true, "status": "escalate", "evaluation": {"transfer": {"verdict": "reserved", "master": "withhold"}}, "undecided": ["t1"]}
{"method": "minimax_regret", "result": {"choice": "buy", "ranking": ["buy", "build"], "scores": {"build": 40.0, "buy": 30.0}}}
```

## Interface

41 tools, one per plane function (the seven solver skill scripts count as functions; the topos reader, the catalogue, the release register and the skill index are this repository's); signatures, envelopes and enums: `docs/tools.md`. Call `loomground_catalogue` first: the family map, the pipeline order, how documents become an `.lg` patch. `loomground_releases` is the family's release/pin register — every catalogued repository with version, tag, commit, family, tools and skills; range, pin and status per dependency edge; accepted transitive pins — vendored from `RELEASES.json` the same way.

Prompts: 22 skills (`prompts/list`; one per vendored SKILL.md, `prompts/get` returns its body under one header line `Skill <name> from <repo> @ <commit>; tools: <allowed-tools>`); `loomground_skill(name?)` returns the same index and bodies as a tool. The index carries 22 records — the family's conformant Agent Skills in public repositories, at each repository's pushed main commit — and every body is vendored (`src/loomground_mcp/skills/<repo>/<name>/SKILL.md`, `tests/test_skills_parity.py` checks them byte for byte against the repositories). The one shared skill name is qualified: `loomground/loomground` and `loomground-governance/loomground`.

| plane | tools |
|---|---|
| loomground | `loomground_catalogue` · `loomground_releases` · `loomground_skill` |
| loomground-versum | `versum_index` · `versum_claims` · `versum_search` · `versum_capture` · `versum_suggest` · `versum_confirm` · `versum_canon` |
| loomground-deontic | `deontic_parse` · `deontic_conflicts` |
| loomground-factual · -epistemic · -norm · -topos | `factual_lower` · `epistemic_extract` · `norm_extract` · `topos_parse` |
| loomground-solver | `solver_evaluate` · `solver_verify` · `solver_manifest` · `solver_analyse_risks` · `solver_estimate_liability` · `solver_litigation_risk` · `solver_opponent_model` · `solver_probability` · `solver_strategy` · `solver_advise_addons` |
| loomground-ingest | `ingest_text` |
| operators | `collapse` · `escalation` · `falsifiability` · `proxy` · `mandate` · `brief` |
| assurance | `oversight_issue` · `oversight_verify` · `govcert_verify` · `norm_freshness` · `obligation_admit` · `effect_reconcile` · `enforcement_compare` · `nd_digest` |

Result envelope: `{plane, function, ok, result | error | unavailable}`; keys are passed per call as PEM.

## Family

Interface: exposes the planes over MCP. Pipeline position: beside `source → loomground-ingest → loomground-versum → loomground-solver → applied or diagnostic planes`, reachable from any MCP client.

- consumes: loomground (`CATALOGUE.json` and `RELEASES.json`, vendored as `catalogue.json` and `releases.json`; no package) · the family's SKILL.md files (vendored under `skills/` at pinned commits) · loomground-governance `>=0.11,<0.12` · loomground-versum `>=0.13,<0.14` · loomground-deontic `>=0.1,<0.3` · loomground-factual `>=0.1,<0.2` · loomground-epistemic `>=0.1,<0.2` · loomground-norm `>=0.1,<0.2` · loomground-topos (the `.lt` grammar, read by `tools/topos.py`; no package) · loomground-solver `>=0.5,<0.6` (kernel + the seven skill scripts as tools) · loomground-ingest `>=0.2,<0.3` · the six operators · the seven assurance artifacts (pins: `requirements-dev.txt`)
- consumed by: any MCP client: Claude, Codex, n8n MCP Client Tool, Langdock remote MCP
- third-party: `mcp` `>=2,<3`, the official SDK

## Status

0.1.0 · 41 tools · 22 prompts · 93 tests (one per tool, script parity for the seven solver skill tools, the loomground-topos examples corpus, catalogue and release-register parity against the loomground repository, skill parity against every repository at its pinned commit, catalogue–index consistency, stdio, SSE and streamable-HTTP smokes) · Python >=3.10 · mcp 2.x

## License

Apache-2.0 — `LICENSES/Apache-2.0.txt`, `NOTICE`.
