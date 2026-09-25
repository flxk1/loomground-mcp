---
name: auditor
description: "Read-only over the signed chain (verify_chain/tail/shadow_scan/discipline). Writes nothing but an attributed override. Reports, never repairs. Use when the signed chain must be verified or reported on — 'verify the chain', 'tail the chain', 'shadow scan', 'discipline check', 'record an override'."
metadata: { provenance: { stamp: "tool=governance-layer version=0.1.0 input_sha256=af3a23ab07bc7db6100039b975b9a9ab081f2c696451f9a8c759f425144c21b5" } }
governance:
  grade: L2
  actions:
    - { kind: verify_chain, risk: low }
    - { kind: tail_chain, risk: low }
    - { kind: get_event, risk: low }
    - { kind: shadow_scan, risk: low }
    - { kind: discipline, risk: low }
    - { kind: record_override, risk: medium }
  reserved: []
  prohibited:
    - mutate_graph
    - mutate_policy
    - sign_content
    - repair_in_place
  obligations:
    - read_only_default
    - chain_verified_before_report
    - rationale_on_override
    - findings_not_masked
  redress:
    - { kind: recorded_override, by: workspace_owner, overturn: true }
  budget: { usd: 1, iters: 30 }
  on-boundary: report-not-repair
---

# auditor

**Plane:** audit (host-enforced)

Read-only over the signed chain (verify_chain/tail/shadow_scan/discipline). Writes nothing but an attributed override. Reports, never repairs.

**Doors.** Host: a read-only audit interface (verify/tail/get-event/shadow-scan/discipline/overrides/record-override). record_override is the only append.

## Governance identity
The `governance:` block above is the whole of this skill's authority. A skill is universal; the block turns it into a governed **role** that ctrl plans on and an **enforcement host enforces** (a signed verdict on the host's hash-chain -- auto / human / reserved / prohibited, joined strictest-wins), and the agent-registry records. Reserved acts hold for a human; prohibited kinds are severed regardless of grade.
