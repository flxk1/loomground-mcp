# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""loomground-norm: rule extraction from running text, lifted into deontic formulae."""
from typing import Any

from ._result import tool

PLANE = "loomground-norm"


@tool(PLANE, "rule_extractor.extract_rules + deontic_lift.formula_from_rule")
def norm_extract(text: str, language: str = "en") -> dict[str, Any]:
    """Extract every rule the Phase-1 extractor finds in `text` (one RuleFacet per matched sentence: subject, modal, modal_phrase, action, condition, exception, consequence, language, confidence) and lift each into a deontic formula (`formula` = canonical render, `formula_fields` = the carrier). The extractor detects each sentence's language itself; `language` must be one of the 24 supported codes and is echoed beside `languages_detected` so a mismatch is visible. No rule → `n_rules` 0, never an error."""
    from loomground_norm import extract_rules, formula_from_rule
    from loomground_norm.rule_extractor import supported_languages
    if language not in supported_languages():
        raise ValueError(f"language {language!r} not in {supported_languages()}")
    rules = extract_rules(text)
    out = []
    for r in rules:
        f = formula_from_rule(r)
        out.append({"rule": r.to_dict(), "formula": f.render(), "formula_fields": f.to_dict()})
    return {"language": language, "languages_detected": sorted({r.language for r in rules}),
            "n_rules": len(out), "rules": out}


TOOLS = [norm_extract]
