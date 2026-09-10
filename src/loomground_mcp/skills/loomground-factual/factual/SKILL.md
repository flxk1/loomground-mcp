---
name: factual
description: 'Lower one plain assertion into a factual triple: subject, predicate, object, with dimension (structural for is-a and part-of, relational for any other copula), negation and quantification. Use when the user wants a sentence read as a fact, asks what loomground-factual recognises (copulas, negation, quantifiers, entity trimming), or needs to know whether a sentence has a copula at all; triggers on "lower this sentence", "is this a fact", "subject predicate object", "factual triple". Ought, knowledge, time and authority belong to the other planes.'
allowed-tools: factual_lower
metadata:
  version: "1.0"
---

# loomground-factual — language card

Primary path: call `factual_lower` with `{"sentence": "The operator is a controller."}`; the `result` is `{subject, predicate, object, dimension, negated, quantification}`, and a sentence without a copula comes back `unavailable` (no copula), never as a guessed triple.

Shell fallback: `python3 -c 'from loomground_factual import lower; print(lower("The operator is a controller."))'` (package `loomground-factual`; `None` = no copula).

Cues from `src/loomground_factual/artifacts/extraction.json` (0.1.0); the plane has no keywords. Every sentence below was run through `lower` before this card was written; the outputs are pasted from that run.

## What it recognises in one sentence

| cue class | cue words | effect |
|---|---|---|
| structural predicate | `is a` · `is an` · `is one of` · `is a type of` · `is a kind of` · `is a category of` · `is part of` · `is comprised of` · `is composed of` (also with `are`, `shall be`, and an intervening `not`) | dimension `structural` |
| copula | `is` · `are` · `shall be` · `means` · `include` / `includes` / `included` · `consists of` / `consist of` · `refers to` / `refer to` | the predicate; a copula outside the structural class → `relational` |
| negation | `not` · `no` · `never` · `neither` · `without` | `negated: true` |
| universal quantifier | `all` · `any` · `every` · `each` | `quantification: universal` |
| existential quantifier | `some` · `a` · `an` | `quantification: existential` |
| empty quantifier | `no` · `none of` · `neither` | `quantification: empty` |
| entity trimming | leading list markers and numbering; leading `a / an / the / its / their / any / this / each / every / all / both / such / no` (also `der / die / das / ein / eine / jede`); trailing `which / who / whose / to which / as referred to / referred to in / pursuant to / adopted by / involved in …` | clean subject and object |

## Output

`lower(sentence) → {subject, predicate, object, dimension, negated, quantification}`, or `None` when the sentence has no copula. `clean_entity(span)` reduces a span to its NP head with the entity cues; `load_json(name)` loads a packaged artifact.

## Readings

```
The operator is a controller.            operator · is · controller · structural · existential
A processor is not a controller.         processor · is · controller · structural · negated · existential
Every controller is a natural person.    controller · is · natural person · structural · universal
No processor is a controller.            processor · is · controller · structural · negated · empty
The register consists of entries.        register · consists of · entries · relational · existential
Personal data means any information relating to an identified person.
                                         Personal data · means · any information relating to an identified person · relational · existential
Every controller keeps a record.         None  (keeps is no copula; the sentence is no fact here)
```

Outputs as returned:

```
{'subject': 'operator', 'predicate': 'is', 'object': 'controller', 'dimension': 'structural', 'negated': False, 'quantification': 'existential'}
{'subject': 'processor', 'predicate': 'is', 'object': 'controller', 'dimension': 'structural', 'negated': True, 'quantification': 'existential'}
{'subject': 'controller', 'predicate': 'is', 'object': 'natural person', 'dimension': 'structural', 'negated': False, 'quantification': 'universal'}
{'subject': 'processor', 'predicate': 'is', 'object': 'controller', 'dimension': 'structural', 'negated': True, 'quantification': 'empty'}
{'subject': 'register', 'predicate': 'consists of', 'object': 'entries', 'dimension': 'relational', 'negated': False, 'quantification': 'existential'}
{'subject': 'Personal data', 'predicate': 'means', 'object': 'any information relating to an identified person', 'dimension': 'relational', 'negated': False, 'quantification': 'existential'}
None
```

## Outside the language

Ought (`loomground-deontic`), knowledge and belief (`loomground-epistemic`), time, authority (`loomground-topos`). A sentence without a copula is out of scope.

Same card, README-linked copy: `../../docs/language-card.md`.
