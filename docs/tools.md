<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# Tools

Every result is one envelope in `structuredContent` (and as JSON text):
`{plane, function, ok: true, result}` · `{plane, function, ok: false, error: {type, message}}` · `{plane, function, ok: false, unavailable: true, reason}`. The last two carry `isError`.


| Tool | Plane | Function | In → out |
|---|---|---|---|
| `loomground_catalogue(query?)` | loomground | `CATALOGUE.json` (vendored `catalogue.json`) | `repos[]` (`repo`, `family`, `role`, `description`, `pipeline_position`, `depends_on`, `tools`, `skills`, `install`, `url`), `pipeline[]` (`step`, `stage`, `repo`, `tool`, `in`, `out`), `patch_from_documents[]`, `source` (`repo`, `commit`); `query` = case-insensitive substring over repo/family/role/tools/skills, filters `repos` only |
| `loomground_skill(name?)` | loomground | `skills/index.json` (vendored `skills/<repo>/<name>/SKILL.md`) | without `name`: the index — one record per SKILL.md (`repo`, `name`, `description`, `allowed_tools`, `commit`, `path`, `url`, `prompt`); with `name` (or `<repo>/<name>` when the name is shared): the record + `body`, the SKILL.md with its frontmatter stripped; unknown or ambiguous → `unavailable` |
| `versum_index(folder, profile="generic")` | loomground-versum | `versum.store.index.index_folder` | folder → index summary; writes `<folder>/.versum` |
| `versum_claims(folder, limit=100)` | loomground-versum | `<folder>/.versum/claims.csv` | rows with `source_urn`, `span_start`, `span_end`, `marker`, `text`, projections |
| `versum_search(folder, query, k=10, filters?)` | loomground-versum | `versum.store.retrieve.SearchIndex` / `from_kg` | hits with spans; hybrid over a materialised KG (`by-domain/`), BM25 over a plain index; `unavailable` when there is nothing to search |
| `versum_capture(folder, source_path, profile="generic")` | loomground-versum | `versum.write.capture_file` | one `.txt`/`.md`/`.pdf` → `admitted` or `duplicate`, `urn`, `claim_count`, `index`; an unsupported source is a `CaptureError` |
| `versum_suggest(folder, min_sources=1)` | loomground-versum | `versum.concept.curate.suggest_folder` | curation-queue counts + `candidates` (`concept_id`, `label`, `n_claims`, `n_sources`, `seed`, `example`) with at least `min_sources` sources; writes `.versum/curation/`, never the graph; `unavailable` before indexing |
| `versum_confirm(folder, concept_ids?, min_sources=1)` | loomground-versum | `versum.concept.curate.confirm_folder` | promotes the explicit pick, else every candidate with at least `min_sources` sources, into `.versum/concepts.csv` + `semantic_edges.csv`; `unavailable` without a queue |
| `versum_canon(folder, config?, m_max=1)` | loomground-versum | `versum.concept.canon.curate_kg` / `curate_domain_folder` | coordinate-identity canon; `layout` = `kg` (a sync `config` or a `by-domain/` root → `canon.json` + `convergence.json`), `domain` (one by-domain folder) or `index` (a plain `.versum`, its concept tables overwritten) |
| `deontic_parse(statement)` | loomground-deontic | `deontic.grammar.parse` | `[if [c] then] O|P|F(bearer : action) [unless [e]]` → formula fields, `formula` (canonical render), `round_trip`, `validation`; not a statement → `DeonticSyntaxError` |
| `deontic_conflicts(statements)` | loomground-deontic | `deontic.contract.conflict_candidates` | parsed formulae + candidate `may-conflict-with` edges (same bearer and action, incompatible modality); flagged, never resolved |
| `factual_lower(sentence)` | loomground-factual | `loomground_factual.lower` | one assertion → `subject`, `predicate`, `object`, `dimension` (`structural` for is-a/part-of, else `relational`), `negated`, `quantification` (`universal`/`existential`/`empty`); no copula → `unavailable` |
| `epistemic_extract(sentence)` | loomground-epistemic | `loomground_epistemic.extract` | one sentence → `operator` (`K`/`B`), `holder`, `proposition`, `certainty` (`certain` > `reasonable-grounds` > `probable` > `possible` > `estimate`), `source`; no epistemic cue → `unavailable` |
| `norm_extract(text, language="en")` | loomground-norm | `rule_extractor.extract_rules` + `deontic_lift.formula_from_rule` | text → `rules[]` of `{rule: RuleFacet fields, formula: canonical render, formula_fields}`, `n_rules`, `languages_detected`; the extractor detects each sentence's language, `language` is checked against the 24 codes and echoed; no rule → `n_rules` 0 |
| `topos_parse(text)` | loomground-topos | `loomground_mcp.tools.topos.parse` (reader for `grammar/topos.ebnf` v0.1) | `.lt` text → `statements[]` (`system`/`organ`/`level`/`instrument`/`competence` records, `rel` and `assert` edges with `from`, `type`, `to`, `vocabulary`, `props`, `asserted_by`, `polarity`), `errors[]` with `line`, `reason`, `statement`, `warnings[]`, `valid`, `counts` |
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

