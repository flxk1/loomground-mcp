---
name: topos
description: 'Read and write lt, the legal-system topology language: system, level, organ, instrument, competence statements, rel relations between them (outranks, has-primacy-over, reviews, must-be-transposed-by ...) and assert claims by a named organ, with props (resolution_mode, state, status, deadline, basis). Use when the user wants to express which source outranks which, who reviews or transposes what, or the competence of an organ, needs an lt block parsed or checked, or asks for the relation vocabulary; triggers on "write this in lt", "topology statement", "has-primacy-over", "parse this lt block". What an instrument says and the facts of a case belong to the other planes.'
allowed-tools: topos_parse
metadata:
  version: "1.0"
---

# `lt` — language card

Primary path: call `topos_parse` with `{"text": "organ de:bverfg  system de  level de:federal  powers {judicial}\nrel eu:regulation has-primacy-over de:formal-statute [resolution_mode = disapply]"}`; the `result` carries the statements as records (keyword, id, attributes, relation, props) and the errors with their line numbers.

Shell fallback: `python3 -c 'from loomground_mcp.tools.topos import topos_parse; print(topos_parse(open("block.lt").read()))'` (the reader lives in loomground-mcp, implemented from `../../grammar/topos.ebnf`, which stays normative); any `.lt` block placed in a file under `../../examples/` is also checked by the CI job.

Values come from [`grammar/topos.ebnf`](../../grammar/topos.ebnf) and [`spec/SPEC.md`](../../spec/SPEC.md). One statement per line; `#` opens a comment; an indented line continues the statement above. Any `id` parses; membership in a ladder or catalogue is checked at apply time.

## Statements

| form | attributes |
|---|---|
| `system <id>` | `tradition <id>` · `powers <catalogue>` · `levels <ladder>` · `ranks <ladder>` |
| `level <id>` | `system <id>` · `rank <n>` (territorial) · `contains <level>` |
| `organ <id>` | `system <id>` · `level <id>` · `powers <label \| {label, …}>` · `party <id>` |
| `instrument <id>` | `system <id>` · `rank <n \| null>` (normative; `null` = not yet grounded) · `origin <organ>` · `direct-effect none \| vertical \| horizontal` · `directly-applicable` |
| `competence <id>` | `system <id>` · `allocation <id>` · `holder <organ>` |
| `rel <a> <relation> <b> [props]` | a settled relation |
| `assert <organ> : [NOT] <a> <relation> <b> [props]` | a relation claimed or denied by a named organ; two opposite assertions over one triple form a contested edge |

`id` = letter, then letters, digits, `-`, `_`, `:`, `#`.

## Relations

| class | relations |
|---|---|
| vertical | `outranks` · `derives-authority-from` · `level-contains` · `has-primacy-over` |
| horizontal | `co-equal-with` · `reviews` · `can-veto` · `can-override` · `appoints` · `dissolves` · `may-refer-to` · `must-refer-to` |
| coupling (endpoints in different systems) | `has-primacy-over` · `applies-directly-in` · `must-be-transposed-by` · `confers-competence` · `has-direct-effect` · `may-refer-to` · `must-refer-to` |

## Props

`[key = value, …]` on `rel` and `assert`. Keys: `resolution_mode` = `disapply` \| `invalidate` \| `void` · `state` = `pending` \| `transposed` \| `gap` \| `partial` · `status` = `asserted` \| `contested` · `deadline` = `YYYY-MM-DD` · `basis` = `"text"` · any further `id`.

## Readings

```lt
system de  tradition civil  powers separation-tripartite  levels de-levels  ranks de-ranks   # a civil-law order with its power catalogue and ladders
level  de:federal  system de  rank 0  contains de:land                  # the federal level, territorial rank 0, contains the Land level
organ  de:bverfg   system de  level de:federal  powers {judicial}       # the constitutional court: federal level, judicial power
instrument eu:regulation  system eu  rank 1  origin eu:parliament-council  directly-applicable   # normative rank 1, directly applicable
competence de:police  system de  allocation reserved  holder de:land    # police is a reserved competence held by the Länder
rel eu:regulation  has-primacy-over  de:formal-statute  [resolution_mode = disapply, basis = "Costa 6/64"]   # the statute is set aside
rel de:bverfg  reviews  de:formal-statute                               # the court reviews statutes
rel eu:directive-2019-790  must-be-transposed-by  de:system  [deadline = 2021-06-07, state = transposed]   # due 2021-06-07, transposed
assert de:bverfg : NOT eu:primary-law has-primacy-over de:grundgesetz  [status = contested, basis = "Solange II BVerfGE 73,339"]   # the court denies primacy; recorded as contested
```

Two rank axes: `rank` on a level is territorial; `rank` on an instrument is normative.

## Output

The parse yields a topology graph (`grammar/topos.ebnf`, appendix): `systems`, `nodes` (class `organ` \| `level` \| `instrument` \| `competence`), `relations` with props, `asserted_by`, `polarity` `affirm` \| `deny`, `status`. A resolver walking a contested pair returns `contested / unresolved` and hands off.

## Not expressible

What an instrument says (deontic), the facts of a case (factual), when a norm was in force beyond point dates (interval axis pending).

All nine statements above were re-checked with the CI job's reader (`.github/workflows/main.yml`) on this file.

Same card, README-linked copy: `../../docs/language-card.md`.
