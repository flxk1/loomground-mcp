---
name: local-grounder
description: "Grounds Felix's own work over his private knowledge folder. Firewalled from the product: never ships, never a product dependency, output never reaches the official versum. Use when Felix's own work must be grounded over his private knowledge folder — 'ground this against my private notes', 'read my private evidence'."
allowed-tools: versum_search, versum_claims
metadata: { provenance: { stamp: "tool=governance-layer version=0.1.0 input_sha256=d2965b25a2f3aca8811c3e0211c5213a0f981b75c8485497f9ea7651a303ad0a" } }
governance:
  grade: L2
  actions:
    - { kind: ground_private, risk: low }
    - { kind: read_private_evidence, risk: low }
  reserved: []
  prohibited:
    - feed_product_grounding
    - write_to_official_versum
    - egress_private_content
    - ship
  obligations:
    - local_only
    - private_stays_private
    - firewalled_from_product
    - separate_store
  redress:
    - { kind: private_grounding, by: felix, overturn: true }
  budget: { usd: 1, iters: 20 }
  on-boundary: hold-local
---

# local-grounder

**Plane:** Loomground · ground (private) — LOCAL-ONLY

Grounds Felix's own work over his private knowledge folder. Firewalled from the product: never ships, never a product dependency, output never reaches the official versum.

**Doors.** No MCP / no signing / no product seam. A local reader over the private folder (Obsidian / local versum / local RAG).

**Public skill.** loomground-versum:loomground-kg-chat, pointed at the private folder — never the official versum. `allowed-tools` above is this role's whole tool grant, from one source (`ROLES` in `build_role_skills.py`); no other tool is served.

## Governance identity
The `governance:` block above is the whole of this skill's authority. This layer compiles it, registers it and binds it to host doors, which makes the skill a governed **role** that ctrl plans on and an **enforcement host enforces** (a signed verdict on the host's hash-chain -- auto / human / reserved / prohibited, joined strictest-wins), and the agent-registry records. Reserved acts hold for a human; prohibited kinds are severed regardless of grade.
