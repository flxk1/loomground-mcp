<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# Tools

Every result is one envelope in `structuredContent` (and as JSON text):
`{plane, function, ok: true, result}` · `{plane, function, ok: false, error: {type, message}}` · `{plane, function, ok: false, unavailable: true, reason}`. The last two carry `isError`.


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

