# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The assurance artifacts: oversight-certificate, governance-certification, norm-freshness,
obligation-discharge, effect-reconciliation, enforcement-posture, 5d-nd, loomground-audit-chain.

Keys are passed in per call as PEM text and used once; the server generates and stores none —
except the audit chain, which verifies against the host's own identity key where it already lives.
"""
import json
from typing import Any, Callable, Optional

from ._result import enum_of, import_plane, tool


def _canonicalizer() -> tuple[Callable[[dict], bytes], str]:
    try:
        import rfc8785
        return rfc8785.dumps, "rfc8785"
    except ImportError:
        return (lambda d: json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")), "json-sorted"


def _signer(private_key_pem: str) -> Callable[[bytes], bytes]:
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    key = load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    return key.sign


def _verifier(public_key_pem: str) -> Callable[[bytes, bytes], bool]:
    from governance_certification.verify import ed25519_verifier_from_pem
    return ed25519_verifier_from_pem(public_key_pem.encode("utf-8"))


@tool("oversight-certificate", "oversight_certificate.issue")
def oversight_issue(cert: dict[str, Any], signing_key_pem: str, keyid: str = "") -> dict[str, Any]:
    """Mint a DSSE envelope over cert = {id, action, disposition: decided|escalated|abstained, at, basis, evidence?: [digest..], human?: {id, qualification, credential_not_after?}, escalated_to?, assistance?: {aid: unaided|deterministic|model, system?, same_model_family?}} with the caller's Ed25519 private key (PEM)."""
    import oversight_certificate as oc
    human = cert.get("human")
    assist = cert.get("assistance")
    c = oc.OversightCertificate(
        str(cert["id"]), str(cert["action"]), enum_of(oc.Disposition, cert["disposition"]), str(cert["at"]), str(cert["basis"]),
        evidence=tuple(cert.get("evidence") or ()),
        human=oc.Human(str(human["id"]), str(human["qualification"]), human.get("credential_not_after")) if human else None,
        escalated_to=cert.get("escalated_to"),
        assistance=oc.Assistance(enum_of(oc.Aid, assist["aid"]), str(assist.get("system", "")), assist.get("same_model_family")) if assist else None)
    canon, name = _canonicalizer()
    env = oc.issue(c, canonicalize=canon, sign=_signer(signing_key_pem), keyid=keyid)
    return {"envelope": env.to_dict(), "canonicalizer": name}


@tool("oversight-certificate", "oversight_certificate.verify")
def oversight_verify(envelope: dict[str, Any], public_key_pem: str, now: str, required_basis: Optional[str] = None) -> dict[str, Any]:
    """Offline re-check of an oversight-certificate envelope at time `now` (RFC 3339) with the Ed25519 public key (PEM). Returns ok, findings, independence."""
    import oversight_certificate as oc
    canon, name = _canonicalizer()
    rep = oc.verify(envelope, canonicalize=canon, verify_sig=_verifier(public_key_pem), now=now, required_basis=required_basis)
    return {"ok": rep.ok, "findings": rep.findings, "independence": rep.independence, "canonicalizer": name}


@tool("governance-certification", "governance_certification.verify.verify")
def govcert_verify(envelope: dict[str, Any], public_key_pem: str) -> dict[str, Any]:
    """Offline re-check of a GovernanceCertification DSSE envelope: signature, predicate type, the enforced pillar, schema. Returns ok, findings, statement."""
    from governance_certification.verify import verify
    return verify(envelope, verify_sig=_verifier(public_key_pem))


