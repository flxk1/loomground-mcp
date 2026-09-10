---
name: loomground
description: Express an AI-governance requirement as a validated Loomground policy-graph patch. Use when the user wants to encode a governance rule (human oversight, reservation, prohibition, separation of duty / quorum, redress or contestation, delegation and the principal chain, autonomy grades, disclosure obligation) as a .lg patch; validate or fix an existing patch; or judge whether a requirement is expressible in Loomground versus belonging to policy or a host. Triggers on "express this as Loomground", "write a .lg patch", "is this governable in Loomground", "validate this patch", "governance as a policy graph".
---

# Loomground skill — draft, classify, validate

Turn a natural-language AI-governance requirement into a **verified** Loomground
policy-graph patch. Loomground *declares* governance; it never computes,
aggregates, schedules, persists, or communicates. Express what is declarable,
**hand the rest to a host**, then prove the patch is well-formed.

Everything factual below is generated from the language's canonical sources
(`vocabulary/`, `schema/`, `language-card.json`, `conformance/manifest.json`,
`examples/`) by `skills/loomground/make_skill.py` and CI-checked — this skill cannot drift
from the language. The normative source is `spec/SPEC.md`; it governs on any
conflict.

## The language

<!-- generated:language:begin -->
- **Nodes (4):** `actor` (principal that may be granted authority and propose an action) · `human` (person named by a role; a reserved token is referred to it, or it roots a principal chain as delegator) · `gate` (governed checkpoint where an actor acts and a verdict is produced) · `master` (single sink; the release point at which the policy enforcement point attaches)
- **Cords (3):** `authority` (actor → gate) · `pipe` (gate → gate) · `egress` (gate → master)
- **Token:** `{id, kind, risk, party, provenance, reversibility, uncertainty, tags}`; `risk` ∈ low < medium < high < critical; `tags` is an optional set of declared categories.
- **Verdicts (join strictest-wins along pipes):** `auto` ⊑ `human` ⊑ `refused` ⊑ `reserved` ⊑ `prohibited`. The master releases iff the effective verdict is `auto` and every egress obligation is attached.
- **Autonomy grades:** active ladder `L0 < L1 < L2 < L3 < L4 < L5 < L6` (policy, remappable); granted on an actor, required on a source gate; an ungated gate dispositions `auto` — declare a required grade to withhold.
- **Guards** range over exactly `{kind, risk, reversibility, uncertainty, party, tags}` — never `id`, `provenance`, `grade`, or any computed value.
<!-- generated:language:end -->

## The declarations

<!-- generated:declarations:begin -->
| Declaration | Form | Effect |
| --- | --- | --- |
| reservation | `reserve <kind> by <target> [when <guard>] [duration <d>:<on-elapse>]` | verdict reserved; the action is referred to a human role |
| quorum | `target = role | role and role | <m> of { roles }` | requires distinct parties (separation of duty) |
| prohibition | `prohibit <kind> [when <guard>]` | verdict prohibited; never released and never discharged; overrides any grant |
| temporal | `duration <d>:<halt|proceed> on a reserved action` | declares a deadline/window/expiry/cooling-off and its on-elapse resolution |
| egress-obligation | `obligation <id> on <gate>` | the master acts only if the obligation is attached |
| redress | `redress <kind> by <role> [overturn] [within <duration>]` | a released decision of <kind> is contestable: a fresh re-examination by <role> is owed and recorded; 'overturn' qualifies that role as empowered to reverse the outcome; 'within' declares the appeal/recall window. The re-examination is a separate (forward) activation and the reversal/recall is outside this specification; the language declares and records the right. |
| party | `party <id> on an actor or gate` | sets the party currently responsible |
| delegation | `on-behalf-of <actor|human> on an authority cord` | delegate acts for delegator; the bindings form the acyclic principal chain, projected in the observation; actor-to-actor links are bound by the no-amplification invariant; a human delegator anchors answerability and confers no authority; a partyless delegate bears its delegator's party |
| mandate | `mandate <purpose> | mandate { <purpose>, ... } on an actor` | the set of declared purposes an actor is authorised to pursue; configuration on an actor like grade, never a token field and never guardable. A delegate's mandate MUST be a subset of its delegator's and a delegator declaring none caps its delegate at none, so delegation narrows purpose and never widens it; attenuation composes pairwise along the acyclic principal chain. A mandate neither confers nor withholds authority — a grant says what, a mandate says what for — and the language judges no conduct against it |
| transfer | `consign <id> on a terminal gate; transfer <kind> to <consignee> within { <purpose>, ... }` | names the party a released action's material goes to, and the purposes it is limited to there. The consignee is a declared id, not a node - the four node classes are unchanged and a consignee is never a cord endpoint. A gate declaring a consignee MUST be terminal. The transfer's purposes MUST be a subset of the mandate of every actor granted over that kind at a consigning gate; an unmandated actor holds the empty set and can license nothing onward, so an actor cannot hand on a purpose it was not itself given. Lateral, not a delegation: the consignee acts on nobody's behalf and no principal chain is formed. The language records the purposes and bounds them; whether the consignee honours them is conduct and outside the specification |
| autonomy-grade | `grade <level> on an actor (granted) or source gate (required)` | gates the step-(4) auto/human disposition at a source gate; grade is configuration, not a token field or guard domain |
<!-- generated:declarations:end -->

