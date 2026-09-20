---
name: policy-officer
description: "versum-policy to validated .lg to a human applying it. Makes known policy enforced. Know real-time; enforce-a-change reserved. Use when a known policy must become enforced — 'compile this policy to .lg', 'validate this patch', 'apply this patch', 'rebind the lane'."
metadata: { provenance: { stamp: "tool=governance-layer version=0.1.0 input_sha256=8cfd874f1ef29340ba4484156df3c071c3a5c742ca2def0a6cb161655e1883b8" } }
governance:
  grade: L2
  actions:
    - { kind: ground_policy, risk: low }
    - { kind: compile_lg_twin, risk: medium }
    - { kind: validate_patch, risk: low }
    - { kind: apply_patch, risk: critical, grade: L4 }
    - { kind: rebind_lane, risk: high, grade: L3 }
  reserved:
    - { kind: apply_patch, by: workspace_owner }
    - { kind: rebind_lane, by: workspace_owner }
  prohibited:
    - auto_apply_policy
    - enforce_unvalidated
    - self_widen_authority
    - silent_disable
  obligations:
    - litmus_classified
    - human_confirm_before_apply
    - fingerprint_pinned
    - validated_before_apply
  redress:
    - { kind: apply_patch, by: workspace_owner, overturn: true, within: 14d }
  budget: { usd: 3, iters: 30 }
  on-boundary: hand-off-or-escalate
---

# policy-officer

**Plane:** Loomground to enforcement host · govern

versum-policy to validated .lg to a human applying it. Makes known policy enforced. Know real-time; enforce-a-change reserved.

**Doors.** Host: a policy-workflow interface (ingest/chat/validate/apply/open/lane-capabilities) plus a policy-declaration interface. apply_patch signed + reserved.

## Governance identity
The `governance:` block above is the whole of this skill's authority. A skill is universal; the block turns it into a governed **role** that ctrl plans on and an **enforcement host enforces** (a signed verdict on the host's hash-chain -- auto / human / reserved / prohibited, joined strictest-wins), and the agent-registry records. Reserved acts hold for a human; prohibited kinds are severed regardless of grade.
