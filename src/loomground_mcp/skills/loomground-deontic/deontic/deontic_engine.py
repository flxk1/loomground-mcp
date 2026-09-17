#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""A self-contained implementation of the deontic language, bundled with the skill.

Stdlib-only. It realises the language surface — parse, validate, project, render,
the Hohfeld incident classifier, the claim-right constructor, and candidate-
conflict flagging — so a norm can be machine-validated wherever the skill runs,
without installing the `deontic` package. It imports no product code; a companion
drift gate (`tools/check_companion.py`) conformance-checks it against the published
vectors so it cannot go stale.

The language it implements: three modalities O/P/F (one primitive, F≡O¬, P≡¬O¬),
the eight Hohfeld incidents, and a canonical statement grammar. It never infers,
schedules, or resolves — it transcribes and flags.
"""
from __future__ import annotations

import re
from typing import Any

OPERATORS = ("O", "P", "F")
GLOSS = {"O": "obligatory", "P": "permitted", "F": "forbidden"}
# A surface "right" reduces to a P (liberty) for the holder; a claim-right is the
# counterparty's O and is built with claim_right(), not this map.
MODAL_TO_OP = {"obligation": "O", "permission": "P", "prohibition": "F", "right": "P"}

# classify_incident keys on the canonical surface modal, so a formula's incident
# must be read from its resolved operator, not the raw input modal. A negated
# phrase ("must not") resolves to F but is not a modal classify_incident knows;
# passing it through left the prohibition's incident unclassified. Map the
# operator back to the modal the classifier expects.
_OP_TO_MODAL = {"O": "obligation", "P": "permission", "F": "prohibition"}

# A negated modal ("must not", "shall not", "may not", "cannot", "is not permitted
# to") denotes a prohibition, not a duty: mapping it to the O fallback would invert
# the norm's force. Recognise it as F. "need not" (a release from duty) and bare
# "will/would not" are deliberately excluded — they fail closed instead of F.
_NEGATED_MODAL = re.compile(
    r"\b(?:"
    r"cannot"
    r"|(?:must|shall|may)\s+(?:not|never)"
    r"|can\s+not"
    r"|not\s+(?:be\s+)?(?:permitt\w*|allow\w*|entitl\w*|authoris\w*|authoriz\w*|"
    r"free|at\s+liberty)"
    r"|no\s+(?:right|permission|liberty)\b"
    r"|prohibit\w*|forbid\w*|forbidden|barred|proscrib\w*|preclud\w*|enjoin\w*"
    r")", re.I)

INCIDENTS = ("claim", "duty", "privilege", "no-right",
             "power", "liability", "immunity", "disability")
_CORRELATIVE = {"claim": "duty", "duty": "claim", "privilege": "no-right",
                "no-right": "privilege", "power": "liability", "liability": "power",
                "immunity": "disability", "disability": "immunity"}

_POWER_VERBS = re.compile(
    r"\b(?:terminat\w*|rescind\w*|revoke\w*|withdraw\w*|waive\w*|consent\w*|"
    r"approv\w*|authoris\w*|authoriz\w*|assign\w*|renew\w*|exercis\w*|elect\w*|"
    r"suspend\w*|instruct\w*|k(?:ü|u)ndig\w*|widerruf\w*|zur(?:ü|u)cktret\w*|"
    r"verzicht\w*|zustimm\w*|genehmig\w*|abtret\w*|verl(?:ä|a)nger\w*|"
    r"aus(?:ü|u)b\w*|anweis\w*)\b", re.I)
_IMMUNITY_CUES = re.compile(
    r"\b(?:not\s+be\s+(?:varied|amended|modified|assigned)|"
    r"nicht\s+(?:ge(?:ä|a)ndert|abgetreten|(?:ü|u)bertragen)\s+werden)\b", re.I)

_COND = re.compile(r"^\s*if\s*\[(?P<cond>.*?)\]\s*then\s+", re.S | re.I)
_EXC = re.compile(r"\s+unless\s*\[(?P<exc>.*?)\]\s*$", re.S | re.I)
_CORE = re.compile(
    r"^\s*(?P<op>[A-Za-z]+)\s*\(\s*(?P<bearer>[^():]+?)\s*:\s*(?P<action>[^()]+?)\s*\)\s*$",
    re.S)


class DeonticSyntaxError(ValueError):
    """A statement string does not conform to the deontic grammar."""


def correlative(incident: str) -> str:
    return _CORRELATIVE.get(incident, "")


def classify_incident(modal: str, action: str, raw: str) -> str:
    """The incident borne by the norm-addressee; abstains ('') when unsure."""
    blob = f"{action} {raw}"
    if modal == "obligation":
        return "duty"
    if modal == "prohibition":
        if _IMMUNITY_CUES.search(blob):
            return "immunity"
        if _POWER_VERBS.search(blob):
            return "disability"
        return "duty"
    if modal in ("permission", "right"):
        return "power" if _POWER_VERBS.search(blob) else "privilege"
    return ""


def _formula(operator, bearer, action, *, condition="", exception="",
             negated=False, incident="", counterparty="") -> dict[str, Any]:
    return {"operator": operator, "bearer": bearer, "action": action,
            "condition": condition, "exception": exception, "negated": negated,
            "incident": incident, "counterparty": counterparty}


def formula_from_fields(modal, subject, action, *, condition="", exception="",
                        raw_sentence="", counterparty="") -> dict[str, Any]:
    """Build a formula from a norm's primitive fields, classifying its incident.

    A negated modal lowers to F; an unrecognised, non-negated modal fails closed
    (raises) rather than silently becoming an obligation.
    """
    op = MODAL_TO_OP.get(modal)
    if op is None:
        if _NEGATED_MODAL.search(modal or ""):
            op = "F"
        else:
            raise ValueError(
                f"unrecognised deontic modal: {modal!r}; expected one of "
                f"{sorted(MODAL_TO_OP)} or a negated modal (e.g. 'must not')")
    incident = classify_incident(_OP_TO_MODAL.get(op, modal), action or "", raw_sentence or "")
    return _formula(op, subject or "(unspecified)", action or "(unspecified)",
                    condition=condition, exception=exception,
                    incident=incident, counterparty=counterparty)


def claim_right(holder, action, obligor, *, condition="", exception="") -> dict[str, Any]:
    """A claim-right modeled as its correlative duty: O(obligor : action)."""
    return _formula("O", obligor or "(unspecified)", action or "(unspecified)",
                    condition=condition, exception=exception,
                    incident="duty", counterparty=holder)


def parse(source: str) -> dict[str, Any]:
    """Parse a canonical statement into a structured formula dict."""
    if not isinstance(source, str) or not source.strip():
        raise DeonticSyntaxError("empty statement")
    rest, condition, exception = source, "", ""
    m = _COND.match(rest)
    if m:
        condition = m.group("cond").strip()
        rest = rest[m.end():]
    m = _EXC.search(rest)
    if m:
        exception = m.group("exc").strip()
        rest = rest[:m.start()]
    m = _CORE.match(rest)
    if not m:
        raise DeonticSyntaxError(f"not a deontic core 'OP(bearer : action)': {rest!r}")
    op = m.group("op")
    if op not in OPERATORS:
        raise DeonticSyntaxError(f"unknown operator {op!r} (not in {OPERATORS})")
    bearer, action = m.group("bearer").strip(), m.group("action").strip()
    negated = action.startswith("¬")
    if negated:
        action = action[1:].strip()
    if not bearer:
        raise DeonticSyntaxError("empty bearer")
    if not action:
        raise DeonticSyntaxError("empty action")
    return _formula(op, bearer, action, condition=condition, exception=exception, negated=negated)


def validate(formula: dict[str, Any]) -> dict[str, Any]:
    errors = []
    if formula.get("operator") not in OPERATORS:
        errors.append(f"unknown operator: {formula.get('operator')!r}")
    if not str(formula.get("bearer", "")).strip():
        errors.append("empty bearer")
    if not str(formula.get("action", "")).strip():
        errors.append("empty action")
    if formula.get("incident") and formula["incident"] not in INCIDENTS:
        errors.append(f"unknown incident: {formula['incident']!r}")
    return {"ok": not errors, "errors": errors}


def project(formula: dict[str, Any]) -> dict[str, Any]:
    return {k: formula.get(k, "") if k not in ("negated",) else bool(formula.get("negated", False))
            for k in ("operator", "bearer", "action", "condition", "exception",
                      "negated", "incident", "counterparty")}


def render(formula: dict[str, Any]) -> str:
    act = f"¬ {formula['action']}" if formula.get("negated") else formula["action"]
    s = f"{formula['operator']}({formula['bearer']} : {act})"
    if formula.get("condition"):
        s = f"if [{formula['condition']}] then {s}"
    if formula.get("exception"):
        s = f"{s} unless [{formula['exception']}]"
    return s


def detect_conflicts(formulae: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flag incompatible truth values over the same bearer and unsigned action."""
    def key(s):
        return " ".join((s or "").lower().split())
    def modal_truth(formula):
        truth = not bool(formula.get("negated", False))
        return not truth if formula["operator"] == "F" else truth
    out = []
    for i in range(len(formulae)):
        for j in range(i + 1, len(formulae)):
            a, b = formulae[i], formulae[j]
            if key(a["bearer"]) != key(b["bearer"]) or key(a["action"]) != key(b["action"]):
                continue
            both_permissions = a["operator"] == b["operator"] == "P"
            if not both_permissions and modal_truth(a) != modal_truth(b):
                out.append({"kind": "deontic-conflict", "bearer": a["bearer"],
                            "action": a["action"], "operator_a": a["operator"],
                            "operator_b": b["operator"], "resolution": "candidate-escalate"})
    return out
