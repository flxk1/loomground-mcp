---
name: epistemic
description: 'Extract who knows or believes what, at which certainty band, from one sentence: operator K (knowledge) or B (belief), holder, proposition, certainty (certain, reasonable-grounds, probable, possible, estimate) and evidential source. Use when the user wants a sentence read as a knowledge or belief claim, asks which cue words loomground-epistemic recognises (knows, is aware, believes, reasonable grounds to suspect, estimates that, based on), or needs the certainty band of a statement; triggers on "who knows this", "is this knowledge or belief", "certainty band", "epistemic facet". Whether the belief is true and what duty follows belong to the other planes.'
allowed-tools: epistemic_extract
metadata:
  version: "1.0"
---

# loomground-epistemic — language card

Primary path: call `epistemic_extract` with `{"sentence": "The processor believes the transfer was lawful."}`; the `result` carries `operator, holder, proposition, certainty, source` (plus `facet`, `system_id`), and a sentence without an epistemic cue comes back `unavailable`.

Shell fallback: `python3 -c 'from loomground_epistemic import extract; print(extract("The processor believes the transfer was lawful."))'` (package `loomground-epistemic`; `None` = no cue).

Cues from `src/loomground_epistemic/artifacts/extraction.json` (0.1.0); the plane has no keywords. Every sentence below was run through `extract` before this card was written; the outputs are pasted from that run.

## Facet

`system:epistemic`, fields `operator · holder · proposition · certainty · source`. `binds`: proposition → relational, holder → intentional, certainty → causal, assertion → temporal (`EPISTEMIC_FACET`).

## Operators and certainty bands

`K` knowledge · `B` belief. Bands, descending: `certain > reasonable-grounds > probable > possible > estimate`.

## Cue table (surface → operator · band; first match in listed order wins)

| cue words | operator · band |
|---|---|
| `reasonable grounds to believe` · `reasonable grounds to suspect` | B · reasonable-grounds |
| `has reason to believe` | B · possible |
| `knows` · `know` · `is aware` · `becomes aware` · `has become aware` · `established that` · `it is known that` | K · certain |
| `suspects` · `suspect` | B · possible |
| `believes` · `believe` · `considers that` · `is satisfied that` · `is of the view that` · `is of the opinion that` | B · probable |
| `is likely` · `are likely` · `likely to` · `expects that` · `anticipates that` | B · probable |
| `estimates that` · `assesses that` | B · estimate |
| `on the basis of` · `based on` · `according to` · `in light of` … (up to the next `.` `;` `,`) | evidential `source` |

Holder: the entity phrase before the cue, stripped of a leading `where / when / if / provided that / in the case that` and a trailing auxiliary (`has / have / is / are / was / were`), then cleaned with `loomground_factual.clean_entity` (consumed, not duplicated). Proposition: the text after the cue, stripped of a leading `that / to / a / an / the`.

## Readings

```
The controller knows that the data is inaccurate.                          K · controller · the data is inaccurate · certain
The processor believes the transfer was lawful.                            B · processor · transfer was lawful · probable
The controller has reasonable grounds to believe that the breach is likely to result in a risk.
                                                                           B · controller · the breach is likely to result in a risk · reasonable-grounds
The supervisory authority suspects that the transfer was unlawful.         B · supervisory authority · the transfer was unlawful · possible
The processor estimates that the incident affected 400 records.            B · processor · incident affected 400 records · estimate
The auditor considers that the record is complete, based on the log.       B · auditor · record is complete, based on the log · probable · source: the log
```

Outputs as returned:

```
{'facet': 'nD', 'system_id': 'system:epistemic', 'operator': 'K', 'holder': 'controller', 'proposition': 'the data is inaccurate', 'certainty': 'certain', 'source': ''}
{'facet': 'nD', 'system_id': 'system:epistemic', 'operator': 'B', 'holder': 'processor', 'proposition': 'transfer was lawful', 'certainty': 'probable', 'source': ''}
{'facet': 'nD', 'system_id': 'system:epistemic', 'operator': 'B', 'holder': 'controller', 'proposition': 'the breach is likely to result in a risk', 'certainty': 'reasonable-grounds', 'source': ''}
{'facet': 'nD', 'system_id': 'system:epistemic', 'operator': 'B', 'holder': 'supervisory authority', 'proposition': 'the transfer was unlawful', 'certainty': 'possible', 'source': ''}
{'facet': 'nD', 'system_id': 'system:epistemic', 'operator': 'B', 'holder': 'processor', 'proposition': 'incident affected 400 records', 'certainty': 'estimate', 'source': ''}
{'facet': 'nD', 'system_id': 'system:epistemic', 'operator': 'B', 'holder': 'auditor', 'proposition': 'record is complete, based on the log', 'certainty': 'probable', 'source': 'the log'}
```

Limits visible in the outputs: a proposition keeps a trailing source phrase; a leading article on the proposition is stripped (`transfer was lawful`); a holder introduced by `there are` resolves to `there` and is out of scope for this version.

## Outside the language

Whether the belief is true; what duty follows (`loomground-norm`, `loomground-deontic`); when the belief was formed, beyond the sentence itself.

Same card, README-linked copy: `../../docs/language-card.md`.
