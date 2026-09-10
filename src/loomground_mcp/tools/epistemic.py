# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""loomground-epistemic: extract the knowledge/belief facet of one sentence."""
from typing import Any

from ._result import Unavailable, tool

PLANE = "loomground-epistemic"


@tool(PLANE, "loomground_epistemic.extract")
def epistemic_extract(sentence: str) -> dict[str, Any]:
    """Extract who knows or believes what: `operator` (K knowledge, B belief), `holder`, `proposition`, `certainty` (certain > reasonable-grounds > probable > possible > estimate), `source` (evidential phrase, may be empty). No epistemic cue → `unavailable`."""
    from loomground_epistemic import extract
    facet = extract(sentence)
    if facet is None:
        raise Unavailable("no epistemic operator: the sentence carries no knowledge/belief cue")
    return facet


TOOLS = [epistemic_extract]
