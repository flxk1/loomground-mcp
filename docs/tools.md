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
| `versum_capture(folder, source_path, profile="generic")` | loomground-versum | `versum.write.capture_file` | one `.txt`/`.md`/`.pdf` → `admitted` or `duplicate`, `urn`, `claim_count`, `index`; an unsupported source is a `CaptureError` |
| `versum_suggest(folder, min_sources=1)` | loomground-versum | `versum.concept.curate.suggest_folder` | curation-queue counts + `candidates` (`concept_id`, `label`, `n_claims`, `n_sources`, `seed`, `example`) with at least `min_sources` sources; writes `.versum/curation/`, never the graph; `unavailable` before indexing |
| `versum_confirm(folder, concept_ids?, min_sources=1)` | loomground-versum | `versum.concept.curate.confirm_folder` | promotes the explicit pick, else every candidate with at least `min_sources` sources, into `.versum/concepts.csv` + `semantic_edges.csv`; `unavailable` without a queue |
| `versum_canon(folder, config?, m_max=1)` | loomground-versum | `versum.concept.canon.curate_kg` / `curate_domain_folder` | coordinate-identity canon; `layout` = `kg` (a sync `config` or a `by-domain/` root → `canon.json` + `convergence.json`), `domain` (one by-domain folder) or `index` (a plain `.versum`, its concept tables overwritten) |
| `deontic_parse(statement)` | loomground-deontic | `deontic.grammar.parse` | `[if [c] then] O|P|F(bearer : action) [unless [e]]` → formula fields, `formula` (canonical render), `round_trip`, `validation`; not a statement → `DeonticSyntaxError` |
| `deontic_conflicts(statements)` | loomground-deontic | `deontic.contract.conflict_candidates` | parsed formulae + candidate `may-conflict-with` edges (same bearer and action, incompatible modality); flagged, never resolved |
| `solver_evaluate(patch_lg, transport_json?)` | loomground-solver | `loomground_solver.loomground.reason` | `.lg` + transport → status, accepted/undecided/rejected, trace |
| `solver_verify(request_json)` | loomground-solver | `default_service().verify` | `reasoning.interop` 1.0 request → result with replayable trace |
| `solver_manifest()` | loomground-solver | `default_service().manifest` | protocol manifest |
| `solver_analyse_risks(vectors?, options?, method="pareto", extra?)` | loomground-solver | `skills/analyse-risks/scripts/run.py` → `method("pareto")` | `{risk: [impact, likelihood, …]}` → `{method, result: {choice, ranking, scores}}`, frontier first |
| `solver_estimate_liability(prior?, likelihoods?, evidence?, method="bayesian_update", extra?)` | loomground-solver | `skills/estimate-liability/scripts/run.py` → `method("bayesian_update")` | `{hypothesis: p}`, `{hypothesis: {evidence: p}}`, the observed key → posterior as `scores`, MAP as `choice` |
| `solver_litigation_risk(options?, payoffs?, probabilities?, method="expected_utility", extra?)` | loomground-solver | `skills/litigation-risk-assessor/scripts/run.py` → `method("expected_utility")` | `{strategy: {outcome: value}}`, `{outcome: p}` (uniform when absent) → expected utilities, `choice` |
| `solver_opponent_model(options?, payoffs?, probabilities?, method="expected_utility", extra?)` | loomground-solver | `skills/opponent-modeler/scripts/run.py` → `method("expected_utility")` | the opponent's payoffs → their likely move; `method="maximin"` attributes a cautious rule |
| `solver_probability(prior?, likelihoods?, evidence?, method="bayesian_update", extra?)` | loomground-solver | `skills/probability-tracker/scripts/run.py` → `method("bayesian_update")` | one Bayesian update → posterior as `scores` |
| `solver_strategy(options?, payoffs?, method="minimax_regret", extra?)` | loomground-solver | `skills/strategic-analysis/scripts/run.py` → `method("minimax_regret")` | `{strategy: {state: value}}` → regrets as `scores` (lower first), `choice` |
| `solver_advise_addons(policy?, problem?, runs?)` | loomground-solver | `skills/advise-solver-addons/scripts/advise.py` → `loomground_solver.addons.advise` | recommendations for `world_model` and `metacognition` with score, threshold, reasons, missing inputs; `activation_performed` always false |
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

The seven `solver_*` skill tools take the JSON their script reads on stdin as named arguments and return what it prints (`{method, result}`). `method` overrides the kernel method (any name in `loomground_solver.METHODS`); `extra` carries an overridden method's further keyword arguments (`{"alpha": 0.3}` for `hurwicz`). The scripts stay in the skills as the shell fallback; `tests/test_solver_parity.py` feeds both the same JSON and asserts the same output.

Enum arguments take the plane's own names (`PRESENT`, `decided`, `editorial`, …). Keys are passed in per call as PEM and never generated or stored. Canonicalisation uses `rfc8785` when installed, else sorted compact JSON; the envelope names which.

