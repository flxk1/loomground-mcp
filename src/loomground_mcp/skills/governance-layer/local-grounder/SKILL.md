---
name: local-grounder
description: "Grounds Felix's own work over his private knowledge folder. Firewalled from the product: never ships, never a product dependency, output never reaches the official versum. Use when Felix's own work must be grounded over his private knowledge folder — 'ground this against my private notes', 'read my private evidence'."
metadata: { provenance: { stamp: "tool=governance-layer version=0.1.0 input_sha256=c0360c354fff19b2491a49835ffc6d38420c39c0d6bd676369c38381fd526a47" } }
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

## Governance identity
The `governance:` block above is the whole of this skill's authority. A skill is universal; the block turns it into a governed **role** that ctrl plans on and an **enforcement host enforces** (a signed verdict on the host's hash-chain -- auto / human / reserved / prohibited, joined strictest-wins), and the agent-registry records. Reserved acts hold for a human; prohibited kinds are severed regardless of grade.
