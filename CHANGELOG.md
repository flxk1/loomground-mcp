<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# Changelog

## Unreleased

* Skills over MCP: the family's 22 conformant SKILL.md files in public repositories as `skills/index.json` (repo, name, description, allowed_tools, commit, path, url), every body vendored at each repository's pushed main commit as package data; one MCP prompt per vendored body (`prompts/list` over stdio, SSE and streamable-HTTP; `prompts/get` = the body under `Skill <name> from <repo> @ <commit>; tools: …`; a shared name is qualified `<repo>/<name>`); 1 new tool `loomground_skill(name=None)`, plane `loomground` (the index, or one record with its body); parity test against every repository at its pin (CI fetches the public ones), catalogue–index consistency test; 40 tools.
* Tools: 1 new — `loomground_catalogue(query=None)`, plane `loomground`: the family map (`repos`, `pipeline`, `patch_from_documents`, `source`) from `CATALOGUE.json` vendored as `catalogue.json` (package data, byte-parity test against the loomground repository at 782e745); the server's instructions say to call it first; 39 tools.
* Tools: 4 new — the reader/writer languages: `factual_lower` (loomground-factual), `epistemic_extract` (loomground-epistemic), `norm_extract` (loomground-norm: rules lifted to deontic formulae), `topos_parse` (a statement-level reader for loomground-topos's `grammar/topos.ebnf`, implemented in `tools/topos.py`; every `.lt` block in the spec's examples parses); 38 tools.
* Tools: 13 new — deontic (`deontic_parse`, `deontic_conflicts`), versum write/curate (`versum_capture`, `versum_suggest`, `versum_confirm`, `versum_canon`), the seven loomground-solver skill scripts as tools (`solver_analyse_risks`, `solver_estimate_liability`, `solver_litigation_risk`, `solver_opponent_model`, `solver_probability`, `solver_strategy`, `solver_advise_addons`) with script-parity tests; 34 tools.

## 0.1.0

* Initial: one MCP server over the Loomground planes — versum (3 tools), solver (3), ingest (1), the six operators (6), the assurance artifacts (8); stdio, SSE and streamable-HTTP transports; structured fail-closed envelopes.