## Well-formed iff

<!-- generated:wellformed:begin -->
- every cord is a permitted endpoint pairing
- the pipe relation is acyclic
- exactly one master
- every gate lies on a path to the master
- every actor-to-actor delegation link satisfies the no-amplification invariant (risk subset — an ungranted delegator has the empty set, so a delegate is never granted where its delegator is not — and, pairwise, grade(delegate) not above grade(delegator) in the active-ladder order; additionally an ungraded delegator caps the delegate at ungraded); a human delegator anchors answerability and constrains no grant
- every actor-to-actor delegation binding satisfies the mandate-attenuation invariant (the delegate's mandate is a subset of its delegator's; a delegator declaring no mandate caps its delegate at none, so delegation narrows purpose and never widens it); an actor declares at most one mandate
- a gate declaring a consignee is terminal; every transfer names a declared consignee with a non-empty purpose set; and a transfer's purposes are a subset of the mandate of every actor granted over that kind at a consigning gate (an unmandated actor licenses nothing onward)
- a gate declaring a required grade is a source gate; grade_required on a non-source (piped) gate is ill-formed at apply
- the on-behalf-of relation names only declared nodes (actor or human) and is acyclic — the principal chain; it projects in the observation, and a partyless delegate bears its delegator's party
<!-- generated:wellformed:end -->

## Procedure

### Step 1 — split the requirement into atoms

