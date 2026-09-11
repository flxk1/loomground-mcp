# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The runtime controls: lock, lane, drift, erasure.

Only the read-only face of each plane is served: nothing here approves a lane, renews a lease,
seals a folder or purges a chain — those stay the host's own acts. Each plane is optional; one
that is not installed comes back `unavailable`, never an error.
"""
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

from ._result import enum_of, import_plane, tool


@tool("loomground-lock", "lock_text / verdicts.verdict_for_action")
def lock_text(text: str, context: str = "", mode: str = "standard", source: str = "document",
              moderation_rules: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """May this text leave? Tier B (regex) + B+ (confusables) + C (context terms, then the semantic tier),
    plus Tier M when `moderation_rules` is given. `mode` = standard | strict | permissive | audit_only.
    Returns `action` (allow|minimise|refuse), the `.lg` `verdict` it maps to, the findings and the
    redacted text; a semantic tier that cannot run adds a high-severity finding and refuses."""
    lk = import_plane("loomground_lock")
    d = lk.lock_text(text, context=context, mode=enum_of(lk.Mode, mode), source=source,
                     moderation_rules=moderation_rules)
    return {"action": d.action, "verdict": lk.verdict_for_action(d.action), "reason": d.reason,
            "source": d.source, "findings": d.findings, "redacted_text": d.redacted_text}


@tool("loomground-lane", "evaluate_lane")
def lane_evaluate(lane: Optional[dict[str, Any]], request: dict[str, Any], use_case_id: str = "",
                  connector_id: str = "", policy_fingerprint: str = "") -> dict[str, Any]:
    """Does a request fall inside the approval envelope a human granted? lane = {lane_id, agent, max_grade,
    action_classes, footprints?, folder?, use_cases?, connectors?, policy_fingerprint?, version?, approved_by?,
    rationale?}; request = {agent, action_class, autonomy_grade, footprint: [..], folder?}. `lane` = null fails
    closed. Returns lane_id, allowed and the violations."""
    ln = import_plane("loomground_lane")
    gl = None if lane is None else ln.GovernanceLane(
        str(lane["lane_id"]), str(lane["agent"]), str(lane["max_grade"]),
        tuple(lane.get("action_classes") or ()), tuple(lane.get("footprints") or ()),
        str(lane.get("folder", "")), tuple(lane.get("use_cases") or ()), tuple(lane.get("connectors") or ()),
        str(lane.get("policy_fingerprint", "")), int(lane.get("version", 1)),
        str(lane.get("approved_by", "")), str(lane.get("rationale", "")))
    req = SimpleNamespace(agent=str(request["agent"]), action_class=str(request["action_class"]),
                          autonomy_grade=str(request["autonomy_grade"]),
                          footprint=tuple(request.get("footprint") or ()), folder=str(request.get("folder", "")))
    return ln.evaluate_lane(gl, req, use_case_id=use_case_id, connector_id=connector_id,
                            policy_fingerprint=policy_fingerprint)


@tool("loomground-drift", "Breaker.status")
def drift_breaker(lease: dict[str, Any], tripwires: Optional[list[dict[str, Any]]] = None,
                  metrics: Optional[dict[str, Any]] = None, now: Optional[float] = None) -> dict[str, Any]:
    """What grade does a leased agent actually hold now? lease = {agent, granted_grade, expires_at, ttl_seconds?,
    granted_at?} (epoch seconds); tripwires = [{name, metric, limit, kind: max|min|flag}], omitted → the drift
    tripwire alone; metrics = the readings to test against them (a missing metric is a gap, never a trip).
    Returns state RUNNING | DECAYED | QUARANTINED, the effective grade, the tripped wires and the verdict.
    The breaker is evaluated fresh per call: keeping a quarantine sticky, and clearing it by a named human,
    stay the host's."""
    dr = import_plane("loomground_drift")
    ls = dr.Lease(str(lease["agent"]), str(lease["granted_grade"]), float(lease["expires_at"]),
                  **{k: float(lease[k]) for k in ("ttl_seconds", "granted_at") if lease.get(k) is not None})
    wires = ([dr.Tripwire(str(t["name"]), str(t["metric"]), float(t["limit"]), str(t.get("kind", "max")))
              for t in tripwires] if tripwires is not None else [dr.drift_tripwire()])
    return dr.Breaker(ls, wires).status(metrics=metrics, now=now)


@tool("loomground-erasure", "sweep")
def erasure_sweep(folder: str, subject: str, cascade: bool = False, log_root: Optional[str] = None) -> dict[str, Any]:
    """What would an erasure reach, before anything is deleted? Every chain event in `folder` (and, with
    `cascade`, its registered descendants) naming `subject`, the composite tombstone it would write, the sealed
    stores it would queue, and the `blind_spots` no host port covers. Read only — `execute` purges a signed
    chain and stays the host's reserved act."""
    er = import_plane("loomground_erasure")
    return er.sweep(folder, subject, cascade=cascade, log_root=Path(log_root) if log_root else None)


TOOLS = [lock_text, lane_evaluate, drift_breaker, erasure_sweep]
