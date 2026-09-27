---
name: legal-reasoner
description: "Grounded premises to a warranted conclusion (apply, in-force, conflict, effect, deontic). Calls grounder first; enacts nothing alone. Use when grounded premises must be argued to a conclusion — 'what follows from these provisions', 'is this permitted / obligatory / forbidden', 'which norm wins', 'how likely is liability'."
allowed-tools: deontic_parse, deontic_conflicts, solver_evaluate, solver_analyse_risks, solver_estimate_liability, solver_litigation_risk, solver_opponent_model, solver_probability, solver_strategy, solver_advise_addons
metadata: { provenance: { stamp: "tool=governance-layer version=0.1.0 input_sha256=9cdae110b146c11fb8fde3f6870a51137aceb9e544ca1fb289e63b012cb6c3eb" } }
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

**Public skill.** loomground-deontic:deontic; the loomground-solver:* analysis skills (analyse-risks, estimate-liability, litigation-risk-assessor, opponent-modeler, probability-tracker, strategic-analysis, advise-solver-addons). `allowed-tools` above is this role's whole tool grant, from one source (`ROLES` in `build_role_skills.py`); no other tool is served.

## Governance identity
The `governance:` block above is the whole of this skill's authority. This layer compiles it, registers it and binds it to host doors, which makes the skill a governed **role** that ctrl plans on and an **enforcement host enforces** (a signed verdict on the host's hash-chain -- auto / human / reserved / prohibited, joined strictest-wins), and the agent-registry records. Reserved acts hold for a human; prohibited kinds are severed regardless of grade.
