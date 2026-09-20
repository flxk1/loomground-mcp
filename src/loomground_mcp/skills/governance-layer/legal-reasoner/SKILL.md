---
name: legal-reasoner
description: "Grounded premises to a warranted conclusion (apply, in-force, conflict, effect, deontic). Calls grounder first; enacts nothing alone. Use when grounded premises must be argued to a conclusion — 'what follows from these provisions', 'is this permitted / obligatory / forbidden', 'which norm wins', 'how likely is liability'."
metadata: { provenance: { stamp: "tool=governance-layer version=0.1.0 input_sha256=b2c6fe4f81ab7eca93d29cf183e7ac44203e848837874fda3033b8d6f997474d" } }
governance:
  grade: L2
  actions:
    - { kind: warrant_conclusion, risk: medium }
    - { kind: quantify_exposure, risk: medium }
    - { kind: emit_lg_patch, risk: high, grade: L3 }
    - { kind: release_disposition, risk: critical, grade: L4 }
  reserved:
    - { kind: release_disposition, by: { quorum: 2, of: [legal_reviewer, policy_owner] } }
  prohibited:
    - reason_over_unconfirmed
    - self_enact
    - parallel_grounding_layer
  obligations:
    - warrant_shown
    - premises_confirmed
    - grounding_called_first
    - egress_checked
    - egress_payload_moat_safe
    - completeness_asserted
  redress:
    - { kind: released_disposition, by: affected_party, overturn: true, within: 14d }
  budget: { usd: 5, iters: 40 }
  on-boundary: escalate-and-state-gap
---

# legal-reasoner

**Plane:** Loomground · reason

Grounded premises to a warranted conclusion (apply, in-force, conflict, effect, deontic). Calls grounder first; enacts nothing alone.

**Doors.** Host: a legal-reasoning / lens / policy / coverage-matrix interface. release_disposition routes to the host's signed decision gate (reserved).

## Governance identity
The `governance:` block above is the whole of this skill's authority. A skill is universal; the block turns it into a governed **role** that ctrl plans on and an **enforcement host enforces** (a signed verdict on the host's hash-chain -- auto / human / reserved / prohibited, joined strictest-wins), and the agent-registry records. Reserved acts hold for a human; prohibited kinds are severed regardless of grade.
