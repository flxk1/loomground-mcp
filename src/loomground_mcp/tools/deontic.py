# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""loomground-deontic: parse a canonical deontic statement, flag candidate clashes across a set."""
from typing import Any

from ._result import tool

PLANE = "loomground-deontic"


@tool(PLANE, "deontic.grammar.parse")
def deontic_parse(statement: str) -> dict[str, Any]:
    """Parse one canonical statement `[if [c] then] O|P|F(bearer : action) [unless [e]]` into its formula fields. `formula` is the canonical render; `round_trip` is whether parse(render) equals the parsed formula; `validation` is the structural check."""
    from deontic import parse, validate
    f = parse(statement)
    d = f.to_dict()
    d["round_trip"] = parse(d["formula"]) == f
    d["validation"] = validate(f)
    return d


@tool(PLANE, "deontic.contract.conflict_candidates")
def deontic_conflicts(statements: list[str]) -> dict[str, Any]:
    """Parse each statement and flag candidate SDL clashes (same bearer and action, incompatible modality) as `may-conflict-with` edges. Candidates are flagged, never resolved; condition/exception scope is deliberately ignored."""
    from deontic import conflict_candidates, parse
    formulae = [parse(s) for s in statements]
    return {"n_statements": len(formulae), "formulae": [f.render() for f in formulae],
            "candidates": conflict_candidates(formulae)}


TOOLS = [deontic_parse, deontic_conflicts]
