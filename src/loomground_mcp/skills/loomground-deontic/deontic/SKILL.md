---
name: deontic
description: 'Transcribe a natural-language norm into a verified deontic formula. Use when the user wants to formalise an obligation, permission, or prohibition as a typed statement O/P/F(bearer : action); classify the Hohfeldian incident (claim, duty, privilege, no-right, power, liability, immunity, disability); decide whether a "right" is a claim or a liberty; validate a deontic statement; or flag candidate normative conflicts across a set of norms. The procedure transcribes each norm, classifies its incident, validates it against the schema with a bundled engine, flags conflicts, and reports what is a deontic statement versus what belongs to the reasoning layer. Triggers on "formalise this obligation", "write this as a deontic statement", "O/P/F", "is this a claim or a liberty", "validate this deontic formula", "are these norms in conflict".'
allowed-tools: deontic_parse deontic_conflicts
---

# Deontic skill — transcribe, classify, validate

Turn a natural-language norm into a **verified** deontic formula. Deontic
*transcribes* a norm and states the identities over it; it never infers,
schedules, or resolves. Express what is a norm and **hand the rest to the
reasoning layer**, then prove each statement is well-formed.

The bundled engine (`deontic_engine.py`, stdlib-only) is the checker; run it, do
not hand-judge well-formedness.

## Step 0 — Load the language
Read `llms.txt` and `deontic-card.json` from the package artifacts (or this
skill's copy). They give the whole surface: three modalities `O`/`P`/`F` (one
primitive; `F≡O¬`, `P≡¬O¬`), the eight Hohfeld incidents in four correlative
pairs, and the canonical statement grammar.

## Step 1 — Split each norm into its slots
For every norm in the request, read off:
- **modality** — obligation (`O`), permission (`P`), prohibition (`F`). "Shall/
  must" → O; "may/is free to" → P; "shall not/must not" → F.
- **bearer** — the party the norm binds. **action** — what it scopes.
- **condition** — an applicability antecedent ("if/where/when …"), if any.
- **exception** — a defeasibility carve-out ("unless/except …"), if any.

## Step 2 — Resolve a "right" before formalising it
A "right" is ambiguous (this is Hohfeld's point). Decide:
- a **liberty-right** (a freedom to act oneself — "may access their data") is a
  **permission**; incident `privilege`.
- a **claim-right** (a right that another act — "the right to erasure/payment/
  notice") is the counterparty's **duty**: build `O(obligor : action)` with the
  holder as counterparty. Use `deontic_engine.claim_right(holder, action,
  obligor)`. Modelling a claim-right as a permission for the holder is the common
  mistake — it puts the modality on the wrong party.

## Step 3 — Transcribe and classify (the engine does the work)
Primary path: call `deontic_parse` with
`{"statement": "The processor shall not engage a subprocessor."}` — it returns
the formula fields (modality, bearer, action, condition, exception, incident,
negated) and the `render` round-trip.

Shell fallback — the bundled engine, so the incident classification and
structure are deterministic:
```
import deontic_engine as eng
f = eng.formula_from_fields("prohibition", "processor", "engage a subprocessor",
                            exception="the controller authorises it",
                            raw_sentence="The processor shall not engage a subprocessor.")
eng.render(f)      # F(processor : engage a subprocessor) unless [the controller authorises it]
f["incident"]      # "duty"
eng.correlative(f["incident"])   # "claim" — the counterparty's position
```
Carry negation in the `negated` sense (a permission-to-refrain), never as the
word "not" inside the action text, or the algebra cannot pair or clash it.

## Step 4 — Validate every statement
Primary path: a rendered statement `deontic_parse` returns fields for is
well-formed; one it cannot parse comes back as an `ok: false` envelope naming
the parse/validate reason. Shell fallback — run the checker on each rendered
statement:
```
python3 validate.py "F(processor : engage a subprocessor) unless [the controller authorises it]"
# WELL-FORMED  + the structured projection, or  REJECTED (parse|validate): reason
```
A statement that will not validate is not a deontic formula — fix the slots.

## Step 5 — Flag conflicts, do not resolve them
Across the whole set, call `deontic_conflicts` with
`{"statements": ["O(a : x)", "F(a : x)", ...]}` — each statement is parsed and
the candidate conflicts returned (shell fallback:
`eng.detect_conflicts([...])`). A candidate conflict is
the same bearer and unsigned action bound to incompatible truth values. Polarity
matters: `O(a)` clashes with `O(¬a)`, while `O(¬a)` and `F(a)` agree. The skill
**flags** it (`resolution: candidate-escalate`); it never picks a winner — a
genuine conflict is a human/reasoning-layer decision.

## Step 6 — Report, and name what is not a norm
Report, per norm: the deontic statement, its incident and the counterparty's
correlative, and any flagged conflicts. Then name what did **not** become a
statement and why — the reasoning layer owns it:
- **time** — deadlines, discharge, expiry ("within 72 hours", "until revoked")
  are carried as text; the language has no temporal type.
- **discretion** — "may … at its discretion / in hardship" is a plain `P`; the
  escalate-on-discretion decision is a reasoning-layer concern.
- **resolution** — which of two conflicting norms wins is never decided here.

## The rule
Transcribe, classify, validate, flag — never infer, schedule, or resolve. A
norm's *form* lives here; its *reasoning* is a host's.
