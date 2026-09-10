# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""loomground-factual: lower one copula-form assertion into its 5D edge fields."""
from typing import Any

from ._result import Unavailable, tool

PLANE = "loomground-factual"


@tool(PLANE, "loomground_factual.lower")
def factual_lower(sentence: str) -> dict[str, Any]:
    """Lower one assertion into `subject`, `predicate`, `object`, `dimension` (structural for is-a/part-of, else relational), `negated`, `quantification` (universal/existential/empty). A sentence without a copula is not a fact here → `unavailable`."""
    from loomground_factual import lower
    edge = lower(sentence)
    if edge is None:
        raise Unavailable("no copula: the sentence is not an assertion loomground-factual lowers")
    return edge


TOOLS = [factual_lower]