`loomground_catalogue` is the family map, to be called first: every repository as one record, the pipeline order `source → ingest → versum → solver → applied | diagnostic` with the tool at each step, and `patch_from_documents` (ingest_text → versum_index → norm_extract / deontic_parse → author the `.lg` patch → solver_evaluate). It reads `catalogue.json`, vendored from `CATALOGUE.json` in the loomground repository at the commit the envelope's `source` names; `tests/test_catalogue_parity.py` asserts byte-equality against a checkout of that commit. `query` never touches `pipeline` or `patch_from_documents`.

`loomground_skill` and the prompts carry the family's Agent Skills. `skills/index.json` has one record per conformant SKILL.md (`skills/<name>/SKILL.md` in each repository, Agent Skills frontmatter with `name`, `description`, `allowed-tools`) at the repository's pushed main commit; public repositories only; the body is vendored beside it. Every vendored body is one MCP prompt with no arguments: `prompts/list` names it after the skill (`<repo>/<name>` when two repositories hold the same name), `prompts/get` returns one user message — the body with the frontmatter stripped, under the line `Skill <name> from <repo> @ <commit>; tools: <allowed-tools>`. `tests/test_skills_parity.py` checks every record against `git show <commit>:<path>` in a reachable checkout (siblings, or `LOOMGROUND_SKILLS_ROOT`; CI fetches each public repository at its pin); `tests/test_skills.py` checks the catalogue's `skills[]` against the index per repository.

`topos_parse` is the one tool whose function lives in this repository: the loomground-topos spec ships the grammar (`grammar/topos.ebnf`, normative) and no package, so the reader is implemented here. It parses only — any id parses; ladder/catalogue membership and the well-formedness invariants are apply-time. An indented line continues the statement above it; a prop block on a node declaration is kept with a warning; an off-vocabulary `resolution_mode`/`state`/`status` value is a warning, not an error. Every rejected statement is one error with its line.

The seven `solver_*` skill tools take the JSON their script reads on stdin as named arguments and return what it prints (`{method, result}`). `method` overrides the kernel method (any name in `loomground_solver.METHODS`); `extra` carries an overridden method's further keyword arguments (`{"alpha": 0.3}` for `hurwicz`). The scripts stay in the skills as the shell fallback; `tests/test_solver_parity.py` feeds both the same JSON and asserts the same output.

Enum arguments take the plane's own names (`PRESENT`, `decided`, `editorial`, …). Keys are passed in per call as PEM and never generated or stored. Canonicalisation uses `rfc8785` when installed, else sorted compact JSON; the envelope names which.

