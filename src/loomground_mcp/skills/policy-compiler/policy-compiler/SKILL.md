---
name: policy-compiler
description: >-
  Read a written policy and produce executable governance norms. Use when the
  user asks to turn a policy into rules, compile a contract's obligations, find
  the conflicts in a policy, or ask what a policy requires or forbids.
allowed-tools: policy_compile policy_check
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

Primary path: call `policy_compile` with the policy text. Call `policy_check`
with the same text and explicit `{actor, action, expect}` cases when the user
asks whether the draft satisfies examples. Both calls stop at a validated draft;
neither activates it.

The same operations are implemented in the `policy_compiler` package:
`compile(policy) -> CompiledPolicy`
(norms, conflicts, undetermined, residuals, per-norm provenance) and
`check(policy, cases)`, plus the `policy-compiler` CLI. Lowering delegates to the
loomground `deontic` and `norm` planes when present, with `ingest` corroboration
and `governance` validation; see the README. `to_grounding_seam()` emits the
shape the compliance-fleet consumes, so a compiled policy is the norm base the
fleet steers against.
