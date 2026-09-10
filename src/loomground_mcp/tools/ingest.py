# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""loomground-ingest: text -> dimensioned subgraph (nothing persisted; the writer collects)."""
from typing import Any, Optional

from ._result import Unavailable, tool

PLANE = "loomground-ingest"
_INGESTERS = {"deontic": "DeonticIngester", "policy": "GovernanceIngester"}


@tool(PLANE, "loomground_ingest.ingest_text")
def ingest_text(text: str, ingesters: Optional[list[str]] = None, max_input_chars: Optional[int] = 1000000) -> dict[str, Any]:
    """Route text through the built-in ingesters (deontic, policy) and return the subgraph summary: nodes, edges, rejections, quarantined, plus the nodes and edges themselves."""
    import loomground_ingest as li
    reg = li.IngesterRegistry()
    for key in ingesters or list(_INGESTERS):
        if key not in _INGESTERS:
            raise ValueError(f"unknown ingester {key!r}; built-ins: {sorted(_INGESTERS)}")
        reg.register(getattr(li, _INGESTERS[key])())
    writer = li.CollectingWriter()
    out = li.ingest_text(text, registry=reg, writer=writer, max_input_chars=max_input_chars)
    if out.get("reason") == "no_ingester":
        raise Unavailable("no registered ingester claims this text")
    out["subgraphs"] = [{"dimension": s.dimension, "quarantined": s.quarantined, "nodes": s.nodes, "edges": s.edges,
                         "rejections": s.rejections, "provenance": s.provenance} for s in writer.written]
    return out


TOOLS = [ingest_text]
