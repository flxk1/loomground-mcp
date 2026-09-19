---
name: grounder
description: "Read-only evidence at coordinate + provenance, or ground-or-escalate. Serves; never writes. Product grounder — official versum only. Use when a claim must be grounded against the official versum — 'ground this', 'is this in the corpus', 'give me the source for X at date D', 'confirm this against the graph'."
metadata: { provenance: { stamp: "tool=governance-layer version=0.1.0 input_sha256=f0643419d59d79f7fcebd32e47f25b4648a1b6ecad120a15c0d45102f466ca7c" } }
governance:
  grade: L2
  actions:
    - { kind: ground_query, risk: low }
    - { kind: read_evidence, risk: low }
    - { kind: emit_provenance_receipt, risk: medium, grade: L3 }
  reserved: []
  prohibited:
    - graph_write
    - binary_fetch
    - fabricate_citation
    - answer_from_model_memory
    - ground_from_private_folder
  obligations:
    - provenance_attached
    - coordinate_pinned
    - egress_checked
    - egress_payload_moat_safe
    - ingress_checked
    - official_versum_only
    - completeness_asserted
  redress:
    - { kind: disputed_grounding, by: reviewer, overturn: true }
  budget: { usd: 1, iters: 20 }
  on-boundary: escalate-with-named-axis
---

# grounder

**Plane:** Loomground · ground (product)

Read-only evidence at coordinate + provenance, or ground-or-escalate. Serves; never writes. Product grounder — official versum only.

**Doors.** Host: a read-only grounding-evidence interface (provenance, ask, cross-workspace read). Bundled: portable read + ground-or-escalate; signs nothing.

## Governance identity
The `governance:` block above is the whole of this skill's authority. A skill is universal; the block turns it into a governed **role** that ctrl plans on and an **enforcement host enforces** (a signed verdict on the host's hash-chain -- auto / human / reserved / prohibited, joined strictest-wins), and the agent-registry records. Reserved acts hold for a human; prohibited kinds are severed regardless of grade.
