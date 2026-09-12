# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Applied skill runtimes: policy compilation, evidence, privacy and A2A grounding.

Each wrapper calls the public package API.  It does not reproduce a plane inside
the MCP server, activate policy, dispatch a directive, or handle production key
material.
"""
import json
from importlib.resources import files
from typing import Any, Optional

from ._result import enum_of, import_plane, tool


@tool("policy-compiler", "policy_compiler.compile")
def policy_compile(policy: str) -> dict[str, Any]:
    """Compile policy text to a validated draft with norms, conflicts, undetermined
    rules, residual spans and the compliance-fleet grounding seam.  Read only: the
    draft is not activated or applied."""
    pc = import_plane("policy_compiler")
    compiled = pc.compile(policy)
    return {"draft": compiled, "grounding_seam": compiled.to_grounding_seam()}


@tool("policy-compiler", "policy_compiler.check")
def policy_check(policy: str, cases: list[dict[str, Any]]) -> Any:
    """Compile policy text and run explicit cases of the form
    {actor, action, expect}.  Returns the per-case result and aggregate verdict;
    it never activates the draft."""
    pc = import_plane("policy_compiler")
    report = pc.check(policy, cases)
    return {"ok": report.ok, "total": report.total, "passed": report.passed,
            "results": report.results}


@tool("evidence-emitter", "evidence_emitter.emit")
def evidence_emit(subject: dict[str, Any], kind: Optional[str] = None,
                  components: Optional[list[str]] = None,
                  issued_at: Optional[str] = None) -> dict[str, Any]:
    """Emit one offline-verifiable evidence package with the package's explicitly
    non-production development signer.  This MCP surface accepts, creates and
    stores no production key material; absent assurance components stay marked
    absent."""
    ee = import_plane("evidence_emitter")
    package = ee.emit(subject, kind=kind, components=components, issued_at=issued_at)
    return {"envelope": package.to_dict(), "statement": package.statement,
            "signer_production": False}


@tool("evidence-emitter", "evidence_emitter.verify")
def evidence_verify(envelope: dict[str, Any]) -> Any:
    """Verify a development-signed evidence package fully offline.  Production
    Ed25519 verification remains a host operation because key trust is not an MCP
    default."""
    ee = import_plane("evidence_emitter")
    return ee.verify(envelope)


@tool("privacy-shield", "brain.privacy_shield.scan")
def privacy_scan(text: str, mode: str = "standard", destination: str = "external_llm",
                 redaction_mode: str = "redact", min_confidence: str = "medium",
                 audit_log_path: Optional[str] = None, tenant_id: str = "",
                 user_id: str = "") -> Any:
    """Scan raw text locally, produce its clean overlay and decide whether that
    overlay may leave for `destination`.  The original text and placeholder map
    never leave this call.  The package records its normal local audit event."""
    ps = import_plane("brain.privacy_shield")
    scanner = import_plane("brain.privacy_shield.scanner")
    return ps.scan(
        text,
        mode=enum_of(ps.PrivacyMode, mode),
        destination=destination,
        redaction_mode=enum_of(ps.RedactionMode, redaction_mode),
        min_confidence=enum_of(scanner.Confidence, min_confidence),
        audit_log_path=audit_log_path,
        tenant_id=tenant_id,
        user_id=user_id,
        force_text=True,
    )


@tool("a2a-compliance", "a2a_compliance.ground")
def a2a_ground(context: dict[str, Any], planes: Optional[list[str]] = None) -> Any:
    """Ground a maker state against the available Loomground value planes and
    return the bounded recommendation: no-steer, steer, hold or route-human.
    This is derivation only; dispatching or halting an agent remains a host act."""
    a2a = import_plane("a2a_compliance")
    ctx = a2a.GroundingContext(**context)
    selected = tuple(planes) if planes is not None else tuple(a2a.ALL_PLANES)
    return a2a.ground(ctx, selected)


def _declared_team_inventory(a2a: Any) -> Any:
    """Read the surfaces this MCP distribution actually publishes.

    This proves discoverability, not successful execution: every later tool call
    can still return its normal fail-closed ``unavailable`` envelope.
    """
    from loomground_mcp.tools import ALL

    root = files("loomground_mcp")
    catalogue = json.loads(root.joinpath("catalogue.json").read_text(encoding="utf-8"))
    skill_index = json.loads(root.joinpath("skills/index.json").read_text(encoding="utf-8"))
    repos = {item["repo"] for item in catalogue["repos"]}
    return a2a.CapabilityInventory.from_iterables(
        tools=(fn.__name__ for fn in ALL),
        skills=(item["name"] for item in skill_index if not item.get("private")),
        contracts=repos,
        distributions={"loomground-plugins", "loomground-patchbay", "loomground-mcp"} & repos,
    )


@tool("a2a-compliance", "a2a_compliance.ComplianceTeam.plan")
def a2a_plan(context: dict[str, Any], target_kind: str, governance: dict[str, Any],
             planes: Optional[list[str]] = None, profile: str = "loomground") -> Any:
    """Build the inert compliance-team plan over the MCP server's declared
    tools, public skills and family contracts.  In the Loomground profile it
    also binds the current six-plane grounding result.  ``ready`` means ready
    for the host to run the named hand-offs, never permission to dispatch or
    proof that those tools have already succeeded."""
    a2a = import_plane("a2a_compliance")
    ctx = a2a.GroundingContext(**context)
    request = a2a.ControlRequest(
        context=ctx,
        target_kind=target_kind,
        governance=a2a.GovernanceBlock.from_dict(governance),
        profile=a2a.TeamProfile(profile),
    )
    grounding_result = None
    if request.profile is a2a.TeamProfile.LOOMGROUND:
        selected = tuple(planes) if planes is not None else tuple(a2a.ALL_PLANES)
        grounding_result = a2a.ground(ctx, selected)
    plan = a2a.ComplianceTeam(_declared_team_inventory(a2a)).plan(
        request, grounding_result=grounding_result,
    )
    return {"plan": plan, "inventory_source": "loomground-mcp published surface",
            "dispatch_performed": False}


TOOLS = [policy_compile, policy_check, evidence_emit, evidence_verify, privacy_scan,
         a2a_ground, a2a_plan]