@tool("norm-freshness", "norm_freshness.assess")
def norm_freshness(pins: list[dict[str, Any]], observed: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Per-rule freshness. pins = [{rule_id, source?: {uri, version, fragment?}}]; observed = {uri or uri#fragment: {current_version, change_kind?: editorial|amendment|commencement|repeal|unknown, observed_at?}}."""
    import norm_freshness as nf
    rp = [nf.RulePin(str(p["rule_id"]), nf.SourceRef(str(p["source"]["uri"]), str(p["source"]["version"]), p["source"].get("fragment"))
                     if p.get("source") else None) for p in pins]
    obs = {str(k): nf.SourceState(str(v.get("uri", k.split("#")[0])), v.get("current_version"),
                                  enum_of(nf.ChangeKind, v["change_kind"]) if v.get("change_kind") is not None else None,
                                  v.get("observed_at")) for k, v in observed.items()}
    return nf.assess(rp, obs)


@tool("obligation-discharge", "obligation_discharge.admit")
def obligation_admit(obligations: list[dict[str, Any]], declaration: dict[str, Any]) -> dict[str, Any]:
    """May an enforcement point act on a permit carrying duties? obligations = [{id, type, mandatory?, deadline_s?}]; declaration = {pep, supports: [..], unsupported?: [..]}."""
    import obligation_discharge as od
    obs = [od.Obligation(str(o["id"]), str(o["type"]), bool(o.get("mandatory", True)), o.get("deadline_s")) for o in obligations]
    decl = od.Declaration(str(declaration["pep"]), frozenset(declaration.get("supports") or ()), frozenset(declaration.get("unsupported") or ()))
    adm = od.admit(obs, decl)
    return {"status": adm.status, "may_permit": adm.may_permit, "blocking": adm.blocking, "owed": adm.owed,
            "determinations": adm.determinations, "pep": adm.pep, "detail": adm.detail}


@tool("effect-reconciliation", "effect_reconciliation.reconcile")
def effect_reconcile(auths: list[dict[str, Any]], effects: Optional[list[dict[str, Any]]], since: str, until: str,
                     match_window_s: float = 0.0) -> dict[str, Any]:
    """Join an authorisation ledger [{id, action, subject, at}] with an effect ledger [{id, action, subject, at, authorisation_id?}] over [since, until]. effects = null -> UNRECONCILED."""
    import effect_reconciliation as er
    a = [er.Authorisation(str(x["id"]), str(x["action"]), str(x["subject"]), str(x["at"])) for x in auths]
    e = None if effects is None else [er.Effect(str(x["id"]), str(x["action"]), str(x["subject"]), str(x["at"]), x.get("authorisation_id")) for x in effects]
    r = er.reconcile(a, e, since=since, until=until, match_window_s=match_window_s)
    return {"status": r.status, "matched": r.matched, "authorised_not_observed": r.authorised_not_observed,
            "observed_not_authorised": r.observed_not_authorised, "duplicated": r.duplicated, "detail": r.detail,
            "unauthorised_rate": r.unauthorised_rate, "binding_rate": r.binding_rate}


def _posture(d: dict[str, Any]) -> Any:
    import enforcement_posture as ep
    controls = tuple(ep.Control(str(c["name"]), bool(c["enabled"]), c.get("mode"), c.get("quantity"), bool(c.get("weakens_when_enabled", False)))
                     for c in d.get("controls") or ())
    return ep.Posture(str(d["engine"]), controls, str(d["effective_from"]), d.get("effective_to"))


@tool("enforcement-posture", "enforcement_posture.compare")
def enforcement_compare(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Partial-order comparison of two postures {engine, controls: [{name, enabled, mode?, quantity?, weakens_when_enabled?}], effective_from, effective_to?}: unchanged, hardened, weakened, incomparable."""
    import enforcement_posture as ep
    return {"change": ep.compare(_posture(a), _posture(b))}


@tool("5d-nd", "five_d_nd.canonicalize / digest / validate")
def nd_digest(ref: dict[str, Any]) -> dict[str, Any]:
    """Canonical bytes and sha256 digest of a 5d+nd reference {dimensions: [..], anchor}; valid=false on an unknown dimension."""
    import five_d_nd as nd
    return {"scheme": nd.SCHEME, "ref": ref, "valid": nd.validate(ref), "canonical": nd.canonicalize(ref), "digest": nd.digest(ref)}


@tool("loomground-audit-chain", "mutation_log.MutationLog.verify_chain / pillar.intact_attestation")
def audit_chain_verify(folder: str, log_root: Optional[str] = None, subject: str = "", entry_ref: str = "") -> dict[str, Any]:
    """Walk a folder's append-only log: hash links, Ed25519 signatures, purge tombstones, the head anchor, the
    key pin. `log_root` defaults to the plane's own (`RVND_LOG_ROOT`, else `~/.workspace/log`). Returns the
    verification (`ok`, counts, `broken_links`, `signature_failures`, …), `head_hash`, `count`, and the `intact`
    pillar attestation for `subject` (default: the folder id) that a certification cites. Verification reads the
    host identity key under `WORKSPACE_KEY_DIR` and mints one there when the host has none."""
    ac = import_plane("loomground_audit_chain")
    log = ac.MutationLog(folder, log_root=log_root)
    verification = log.verify_chain()
    return {"folder_id": log.folder_id, "count": log.count(), "head_hash": log.head_hash(),
            "verification": verification,
            "intact": ac.intact_attestation(verification, subject=subject or log.folder_id, entry_ref=entry_ref)}


TOOLS = [oversight_issue, oversight_verify, govcert_verify, norm_freshness, obligation_admit, effect_reconcile,
         enforcement_compare, nd_digest, audit_chain_verify]