One atom = one governance condition (one "who may / must not / must be
overseen doing what"). Never draft from an unsplit paragraph.

### Step 2 — the litmus, per atom

<!-- generated:litmus:begin -->
A regulation names it as a declaration -> language. A deployment chooses its values -> policy. A runtime does it -> host. A guard ranges only over declared token properties, never a computed value, and never over grade (a config attribute: granted on actor, required on a source gate). The autonomy ladder and its order are policy (vocabulary/grades.json, default L0..L6, remappable); the language requires an active total order and owns the §7.1 comparison/gating rule evaluated at the source gate, including the auto disposition of a gate that declares no required grade.
<!-- generated:litmus:end -->

<!-- generated:outofscope:begin -->
Outside the language (hand off to a host, never force into a guard): execution, scheduling, storage, presentation, communication, time measurement, obligation discharge, party authentication.
<!-- generated:outofscope:end -->

Classify each atom as **language** (express it below), **policy** (record the
chosen values in the report, not in language semantics), or **host** (hand
off explicitly — name what the host must do, e.g. measure a duration,
authenticate a party, discharge an obligation, meter a budget).

### Step 3 — draft the graph, then the declarations

Declare nodes first (`actor`, `human`, `gate`; `master` is never declared),
then cords/grants, then declarations. One statement per line; `#` comments.
Wire every gate onto a `pipe ∪ egress` path to `master`. Per-declaration
guidance:

### reservation

Use when a human must decide or approve. `reserve <kind> by <role>`; narrow
with `when <guard>` (e.g. `risk >= high`) so routine cases stay `auto`. Which
kinds are reserved is policy — record the choice in the report.

### quorum

Separation of duty: `by role and role` (dual control) or `by <m> of {roles}`.
Distinctness is observed over the parties in the token's `provenance` and is
unauthenticated — always hand the party-to-identity binding to the host.

### prohibition

Red lines: `prohibit <kind> [when <guard>]`. It overrides every grant and
never releases. A guard narrows what is prohibited; silence on the rest is
not permission. Where the basis is law, note that the prohibition arises by
law and the patch only mirrors it.

### temporal

Deadlines, windows, cooling-off on a *reserved* action:
`duration <n><m|h|d>:<halt|proceed>`. `halt` is the safe default; treat
`proceed` (fail-open on elapse) as a red flag to surface, and hand the
measurement of time to the host.

### egress-obligation

Disclosure duties attached at release: `obligation <id> on <gate>`. The gate
must be declared. Attachment is in-language; discharge is the host's — say so
in the hand-off.

### redress

Contestability of a *released* decision: `redress <kind> by <role>
[overturn] [within <duration>]`. `overturn` empowers reversal, not mere
review. The re-examination is a fresh activation; the language records the
right, the host runs it.

### party

Accountability attribute on an actor or gate: `party <id>`. A partyless
delegate bears its delegator's party, resolved along the principal chain,
nearest declared party wins. The party-to-legal-entity binding is the host's.

### delegation

`actor <delegate> on-behalf-of <delegator>` — the principal chain. The
delegator is a declared actor **or human**; the chain is acyclic, at most one
delegator per actor. Actor→actor links never amplify (risk subset, grade cap;
a delegate is never granted where its delegator is not); a human root anchors
answerability and confers no authority. Prefer rooting chains in a person
when the requirement is about accountability.

### mandate

`actor <id> mandate <purpose>` or `mandate { <purpose>, … }` — the set of
purposes the actor is authorised to pursue. Configuration on the actor, like
`grade`; never a token field, never guardable. One mandate per actor. Across a
delegation binding the delegate's mandate MUST be a subset of its delegator's;
a delegator with no mandate caps its delegate at none. Delegation narrows
purpose and never widens it. Whether conduct served the mandate is not a
graph property (loomground-mandate answers that after the fact).

### transfer

`gate <id> … consign <consignee>` marks a terminal gate whose release goes to
a declared consignee; `transfer <kind> to <consignee> within { <purpose>, … }`
limits material of that kind, at that consignee, to those purposes. Every
transfer names a declared consignee and a non-empty purpose set; the purposes
MUST be a subset of the mandate of every actor granted over that kind at a
consigning gate. What the consignee then does is outside the language.

### autonomy-grade

`grade <level>` — granted on an actor, required on a source gate. At a gate
requiring `R`: `auto` iff granted `G >= R`, else `human`; an ungraded actor
is withheld (fail-closed); an ungated gate is `auto` — **declare a required
grade to withhold**. The ladder itself is policy.

### Step 4 — worked examples (conformance-tested)

<!-- generated:example:begin -->
A routine drafting gate and a reserving decide gate (`examples/draft-decide.lg`):

```
# draft-decide.lg — worked example (v0.7 grammar)
# A routine draft gate and a decide gate that reserves a high-risk automated
# decision to a human role: reserved is never auto. Two terminal gates; the
# master decides each egress path. Which kinds are reserved is policy.

actor  bot7
human  alice  role legal

gate   draft   risk low    grant bot7
gate   decide  risk high   grant bot7

reserve automated_decision by legal when risk >= high

cord bot7   -> draft      # authority
cord bot7   -> decide     # authority
cord draft  -> master     # egress
cord decide -> master     # egress
```

A principal chain rooted in a person — the delegator anchors answerability and confers no authority (`conformance/vectors/obo-human-root/input.lg`):

```
# obo-human-root — the principal chain terminates at a human: the binding anchors
# answerability and constrains no grant. The human stays graph-disconnected and
# confers no authority; bot releases on its own grant (§3, §6).
human alice role dpo
actor bot on-behalf-of alice
gate g risk low grant bot[deploy:low]
cord g -> master
```

Both are conformance-tested: the first is a repository example, the second is a vector input — an invalid example in this skill is impossible by construction.
<!-- generated:example:end -->

### Step 5 — validate

This repository carries no implementation, so validate against its data:

1. **Self-check** the draft against every "Well-formed iff" bullet above.
2. **Structural check**: serialize the patch as JSON and validate against
   `schema/patch.schema.json`; a projected observation validates against
   `schema/observation.schema.json`.
3. **Compare against the vectors** — the ground truth for edge cases:

<!-- generated:conformance:begin -->
The suite has **65 vectors** (31 negative, 32 patch, 2 token), indexed in `conformance/manifest.json`. When unsure how a construct projects or which stage rejects it, read the matching vector: `expected.json` is the canonical observation; `reject.json` pins the stage.
<!-- generated:conformance:end -->

### Step 6 — report

State (a) what the patch governs, declaration by declaration; (b) every
policy choice made (kinds, thresholds, ladder, roles); (c) every host
hand-off with what the host must guarantee (time, identity binding, tag
integrity, obligation discharge); (d) that expressing a measure satisfies no
legal obligation by itself.
