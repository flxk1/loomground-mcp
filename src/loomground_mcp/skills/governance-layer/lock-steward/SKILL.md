---
name: lock-steward
description: "Provisions and discharges the per-folder egress lock (Privacy Lock). Manages the lock, never exempt. Ratchet + fail-secure. Use when a folder's egress lock must be provisioned, checked, raised, lowered, or unsealed — 'lock this folder', 'lock status', 'egress-check this payload', 'unseal'."
metadata: { provenance: { stamp: "tool=governance-layer version=0.1.0 input_sha256=a1a3818d80cf91346244edd953772c16f4f08ea547af05ee8d01653566f427ba" } }
governance:
  grade: L2
  actions:
    - { kind: lock_status, risk: low }
    - { kind: classify_content, risk: low }
    - { kind: propose_lock_profile, risk: medium }
    - { kind: egress_check, risk: medium }
    - { kind: ingress_check, risk: medium }
    - { kind: provision_lock, risk: high, grade: L3 }
    - { kind: raise_threshold, risk: high, grade: L3 }
    - { kind: lower_threshold, risk: critical, grade: L4 }
    - { kind: downgrade_backend, risk: critical, grade: L4 }
    - { kind: unseal, risk: critical, grade: L4 }
  reserved:
    - { kind: provision_lock, by: workspace_owner }
    - { kind: lower_threshold, by: { all: [workspace_owner, data_protection_officer] } }
    - { kind: downgrade_backend, by: { all: [workspace_owner, data_protection_officer] } }
    - { kind: unseal, by: workspace_owner }
  prohibited:
    - silent_mock_backend
    - weaken_without_distinct_party
    - assume_protected_on_unknown
    - egress_on_lock_unavailable
    - passphrase_in_context
  obligations:
    - secure_default_backend
    - no_silent_weakening
    - human_confirm_before_mutate
    - every_change_chained
    - provision_is_not_access
    - egress_check_not_self_waivable
  redress:
    - { kind: lower_threshold, by: workspace_owner, overturn: true }
    - { kind: provision_lock, by: workspace_owner, overturn: true, within: 30d }
  budget: { usd: 2, iters: 25 }
  on-boundary: hold-and-explain
---

# lock-steward

**Plane:** secure (host-enforced)

Provisions and discharges the per-folder egress lock (Privacy Lock). Manages the lock, never exempt. Ratchet + fail-secure.

**Doors.** Host: an egress-lock interface (setup/threshold/seal/classify/egress_check/ingress_check/audit_query). Mutations signed + reserved; bundled door HOLDs.

## Governance identity
The `governance:` block above is the whole of this skill's authority. A skill is universal; the block turns it into a governed **role** that ctrl plans on and an **enforcement host enforces** (a signed verdict on the host's hash-chain -- auto / human / reserved / prohibited, joined strictest-wins), and the agent-registry records. Reserved acts hold for a human; prohibited kinds are severed regardless of grade.
