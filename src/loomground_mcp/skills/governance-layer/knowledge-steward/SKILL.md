---
name: knowledge-steward
description: "Build and maintain the graph: ingest, concepts, placement, write, curate; enrich; erase. The one write/erase authority. Use when material must enter, be curated in, or be erased from the graph — 'ingest this', 'add what we learned to the graph', 'curate the concepts', 'erase this subject'."
metadata: { provenance: { stamp: "tool=governance-layer version=0.1.0 input_sha256=4d337b7bb3cd4ca89127cfa401fec9873132209bd9a01a81ee83a1370a218b83" } }
governance:
  grade: L2
  actions:
    - { kind: ingest_dryrun, risk: low }
    - { kind: extract_concepts, risk: low }
    - { kind: propose_placement, risk: medium }
    - { kind: graph_write, risk: high, grade: L3 }
    - { kind: curate_canon, risk: high, grade: L3 }
    - { kind: graph_erase, risk: critical, grade: L4 }
  reserved:
    - { kind: graph_erase, by: { all: [data_protection_officer, workspace_owner] } }
    - { kind: curate_canon, by: curator }
  prohibited:
    - direct_write_bypassing_path
    - binary_fetch_in_session
    - invent_node
    - unlogged_mutation
  obligations:
    - single_write_path
    - dry_run_then_confirm
    - dedup_urn_sidecar
    - legal_basis_recorded
    - egress_checked
    - erase_egress_limit_disclosed
  redress:
    - { kind: graph_erase, by: subject, overturn: false, within: 30d }
    - { kind: graph_write, by: workspace_owner, overturn: true }
  budget: { usd: 5, iters: 40 }
  on-boundary: quarantine-or-review-queue
---

# knowledge-steward

**Plane:** Loomground · curate

Build and maintain the graph: ingest, concepts, placement, write, curate; enrich; erase. The one write/erase authority.

**Doors.** Host: ingest / capture / memory / folder / mirror / erase interfaces. Writes append to the host's signed mutation chain (reserved).

## Governance identity
The `governance:` block above is the whole of this skill's authority. A skill is universal; the block turns it into a governed **role** that ctrl plans on and an **enforcement host enforces** (a signed verdict on the host's hash-chain -- auto / human / reserved / prohibited, joined strictest-wins), and the agent-registry records. Reserved acts hold for a human; prohibited kinds are severed regardless of grade.
