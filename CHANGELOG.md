<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# Changelog

## Unreleased

* Tools: 1 new — `loomground_catalogue(query=None)`, plane `loomground`: the family map (`repos`, `pipeline`, `patch_from_documents`, `source`) from `CATALOGUE.json` vendored as `catalogue.json` (package data, byte-parity test against the loomground repository at fbf4f46); the server's instructions say to call it first; 39 tools.
* Tools: 4 new — the reader/writer languages: `factual_lower` (loomground-factual), `epistemic_extract` (loomground-epistemic), `norm_extract` (loomground-norm: rules lifted to deontic formulae), `topos_parse` (a statement-level reader for loomground-topos's `grammar/topos.ebnf`, implemented in `tools/topos.py`; every `.lt` block in the spec's examples parses); 38 tools.
* Tools: 13 new — deontic (`deontic_parse`, `deontic_conflicts`), versum write/curate (`versum_capture`, `versum_suggest`, `versum_confirm`, `versum_canon`), the seven loomground-solver skill scripts as tools (`solver_analyse_risks`, `solver_estimate_liability`, `solver_litigation_risk`, `solver_opponent_model`, `solver_probability`, `solver_strategy`, `solver_advise_addons`) with script-parity tests; 34 tools.

## 0.1.0

* Initial: one MCP server over the Loomground planes — versum (3 tools), solver (3), ingest (1), the six operators (6), the assurance artifacts (8); stdio, SSE and streamable-HTTP transports; structured fail-closed envelopes.
