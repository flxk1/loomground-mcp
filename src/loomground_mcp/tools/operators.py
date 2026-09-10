# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The six diagnostic operators above the solver: collapse, escalation, falsifiability, proxy, mandate, brief."""
from typing import Any, Optional

from ._result import Unavailable, enum_of, tool


@tool("loomground-collapse", "loomground_collapse.collapse")
def collapse(constituents: list[dict[str, Any]]) -> dict[str, Any]:
    """Weakest-link fold over constituents [{name, state: PRESENT|AT_FLOOR|UNASSIGNED, note?}]. Returns overall verdict and per-term verdicts."""
    import loomground_collapse as c
    items = [c.Constituent(str(x["name"]), enum_of(c.ConstituentState, x["state"]), str(x.get("note", ""))) for x in constituents]
    return c.collapse(items)


@tool("loomground-escalation", "loomground_escalation.ceiling / autonomy_verdict")
def escalation(factors: list[dict[str, Any]], delegated: str, ladder: list[str], requested: Optional[str] = None) -> dict[str, Any]:
    """Lowest autonomy ceiling over factors [{name, ceiling?, why?}] on the caller's ascending ladder; unassessed factors cap at the floor. With `requested`, adds the verdict."""
    import loomground_escalation as e
    lad = e.Ladder(tuple(ladder))
    esc = e.ceiling([e.Factor(str(f["name"]), f.get("ceiling"), str(f.get("why", ""))) for f in factors],
                    delegated=delegated, ladder=lad)
    out: dict[str, Any] = {"granted": esc.granted, "binding": esc.binding, "delegated": esc.delegated,
                           "ladder": lad.levels, "factors": esc.factors}
    if requested is not None:
        out["requested"], out["verdict"] = requested, e.autonomy_verdict(requested, esc)
    return out


@tool("loomground-falsifiability", "loomground_falsifiability.support_verdict / best_support")
def falsifiability(evidence: list[dict[str, Any]], floor: Optional[str] = None) -> dict[str, Any]:
    """Rank evidence [{ref, falsifiability: SELF_REPORT|DECLARED_PLAN|OBSERVED_TOOL_CALL|VERIFIED_OUTCOME|SPAN_GROUNDED|REPLAYABLE}]; SATISFIED at or above the floor, else OPEN."""
    import loomground_falsifiability as f
    items = [f.Evidence(str(x["ref"]), enum_of(f.Falsifiability, x["falsifiability"])) for x in evidence]
    fl = enum_of(f.Falsifiability, floor) if floor is not None else f.SUPPORT_FLOOR
    best = f.best_support(items)
    return {"verdict": f.support_verdict(items, floor=fl), "floor": fl.name, "best_support": best.name if best else None}


@tool("loomground-proxy", "loomground_proxy.check_proxies / fold_substitutions")
def proxy(proxies: list[dict[str, Any]], readings: dict[str, str]) -> dict[str, Any]:
    """Check declared proxies [{metric, stands_for, ref?}] against readings {subject: IMPROVED|UNCHANGED|WORSENED|UNMEASURED}. Returns substitutions (gamed, misleading, unchecked, tracking) and the fold."""
    import loomground_proxy as p
    subs = p.check_proxies([p.Proxy(str(x["metric"]), str(x["stands_for"]), str(x.get("ref", ""))) for x in proxies],
                           {str(k): enum_of(p.Movement, v) for k, v in readings.items()})
    return {"substitutions": subs, "fold": p.fold_substitutions(subs)}


def _ref(d: dict[str, Any]) -> Any:
    from loomground_solver.interop import EvidenceRef
    return EvidenceRef(source_id=str(d["source_id"]), item_id=str(d.get("item_id", "")),
                       span_start=d.get("span_start"), span_end=d.get("span_end"),
                       content_digest=str(d.get("content_digest", "")), graph_version=str(d.get("graph_version", "")),
                       locator=dict(d.get("locator") or {}), extensions=dict(d.get("extensions") or {}))


@tool("loomground-mandate", "loomground_mandate.detect / fold_divergences")
def mandate(mandate: dict[str, Any], steps: list[dict[str, Any]], evidence: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Compare a trajectory with its mandate. mandate = {evidence: EvidenceRef, purposes: [..]}; steps = [{ref, evidence: EvidenceRef, serves: [..], defeats: [..]}]. Both must verify through an evidence provider: pass evidence = {kg_root, libraries?} naming a synced versum store; without one the operator is unavailable, never a guess."""
    import loomground_mandate as m
    if not evidence or not evidence.get("kg_root"):
        raise Unavailable("no evidence provider: pass evidence={kg_root, libraries?} of a synced versum store")
    from versum.identity.evidence import StoreEvidenceProvider
    provider = StoreEvidenceProvider(evidence["kg_root"], evidence.get("libraries"))
    md = m.Mandate(_ref(mandate["evidence"]), frozenset(mandate.get("purposes") or ()))
    st = [m.TrajectoryStep(str(s["ref"]), _ref(s["evidence"]), frozenset(s.get("serves") or ()), frozenset(s.get("defeats") or ()))
          for s in steps]
    divs = m.detect(md, st, evidence=provider)
    return {"divergences": divs, "fold": m.fold_divergences(divs), "graph_version": provider.graph_version}


@tool("loomground-brief", "loomground_brief.oversight_brief")
def brief(premises: Optional[list[dict[str, Any]]] = None, space: Optional[dict[str, Any]] = None,
          negative_space: Optional[dict[str, Any]] = None, divergences: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
    """Minimum a supervisor must read. premises = [{name, status: asserted|inferred|presupposed|contested|unknown, depends_on?}]; space = {accepted, undecided, rejected, attacks}; divergences = [{ref, why}]. With nothing to brief on the operator is unavailable."""
    if not (premises or space or negative_space or divergences):
        raise Unavailable("nothing to brief on: pass premises, a decision space, a negative space or divergences")
    from loomground_brief import oversight_brief
    from loomground_solver.decision import DecisionSpace
    from loomground_solver.epistemic_status import EpistemicStatus, StatusedPremise
    prem = [StatusedPremise(str(p["name"]), enum_of(EpistemicStatus, p["status"]), p.get("fact"), tuple(p.get("depends_on") or ()))
            for p in premises or []]
    sp = DecisionSpace(list(space.get("accepted") or []), list(space.get("undecided") or []),
                       list(space.get("rejected") or []), list(space.get("attacks") or [])) if space else None
    divs = [(str(d["ref"]), str(d.get("why", ""))) for d in divergences or []]
    return oversight_brief(premises=prem, space=sp, negative_space=negative_space, divergences=divs)


TOOLS = [collapse, escalation, falsifiability, proxy, mandate, brief]
