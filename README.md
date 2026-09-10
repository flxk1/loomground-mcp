<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# loomground-mcp

One MCP server exposing the Loomground planes as tools: versum, solver, ingest, the six operators and the assurance artifacts, over stdio or HTTP.

## Problem

Each plane is a Python package with its own call; a client that is not Python (Claude, Codex, n8n, Langdock) cannot reach any of them. One server, one tool per plane function, JSON in and out, and an error is a structured error, never a fake result.

## Install

```bash
pip install -r requirements-dev.txt   # git-pinned planes (no index yet)
pip install .                         # installs the `loomground-mcp` command
```

## Usage

```bash
loomground-mcp serve --transport stdio                    # for a local MCP client
loomground-mcp serve --transport sse --port 8765          # /sse and /messages/
loomground-mcp serve --transport streamable-http --port 8765   # /mcp
loomground-mcp tools                                      # the tool table as JSON
```

Every result is one envelope in `structuredContent` (and as JSON text):
`{plane, function, ok: true, result}` · `{plane, function, ok: false, error: {type, message}}` · `{plane, function, ok: false, unavailable: true, reason}`. The last two carry `isError`.

## Example

`policy.lg` is the six-line patch from the `loomground` README; `transport.json` proposes token `t1` (`data_transfer`, risk `high`) at gate `transfer`.

```
$ loomground-mcp serve --transport sse --port 8765 &
$ curl -sN --max-time 1 http://127.0.0.1:8765/sse
event: endpoint
data: /messages/?session_id=3dc2c4915a944260af82ec6dc95a1dd2

$ python example.py      # mcp.client.sse.sse_client + ClientSession: list_tools, call_tool("solver_evaluate", {patch_lg, transport_json})
21 tools: versum_index versum_claims versum_search solver_evaluate solver_verify solver_manifest ingest_text collapse escalation falsifiability proxy mandate brief oversight_issue oversight_verify govcert_verify norm_freshness obligation_admit effect_reconcile enforcement_compare nd_digest
{"plane": "loomground-solver", "ok": true, "status": "escalate", "evaluation": {"transfer": {"verdict": "reserved", "master": "withhold"}}, "undecided": ["t1"]}
```

## Interface

| Tool | Plane | Function | In → out |
|---|---|---|---|
| `versum_index(folder, profile="generic")` | loomground-versum | `versum.store.index.index_folder` | folder → index summary; writes `<folder>/.versum` |
| `versum_claims(folder, limit=100)` | loomground-versum | `<folder>/.versum/claims.csv` | rows with `source_urn`, `span_start`, `span_end`, `marker`, `text`, projections |
| `versum_search(folder, query, k=10, filters?)` | loomground-versum | `versum.store.retrieve.SearchIndex` / `from_kg` | hits with spans; hybrid over a materialised KG (`by-domain/`), BM25 over a plain index; `unavailable` when there is nothing to search |
| `solver_evaluate(patch_lg, transport_json?)` | loomground-solver | `loomground_solver.loomground.reason` | `.lg` + transport → status, accepted/undecided/rejected, trace |
| `solver_verify(request_json)` | loomground-solver | `default_service().verify` | `reasoning.interop` 1.0 request → result with replayable trace |
| `solver_manifest()` | loomground-solver | `default_service().manifest` | protocol manifest |
| `ingest_text(text, ingesters?, max_input_chars?)` | loomground-ingest | `loomground_ingest.ingest_text` | text → nodes, edges, rejections, quarantined, the subgraphs; `unavailable` when no ingester claims the text |
| `collapse(constituents)` | loomground-collapse | `collapse` | `[{name, state}]` → overall verdict + per-term |
| `escalation(factors, delegated, ladder, requested?)` | loomground-escalation | `ceiling` / `autonomy_verdict` | granted level, binding factor, verdict |
| `falsifiability(evidence, floor?)` | loomground-falsifiability | `support_verdict` / `best_support` | ranked evidence → SATISFIED or OPEN |
| `proxy(proxies, readings)` | loomground-proxy | `check_proxies` / `fold_substitutions` | substitutions: gamed, misleading, unchecked, tracking |
| `mandate(mandate, steps, evidence?)` | loomground-mandate | `detect` / `fold_divergences` | divergences; `evidence = {kg_root, libraries?}` names a synced versum store; without a provider → `unavailable` |
| `brief(premises?, space?, negative_space?, divergences?)` | loomground-brief | `oversight_brief` | ordered brief items, `settled_omitted`; nothing supplied → `unavailable` |
| `oversight_issue(cert, signing_key_pem, keyid="")` | oversight-certificate | `issue` | certificate + caller's Ed25519 key → DSSE envelope |
| `oversight_verify(envelope, public_key_pem, now, required_basis?)` | oversight-certificate | `verify` | ok, findings, independence |
| `govcert_verify(envelope, public_key_pem)` | governance-certification | `verify.verify` | ok, findings, statement |
| `norm_freshness(pins, observed)` | norm-freshness | `assess` | per-rule freshness verdicts + determinations |
| `obligation_admit(obligations, declaration)` | obligation-discharge | `admit` | status, `may_permit`, blocking, owed |
| `effect_reconcile(auths, effects, since, until, match_window_s=0)` | effect-reconciliation | `reconcile` | status, matched, the three mismatches, rates |
| `enforcement_compare(a, b)` | enforcement-posture | `compare` | unchanged, hardened, weakened, incomparable |
| `nd_digest(ref)` | 5d-nd | `canonicalize` / `digest` / `validate` | canonical bytes, sha256, validity |

Enum arguments take the plane's own names (`PRESENT`, `decided`, `editorial`, …). Keys are passed in per call as PEM and never generated or stored. Canonicalisation uses `rfc8785` when installed, else sorted compact JSON; the envelope names which.

## Family

Interface: exposes the planes over MCP; consumes versum, solver, ingest, the six operators, the assurance artifacts; consumed by any MCP client. Pipeline position: beside the pipeline, not in it.

- consumes: [loomground-versum](https://github.com/flxk1/loomground-versum) `>=0.13,<0.14` · [loomground-solver](https://github.com/flxk1/loomground-solver) `>=0.5,<0.6` · [loomground-ingest](https://github.com/flxk1/loomground-ingest) `>=0.2,<0.3` · brief, collapse, escalation, falsifiability, mandate, proxy `>=0.1,<0.2` · [oversight-certificate](https://github.com/flxk1/oversight-certificate), [governance-certification](https://github.com/flxk1/governance-certification), [norm-freshness](https://github.com/flxk1/norm-freshness), [obligation-discharge](https://github.com/flxk1/obligation-discharge), [effect-reconciliation](https://github.com/flxk1/effect-reconciliation), [enforcement-posture](https://github.com/flxk1/enforcement-posture), [5d-nd](https://github.com/flxk1/5d-nd)
- consumed by: any MCP client — Claude, Codex, the n8n MCP Client Tool node, Langdock remote MCP
- third-party: [`mcp`](https://github.com/modelcontextprotocol/python-sdk) `>=2,<3` (the official SDK; its `MCPServer`, formerly FastMCP)

## Status

0.1.0 · 21 tools · 24 tests (one per tool, SSE and streamable-HTTP smokes) · Python >=3.10 · mcp 2.x

## License

Apache-2.0 — `LICENSES/Apache-2.0.txt`, `NOTICE`.
