---
name: policy-compiler
description: >-
  Read a written policy and compile it to grounded deontic norms — obligations,
  permissions, and prohibitions (O/P/F) with bearer, action, conditions, and
  cross-references — surfacing conflicts, undetermined rules, and the spans it
  could not place (residuals), and running test cases against the result. It
  stops at a validated draft: activation is a reserved human step, never
  automatic. When the loomground deontic/norm planes are present the lowering is
  grounded via them; absent, it degrades to an advisory extraction marked
  ungrounded. Its output matches the compliance-fleet grounding seam, so the
  compiled norms are the policy the fleet steers against. Triggers on "turn this
  policy into rules", "compile this contract's obligations", "find the conflicts
  in this policy", "what does this policy require or forbid", "make a checkable
  policy".
governance:
  grade: L1
  actions:
    - { kind: compile, risk: low }
    - { kind: check, risk: low }
  reserved:
    - { kind: activate_a_compiled_policy, by: workspace_owner }
  prohibited:
    - auto_activate_or_apply_a_policy
    - fabricate_a_norm_with_no_source_span
    - require_loomground_on_default_path
  obligations:
    - stop_at_a_validated_draft
    - surface_conflicts_and_undetermined_rules
    - residuals_surfaced_never_invented
    - grounded_when_the_plane_is_present_else_advisory
  redress:
    - { kind: recorded_override, by: workspace_owner, overturn: true }
  budget: { usd: 1, iters: 20 }
  on-boundary: report-not-repair
---

# policy-compiler

Implemented in the `policy_compiler` package: `compile(policy) -> CompiledPolicy`
(norms, conflicts, undetermined, residuals, per-norm provenance) and
`check(policy, cases)`, plus the `policy-compiler` CLI. Lowering delegates to the
loomground `deontic` and `norm` planes when present, with `ingest` corroboration
and `governance` validation; see the README. `to_grounding_seam()` emits the
shape the compliance-fleet consumes, so a compiled policy is the norm base the
fleet steers against.
