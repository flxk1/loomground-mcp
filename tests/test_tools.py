# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""One in-process test per tool, through the mcp client."""
import asyncio
import base64
import json
import sys

import pytest
from mcp import Client

from conftest import PATCH, SOLVER_SAMPLES, TRANSPORT, call
from loomground_mcp import build_server
from loomground_mcp.tools import ALL

AHEAD_OF_CATALOGUE: set[str] = set()


def test_lists_every_tool_with_plane_and_function():
    async def go():
        async with Client(build_server()) as client:
            return (await client.list_tools()).tools
    tools = asyncio.run(go())
    assert len(tools) == len(ALL) == 55
    assert all(t.description.startswith("[") and " · " in t.description for t in tools)
    assert "patch_lg" in next(t for t in tools if t.name == "solver_evaluate").input_schema["properties"]
    assert tools[0].name == "loomground_catalogue"


# the family catalogue

def test_loomground_catalogue():
    env = call("loomground_catalogue")
    r = env["result"]
    assert env["plane"] == "loomground" and set(r) == {"repos", "pipeline", "patch_from_documents", "source"}
    assert r["source"] == {"repo": "https://github.com/flxk1/loomground", "commit": "91a0bbee2d8b2520cee8e1d2e5fc9928084d79f4"}
    names = [x["repo"] for x in r["repos"]]
    assert len(names) == 41 and names[0] == "loomground" and "loomground-mcp" in names
    assert {"repo", "family", "role", "description", "pipeline_position", "depends_on", "tools", "skills", "install", "url"} == set(r["repos"][0])
    assert [s["stage"] for s in r["pipeline"]][:3] == ["ingest", "versum", "solver"]
    assert [s["tool"] for s in r["patch_from_documents"]] == ["ingest_text", "versum_index", "norm_extract", "deontic_parse", None, "solver_evaluate"]
    catalogued, served = {t for x in r["repos"] for t in x["tools"]}, {t.__name__ for t in ALL}
    assert served - catalogued == AHEAD_OF_CATALOGUE and not catalogued - served
    by_tool = call("loomground_catalogue", {"query": "SOLVER_EVALUATE"})["result"]
    assert [x["repo"] for x in by_tool["repos"]] == ["loomground-solver"] and len(by_tool["pipeline"]) == len(r["pipeline"])
    by_family = call("loomground_catalogue", {"query": "standard/language"})["result"]["repos"]
    assert by_family and all(x["family"] == "Standard/language planes" for x in by_family)
    assert call("loomground_catalogue", {"query": "no-such-thing"})["result"]["repos"] == []


def test_loomground_releases():
    env = call("loomground_releases")
    r = env["result"]
    assert env["plane"] == "loomground" and set(r) == {"generated", "repos", "edges", "accepted", "skipped", "source"}
    assert r["source"] == {"repo": "https://github.com/flxk1/loomground", "commit": "91a0bbee2d8b2520cee8e1d2e5fc9928084d79f4"}
    assert len(r["repos"]) == 41 and len(r["edges"]) == 77 and len(r["accepted"]) == 17 and r["skipped"] == []
    assert sum(1 for x in r["repos"].values() if x["tag"]) == 34 and all(set(x) == {"version", "tag", "commit", "package", "pypi", "family", "tools", "skills"} for x in r["repos"].values())
    d = r["repos"]["loomground-deontic"]
    assert d["package"] == "loomground-deontic" and d["family"] == "Standard/language planes" and d["skills"] == ["deontic"]
    assert d["tag"] == f"loomground-deontic-v{d['version']}" and len(d["commit"]) == 40 and d["pypi"] is False
    assert r["repos"]["loomground-mcp"]["tag"] is None and r["repos"]["loomground-mcp"]["commit"] is None
    assert all(set(e) == {"consumer", "dependency", "range", "dev_pin", "dev_pin_release", "status"} for e in r["edges"])
    assert {e["status"] for e in r["edges"]} <= {"release", "unreleased-commit", "out-of-range", "missing-range"}
    one = call("loomground_releases", {"repo": "loomground-mcp"})["result"]
    assert set(one) == {"repo", "record", "edges", "accepted", "source"} and one["record"] == r["repos"]["loomground-mcp"]
    assert len(one["edges"]) == 31 and all(e["consumer"] == "loomground-mcp" for e in one["edges"])
    both = call("loomground_releases", {"repo": "loomground-solver"})["result"]["edges"]
    assert len(both) == 12 and {e["consumer"] == "loomground-solver" for e in both} == {True, False}
    env = call("loomground_releases", {"repo": "no-such-repo"})
    assert env["unavailable"] and "no-such-repo" in env["reason"]


# versum

def test_versum_index(policy_folder):
    env = call("versum_index", {"folder": policy_folder, "profile": "law-eu"})
    assert env["ok"] and env["plane"] == "loomground-versum"
    assert env["result"]["n_sources"] == 1 and env["result"]["n_claims"] == 3


def test_versum_claims(policy_folder):
    assert call("versum_claims", {"folder": policy_folder})["unavailable"] is True  # before indexing: no claims.csv
    call("versum_index", {"folder": policy_folder, "profile": "law-eu"})
    env = call("versum_claims", {"folder": policy_folder, "limit": 2})
    rows = env["result"]["rows"]
    assert env["result"]["n_total"] == 3 and len(rows) == 2
    assert {"span_start", "span_end", "marker", "text", "source_urn"} <= set(rows[0])
    assert isinstance(rows[0]["span_start"], int)


def test_versum_search(policy_folder):
    call("versum_index", {"folder": policy_folder, "profile": "law-eu"})
    env = call("versum_search", {"folder": policy_folder, "query": "transfer personal data outside the EU", "k": 1})
    hit = env["result"]["hits"][0]
    assert env["result"]["layout"] == "index" and "must not transfer" in hit["snippet"]
    assert hit["span_start"] == 78 and hit["span_end"] == 139
    env = call("versum_search", {"folder": policy_folder, "query": "invoices", "filters": {"modality": "permitted"}})
    assert [h["snippet"] for h in env["result"]["hits"]] == ["The operator may retain invoices for ten years."]


def test_versum_capture(policy_folder, tmp_path):
    src = tmp_path / "inbox"; src.mkdir()
    (src / "policy.md").write_text("The controller must notify the authority within 72 hours.\n", encoding="utf-8")
    env = call("versum_capture", {"folder": policy_folder, "source_path": str(src / "policy.md"), "profile": "law-eu"})
    r = env["result"]
    assert env["ok"] and r["status"] == "admitted" and r["claim_count"] == 1 and r["urn"].startswith("urn:")
    assert r["index"]["n_sources"] == 2  # policy.txt already in the folder + the admitted source
    again = call("versum_capture", {"folder": policy_folder, "source_path": str(src / "policy.md"), "profile": "law-eu"})
    assert again["result"]["status"] == "duplicate" and again["result"]["admitted"] is False
    (src / "table.csv").write_text("a,b\n", encoding="utf-8")
    bad = call("versum_capture", {"folder": policy_folder, "source_path": str(src / "table.csv")})
    assert bad["ok"] is False and bad["error"]["type"] == "CaptureError"


def test_versum_suggest(corpus_folder):
    assert call("versum_suggest", {"folder": corpus_folder})["unavailable"] is True
    call("versum_index", {"folder": corpus_folder, "profile": "law-eu"})
    env = call("versum_suggest", {"folder": corpus_folder, "min_sources": 2})
    r = env["result"]
    assert r["n_suggested_concepts"] >= 1 and r["cross_source"] >= 1
    cand = next(c for c in r["candidates"] if c["concept_id"] == "personal-data")
    assert cand["n_sources"] == 2 and cand["seed"] == "definition"
    assert call("versum_suggest", {"folder": corpus_folder, "min_sources": 3})["result"]["candidates"] == []


def test_versum_confirm(corpus_folder):
    call("versum_index", {"folder": corpus_folder, "profile": "law-eu"})
    assert call("versum_confirm", {"folder": corpus_folder})["unavailable"] is True  # no queue yet
    call("versum_suggest", {"folder": corpus_folder})
    env = call("versum_confirm", {"folder": corpus_folder, "min_sources": 2})
    assert env["result"]["concept_ids"] == ["personal-data"] and env["result"]["n_edges"] >= 2
    import os
    assert os.path.isfile(os.path.join(corpus_folder, ".versum", "concepts.csv"))
    none = call("versum_confirm", {"folder": corpus_folder, "concept_ids": ["not-a-concept"]})
    assert none["result"] == {"n_concepts": 0, "n_edges": 0, "concept_ids": []}


def test_versum_canon(corpus_folder, tmp_path):
    assert call("versum_canon", {"folder": corpus_folder})["unavailable"] is True
    call("versum_index", {"folder": corpus_folder, "profile": "law-eu"})
    env = call("versum_canon", {"folder": corpus_folder})
    r = env["result"]
    assert r["layout"] == "index" and r["n_sources"] == 2 and r["n_concepts"] >= 1
    import csv, os
    kg = tmp_path / "kg" / "by-domain" / "dom-a"; kg.mkdir(parents=True)
    cols = ["canonical_urn", "library", "item_id", "source_urn", "text", "polarity", "predicate", "modality", "quantification"]
    with (kg / "claims.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
        w.writerow(dict(zip(cols, ["urn:x:1", "lib", "i1", "urn:x:1", "A 'processor' duty.", "N", "obligation", "req", "null"])))
        w.writerow(dict(zip(cols, ["urn:x:2", "lib", "i2", "urn:x:2", "The 'processor' duty recurs.", "N", "obligation", "req", "null"])))
    env = call("versum_canon", {"folder": str(tmp_path / "kg")})
    assert env["result"]["layout"] == "kg" and env["result"]["n_domains"] == 1 and env["result"]["n_concepts"] == 1
    assert os.path.isfile(tmp_path / "kg" / "canon.json")
    assert call("versum_canon", {"folder": str(kg)})["result"]["layout"] == "domain"


# deontic

def test_deontic_parse():
    env = call("deontic_parse", {"statement": "if [the contract has ended] then O(operator : delete personal data) unless [a legal hold applies]"})
    r = env["result"]
    assert env["plane"] == "loomground-deontic" and r["operator"] == "O" and r["bearer"] == "operator"
    assert r["condition"] == "the contract has ended" and r["exception"] == "a legal hold applies" and r["negated"] is False
    assert r["formula"] == "if [the contract has ended] then O(operator : delete personal data) unless [a legal hold applies]"
    assert r["round_trip"] is True and r["validation"] == {"ok": True, "errors": []}
    bad = call("deontic_parse", {"statement": "the operator should probably delete data"})
    assert bad["ok"] is False and bad["error"]["type"] == "DeonticSyntaxError"


def test_deontic_conflicts():
    env = call("deontic_conflicts", {"statements": ["O(operator : transfer personal data)",
                                                    "F(operator : transfer personal data)",
                                                    "P(operator : retain invoices)"]})
    r = env["result"]
    assert r["n_statements"] == 3 and len(r["candidates"]) == 1
    c = r["candidates"][0]
    assert c["predicate"] == "may-conflict-with" and c["resolution"] == "candidate-escalate"
    assert (c["operator_a"], c["operator_b"]) == ("O", "F") and c["action"] == "transfer personal data"


# applied skill runtimes

def test_policy_compile_and_check():
    text = "The operator must delete expired records."
    compiled = call("policy_compile", {"policy": text})
    assert compiled["ok"] and compiled["plane"] == "policy-compiler"
    assert compiled["result"]["draft"]["norms"][0]["operator"] == "O"
    assert compiled["result"]["grounding_seam"]["norms"][0]["bearer"] == "operator"
    checked = call("policy_check", {"policy": text, "cases": [
        {"actor": "operator", "action": "delete expired records", "expect": "obligatory"},
    ]})
    assert checked["result"]["ok"] and checked["result"]["passed"] == 1


def test_evidence_emit_and_verify():
    subject = {
        "id": "msg-001", "ts": "2026-09-12T10:00:00Z",
        "from_": {"actor": "compliance", "role": "policy-compliance"},
        "to": {"actor": "maker", "role": "maker"},
        "verb": "issue-directive", "body": {"instruction": "hold", "kind": "write"},
        "authority": {"basis": "role", "role": "policy-compliance", "reserved": False},
        "protocol": "a2a-compliance/0.1",
    }
    emitted = call("evidence_emit", {"subject": subject, "issued_at": "2026-09-12T10:00:00Z"})
    assert emitted["ok"] and emitted["result"]["signer_production"] is False
    verified = call("evidence_verify", {"envelope": emitted["result"]["envelope"]})
    assert verified["result"]["ok"] and verified["result"]["signer_production"] is False


def test_privacy_scan_text(tmp_path):
    env = call("privacy_scan", {
        "text": "Contact Ada at ada@example.com.", "mode": "regex_only",
        "audit_log_path": str(tmp_path / "privacy.jsonl"),
    })
    doc = env["result"]["documents"][0]
    assert env["ok"] and doc["pii_detected"] and "ada@example.com" not in doc["overlay"]
    # force_text=True, so the walk never runs: walk_errors stays empty whatever its
    # element type upstream, which is why the List[str] -> List[WalkError] change in
    # 2.0.0 is invisible here. Asserted so a future directory-scan path has to notice.
    assert env["result"]["walk_errors"] == [] and env["result"]["document_count"] == 1


@pytest.mark.parametrize("mode", ["standard", "local_only", "anonymous_json", "regex_only"])
@pytest.mark.parametrize("redaction_mode", ["redact", "block", "detect_only", "pseudonymize"])
def test_privacy_scan_envelope_carries_no_original_value(mode, redaction_mode):
    """No accepted mode combination puts an original in the envelope. Every mode, because
    the two that broke this were not the default: `SpanFinding.value`/`.context` ride one
    dataclass-reflection from the wire, and `overlay` IS the untouched original under
    detect_only (nothing redacts) and block (when the redactor refuses) — while egress_allowed
    stays true, since the gate rules on the source class, not the residual. A test over
    `redact` alone, or over `overlay` alone, stays green through both."""
    secrets = ("ada@example.com", "DE89370400440532013000")
    env = call("privacy_scan", {"text": f"Ada: {secrets[0]} IBAN {secrets[1]}",
                                "mode": mode, "redaction_mode": redaction_mode})
    assert env["ok"] and env["result"]["documents"][0]["pii_detected"]
    blob = json.dumps(env, ensure_ascii=False)
    assert not [s for s in secrets if s in blob], f"{mode}/{redaction_mode} egressed the original"


def _scan_takes_a_hash_salt() -> bool:
    """Whether the installed privacy-shield threads hash_salt to its redactor. 2.0.0 does
    not, and the range admits it, so the reachable half of the contract is asserted
    unconditionally and the working half only where the plumbing exists."""
    import inspect
    try:
        from privacy_shield.runner import scan
    except ImportError:
        return False
    return "hash_salt" in inspect.signature(scan).parameters


def test_hash_without_a_salt_fails_closed():
    """True on every version: the redactor refuses to invent a salt, and neither does
    this wrapper — an invented one is unstable per call or a lookup of the value."""
    env = call("privacy_scan", {"text": "Ada: ada@example.com", "mode": "regex_only",
                                "redaction_mode": "hash"})
    assert env["ok"] is False and "result" not in env
    assert "hash_salt" in json.dumps(env)


@pytest.mark.skipif(not _scan_takes_a_hash_salt(),
                    reason="installed privacy-shield does not thread hash_salt (<= 2.0.0)")
def test_hash_with_a_salt_redacts_and_is_salt_dependent():
    salt = "a" * 64
    def overlay(s):
        env = call("privacy_scan", {"text": "Ada: ada@example.com", "mode": "regex_only",
                                    "redaction_mode": "hash", "hash_salt": s})
        assert env["ok"], env
        doc = env["result"]["documents"][0]
        assert "ada@example.com" not in json.dumps(env, ensure_ascii=False)
        assert doc["overlay"] is not None and "overlay_withheld" not in doc
        return doc["overlay"]
    assert "[SHA:" in overlay(salt)
    assert overlay(salt) == overlay(salt) and overlay(salt) != overlay("b" * 64)


def test_privacy_scan_withholds_an_uncleaned_overlay():
    """detect_only produces no redaction, so the overlay is withheld rather than returned:
    the span metadata still answers "is there PII here", which is what the mode is for."""
    env = call("privacy_scan", {"text": "Ada: ada@example.com", "mode": "regex_only",
                                "redaction_mode": "detect_only"})
    doc = env["result"]["documents"][0]
    assert doc["overlay"] is None and "not a cleaned overlay" in doc["overlay_withheld"]
    assert doc["pii_detected"] and doc["span_count"] >= 1
    clean = call("privacy_scan", {"text": "Ada: ada@example.com", "mode": "regex_only"})
    kept = clean["result"]["documents"][0]
    assert kept["overlay"] == "Ada: [EMAIL]" and "overlay_withheld" not in kept


def test_a2a_ground_is_derivation_only():
    env = call("a2a_ground", {"context": {"maker_id": "maker-1"}, "planes": []})
    assert env["ok"] and env["result"]["recommended_action"] == "no-steer"
    assert env["result"]["findings"] == [] and env["result"]["directive"] is None
    assert call("deontic_conflicts", {"statements": ["O(a : x)", "F(a : ¬ x)"]})["result"]["candidates"] == []


def test_a2a_plan_consumes_full_family_surface_without_dispatch():
    env = call("a2a_plan", {
        "context": {"maker_id": "maker-1"},
        "target_kind": "edit",
        "governance": {"actions": [{"kind": "edit"}], "obligations": ["record_effects"]},
        "planes": [],
    })
    result = env["result"]
    plan = result["plan"]
    assert env["ok"] and result["dispatch_performed"] is False
    assert result["inventory_source"] == "loomground-mcp published surface"
    assert len(plan["repository_coverage"]) == 41
    assert len(plan["steps"]) == 8
    assert plan["missing_required"] == []
    assert plan["ready"] is True


def test_a2a_plan_respects_maker_boundary():
    env = call("a2a_plan", {
        "context": {"maker_id": "maker-1"},
        "target_kind": "push",
        "governance": {"actions": [{"kind": "edit"}], "prohibited": ["push"]},
        "planes": [],
    })
    assert env["result"]["plan"]["ready"] is False
    assert env["result"]["plan"]["disposition"] == "refuse"


def test_a2a_admission_preview_fails_closed_without_stage_receipts():
    env = call("a2a_admission_preview", {
        "context": {"maker_id": "maker-1", "proposed_action": {
            "bearer": "maker-1", "action": "edit module X"}},
        "target_kind": "edit",
        "governance": {"actions": [{"kind": "edit"}]},
        "planes": [],
        "receipts": [],
    })
    preview = env["result"]["preview"]
    assert env["ok"] and preview["state"] == "ROUTED_HUMAN"
    assert len(preview["missing_receipts"]) == 22
    assert preview["dispatch_performed"] is False
    assert env["result"]["dispatch_performed"] is False


def test_a2a_reconcile_cannot_certify_without_prior_admission():
    planned = call("a2a_plan", {
        "context": {"maker_id": "maker-1"}, "target_kind": "edit",
        "governance": {"actions": [{"kind": "edit"}]}, "planes": [],
    })["result"]["plan"]
    env = call("a2a_reconcile", {
        "context": {"maker_id": "maker-1"}, "target_kind": "edit",
        "governance": {"actions": [{"kind": "edit"}]}, "planes": [],
        "preflight_receipts": [], "postflight_receipts": [],
        "control_receipt": {
            "action_digest": planned["action_digest"],
            "dispatch_id": "dispatch-1", "observed_effects_digest": "effects-1",
        },
    })
    result = env["result"]["reconciliation"]
    assert env["ok"] and result["state"] == "ROUTED_HUMAN"
    assert result["certified"] is False
    assert result["invalid_receipts"] == ["enforcement-preview:not-admitted"]


# the four reader/writer languages

def test_factual_lower():
    env = call("factual_lower", {"sentence": "The operator is a controller."})
    r = env["result"]
    assert env["plane"] == "loomground-factual" and r == {"subject": "operator", "predicate": "is", "object": "controller",
                                                          "dimension": "structural", "negated": False, "quantification": "existential"}
    assert call("factual_lower", {"sentence": "A processor is not a controller."})["result"]["negated"] is True
    none = call("factual_lower", {"sentence": "The operator deletes the data."})
    assert none["ok"] is False and none["unavailable"] is True and "copula" in none["reason"]


def test_epistemic_extract():
    env = call("epistemic_extract", {"sentence": "The controller knows that the data is inaccurate."})
    r = env["result"]
    assert env["plane"] == "loomground-epistemic" and (r["operator"], r["holder"], r["certainty"]) == ("K", "controller", "certain")
    assert r["proposition"] == "the data is inaccurate" and r["system_id"] == "system:epistemic"
    r = call("epistemic_extract", {"sentence": "According to the audit, the processor believes the transfer was lawful."})["result"]
    assert r["operator"] == "B" and r["certainty"] == "probable" and r["source"]
    none = call("epistemic_extract", {"sentence": "The controller deletes the data."})
    assert none["ok"] is False and none["unavailable"] is True


def test_norm_extract():
    env = call("norm_extract", {"text": ("The operator must delete personal data within 30 days after the contract ends. "
                                         "The operator shall delete personal data unless a legal hold applies. "
                                         "Der Anbieter darf keine personenbezogenen Daten weitergeben.")})
    r = env["result"]
    assert env["plane"] == "loomground-norm" and r["n_rules"] == 3 and r["languages_detected"] == ["de", "en"]
    first, second, third = r["rules"]
    assert first["rule"]["modal"] == "obligation" and first["rule"]["subject"] == "the operator"
    assert first["formula"] == "O(the operator : delete personal data within 30 days after the contract ends)"
    assert first["formula_fields"]["operator"] == "O" and first["formula_fields"]["formula"] == first["formula"]
    assert second["formula"] == "O(the operator : delete personal data) unless [a legal hold applies]"
    assert third["formula"].startswith("F(der anbieter : ") and third["rule"]["language"] == "de"
    assert call("norm_extract", {"text": "Nothing normative here."})["result"]["n_rules"] == 0
    bad = call("norm_extract", {"text": "x", "language": "xx"})
    assert bad["ok"] is False and bad["error"]["type"] == "ValueError"


TOPOS = """system eu  tradition hybrid  powers separation-extended  levels eu-levels  ranks eu-ranks
organ eu:cjeu  system eu  level eu:supranational  powers {judicial}          # Art 19 TEU
instrument eu:regulation  system eu  rank 1  origin eu:parliament-council  directly-applicable
instrument eu:cjeu-judgment system eu  rank null origin eu:cjeu
level de:federal  system de  rank 0  contains de:land
competence eu:culture  system eu  allocation supporting  holder eu:union
rel eu:regulation  has-primacy-over  de:formal-statute
    [resolution_mode = disapply, basis = "Costa 6/64; Simmenthal 106/77"]
assert de:bverfg : NOT eu:primary-law has-primacy-over de:grundgesetz  [status = contested]
assert a1: eu:directive must-be-transposed-by de:formal-statute [state=gap, deadline=2026-05-01]
"""

BROKEN = """rel de:grundgesetz overrules de:formal-statute
organ de:bundestag system de colour red
rel eu:regulation has-primacy-over
instrument x system eu rank high
treaty eu:teu system eu
rel a outranks b [basis = "unterminated]
"""


def test_topos_parse():
    env = call("topos_parse", {"text": TOPOS})
    r = env["result"]
    assert env["plane"] == "loomground-topos" and r["valid"] is True and r["errors"] == [] and r["n_statements"] == 9
    assert r["counts"] == {"system": 1, "organ": 1, "instrument": 2, "level": 1, "competence": 1, "rel": 1, "assert": 2}
    s = r["statements"]
    assert s[0] == {"kind": "system", "id": "eu", "line": 1, "tradition": "hybrid", "powers": "separation-extended",
                    "levels": "eu-levels", "ranks": "eu-ranks"}
    assert s[1]["powers"] == ["judicial"] and s[1]["level"] == "eu:supranational"
    assert s[2]["directly_applicable"] is True and s[2]["rank"] == 1 and s[3]["rank"] is None
    assert s[4]["rank"] == 0 and s[4]["contains"] == "de:land" and s[5]["allocation"] == "supporting"
    assert s[6] == {"kind": "rel", "line": 7, "from": "eu:regulation", "type": "has-primacy-over", "to": "de:formal-statute",
                    "vocabulary": ["vertical", "coupling"], "props": {"resolution_mode": "disapply", "basis": "Costa 6/64; Simmenthal 106/77"}}
    assert (s[7]["asserted_by"], s[7]["polarity"], s[7]["props"]) == ("de:bverfg", "deny", {"status": "contested"})
    assert (s[8]["asserted_by"], s[8]["polarity"], s[8]["props"]) == ("a1", "affirm", {"state": "gap", "deadline": "2026-05-01"})

    r = call("topos_parse", {"text": BROKEN})["result"]
    assert r["valid"] is False and r["n_statements"] == 0 and [e["line"] for e in r["errors"]] == [1, 2, 3, 4, 5, 6]
    reasons = [e["reason"] for e in r["errors"]]
    assert "unknown relation type 'overrules'" in reasons[0] and "unknown attribute 'colour'" in reasons[1]
    assert "expected an endpoint" in reasons[2] and "'null'" in reasons[3] and "statement keyword" in reasons[4]
    assert reasons[5] == "unterminated string" and all(e["statement"] for e in r["errors"])

    r = call("topos_parse", {"text": "rel a outranks b [state = overdue]"})["result"]
    assert r["valid"] and r["warnings"][0]["line"] == 1 and "overdue" in r["warnings"][0]["reason"]


# solver

def test_solver_evaluate():
    env = call("solver_evaluate", {"patch_lg": PATCH, "transport_json": TRANSPORT})
    r = env["result"]
    assert r["status"] == "escalate" and r["undecided"] == ["t1"]
    assert r["trace"]["evaluation"]["transfer"] == {"verdict": "reserved", "master": "withhold"}
    bad = call("solver_evaluate", {"patch_lg": "gate bad"})
    assert bad["ok"] is False and bad["error"]["type"] == "ApplyError"


def test_solver_verify():
    env = call("solver_verify", {"request_json": {}})
    assert env["plane"] == "loomground-solver" and ("result" in env or "error" in env)
    assert env["ok"] is False or isinstance(env["result"], dict)


def test_solver_manifest():
    env = call("solver_manifest")
    assert env["ok"] and env["result"]["protocol"] and "capabilities" in env["result"]


def _skill(tool):
    env = call(tool, SOLVER_SAMPLES[tool][2])
    assert env["ok"] and env["plane"] == "loomground-solver"
    return env["result"]


def test_solver_analyse_risks():
    r = _skill("solver_analyse_risks")
    assert r["method"] == "pareto" and r["result"]["ranking"] == ["data-breach", "vendor-lock-in", "typo-in-footer"]
    assert r["result"]["scores"]["typo-in-footer"] == 0.0
    over = call("solver_analyse_risks", {"method": "lexicographic", "vectors": {"a": [1, 9], "b": [2, 0]}, "extra": {"order": [1, 0]}})
    assert over["result"]["method"] == "lexicographic" and over["result"]["result"]["choice"] == "a"


def test_solver_estimate_liability():
    r = _skill("solver_estimate_liability")
    assert r["method"] == "bayesian_update" and r["result"]["choice"] == "liable"
    assert r["result"]["scores"] == {"liable": 0.658537, "not-liable": 0.341463}


def test_solver_litigation_risk():
    r = _skill("solver_litigation_risk")
    assert r["method"] == "expected_utility" and r["result"]["choice"] == "settle"
    assert r["result"]["scores"] == {"fight": -8.0, "settle": 20.0}


def test_solver_opponent_model():
    r = _skill("solver_opponent_model")
    assert r["method"] == "expected_utility" and r["result"]["choice"] == "escalate"
    cautious = call("solver_opponent_model", {**SOLVER_SAMPLES["solver_opponent_model"][2], "method": "maximin"})
    assert cautious["result"]["result"]["choice"] == "concede"


def test_solver_probability():
    r = _skill("solver_probability")
    assert r["result"]["scores"]["delay"] == 0.727273 and r["result"]["choice"] == "delay"


def test_solver_strategy():
    r = _skill("solver_strategy")
    assert r["method"] == "minimax_regret" and r["result"]["choice"] == "buy" and r["result"]["scores"] == {"build": 40.0, "buy": 30.0}


def test_solver_advise_addons():
    r = _skill("solver_advise_addons")
    assert r["schema"] == "solver.addon-advice.v1" and r["activation_performed"] is False
    wm, meta = r["recommendations"]
    assert wm["addon"] == "world_model" and wm["recommended"] is True and wm["authorization_required"] is True
    assert meta["addon"] == "metacognition" and meta["eligible"] is False
    bad = call("solver_advise_addons", {"policy": {"world_model": {"mode": "always"}}})
    assert bad["ok"] is False and bad["error"]["type"] == "ValueError"


# ingest

def test_ingest_text():
    from conftest import POLICY
    env = call("ingest_text", {"text": POLICY})
    r = env["result"]
    assert env["ok"] and r["ingester"] == "deontic" and r["nodes"] == 3 and r["edges"] > 0
    assert r["rejections"] == 0 and r["quarantined"] is False
    assert r["subgraphs"][0]["nodes"][0]["operator"] == "O"
    assert call("ingest_text", {"text": PATCH})["unavailable"] is True  # no ingester claims a .lg patch


# operators

def test_collapse():
    env = call("collapse", {"constituents": [{"name": "authority", "state": "PRESENT"},
                                             {"name": "timeliness", "state": "AT_FLOOR"},
                                             {"name": "consent", "state": "UNASSIGNED"}]})
    r = env["result"]
    assert r["overall"] == "open"
    assert r["issues"] == [["authority", "satisfied"], ["timeliness", "not_satisfied"], ["consent", "open"]]


def test_escalation():
    env = call("escalation", {"factors": [{"name": "data-sensitivity", "ceiling": "L2"}, {"name": "jurisdiction", "ceiling": "L3"}],
                              "delegated": "L3", "ladder": ["L0", "L1", "L2", "L3", "L4"], "requested": "L3"})
    r = env["result"]
    assert r["granted"] == "L2" and r["binding"] == ["data-sensitivity"] and r["verdict"] == "not_satisfied"


def test_falsifiability():
    both = call("falsifiability", {"evidence": [{"ref": "run#7", "falsifiability": "SELF_REPORT"},
                                                {"ref": "trace#12", "falsifiability": "OBSERVED_TOOL_CALL"}]})
    alone = call("falsifiability", {"evidence": [{"ref": "run#7", "falsifiability": "SELF_REPORT"}]})
    assert both["result"]["verdict"] == "satisfied" and alone["result"]["verdict"] == "open"


def test_proxy():
    env = call("proxy", {"proxies": [{"metric": "tickets_closed", "stands_for": "customer_problems_solved", "ref": "okr#2"}],
                         "readings": {"tickets_closed": "IMPROVED", "customer_problems_solved": "WORSENED"}})
    sub = env["result"]["substitutions"][0]
    assert sub["kind"] == "gamed" and sub["metric"] == "tickets_closed"


def test_mandate_without_provider_is_unavailable():
    env = call("mandate", {"mandate": {"evidence": {"source_id": "engagement-letter"}, "purposes": ["review"]},
                           "steps": [{"ref": "step-1", "evidence": {"source_id": "log"}, "serves": ["review"]}]})
    assert env["ok"] is False and env["unavailable"] is True and "evidence provider" in env["reason"]


def test_brief():
    assert call("brief")["unavailable"] is True
    env = call("brief", {"premises": [{"name": "assumption", "status": "presupposed"},
                                      {"name": "step-1", "status": "inferred", "depends_on": ["assumption"]},
                                      {"name": "fact", "status": "asserted"}],
                         "space": {"accepted": [], "undecided": ["opt"], "rejected": [], "attacks": []},
                         "divergences": [{"ref": "step-2", "why": "out-of-mandate"}]})
    items = env["result"]["items"]
    assert [i["kind"] for i in items] == ["divergence", "root-presupposition", "unresolved-option"]
    assert items[1]["ref"] == "assumption" and env["result"]["settled_omitted"] == 1


# assurance

CERT = {"id": "oc-1", "action": "data_transfer:t1", "disposition": "decided", "at": "2026-09-09T10:00:00Z",
        "basis": "gdpr-2016-679-art-44",
        "evidence": ["sha256:4da8b3468ad57b8a4e6c6d2a741876e1b3f00eb8c974df29e540c9517e2a88d2"],
        "human": {"id": "dpo-01", "qualification": "dpo"}}


def test_oversight_issue(keypair):
    priv, _ = keypair
    env = call("oversight_issue", {"cert": CERT, "signing_key_pem": priv})
    envelope = env["result"]["envelope"]
    assert envelope["payloadType"] == "application/vnd.oversight-certificate+json" and envelope["signatures"][0]["sig"]
    assert json.loads(base64.b64decode(envelope["payload"]))["action"] == "data_transfer:t1"
    bad = call("oversight_issue", {"cert": {**CERT, "disposition": "decided", "human": None}, "signing_key_pem": priv})
    assert bad["ok"] is False and bad["error"]["type"] == "InvalidCertificate"


def test_oversight_verify(keypair):
    priv, pub = keypair
    envelope = call("oversight_issue", {"cert": CERT, "signing_key_pem": priv})["result"]["envelope"]
    env = call("oversight_verify", {"envelope": envelope, "public_key_pem": pub, "now": "2026-09-09T10:00:01Z"})
    assert env["result"] == {"ok": True, "findings": [], "independence": "undeclared", "canonicalizer": env["result"]["canonicalizer"]}
    tampered = {**envelope, "payload": base64.b64encode(b'{"id":"oc-2"}').decode()}
    assert call("oversight_verify", {"envelope": tampered, "public_key_pem": pub, "now": "2026-09-09T10:00:01Z"})["result"]["ok"] is False


def test_govcert_verify(keypair):
    priv, pub = keypair
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    statement = {"_type": "https://in-toto.io/Statement/v1", "subject": [{"name": "data_transfer:t1", "digest": {"sha256": "00"}}],
                 "predicateType": "https://loomground.org/attestations/GovernanceCertification/v1",
                 "predicate": {"enforced": {"blocked_unless_permitted": False}}}
    payload = json.dumps(statement).encode()
    ptype = "application/vnd.in-toto+json"
    pae = b"DSSEv1 " + str(len(ptype)).encode() + b" " + ptype.encode() + b" " + str(len(payload)).encode() + b" " + payload
    sig = load_pem_private_key(priv.encode(), password=None).sign(pae)
    envelope = {"payloadType": ptype, "payload": base64.b64encode(payload).decode(),
                "signatures": [{"sig": base64.b64encode(sig).decode()}]}
    env = call("govcert_verify", {"envelope": envelope, "public_key_pem": pub})
    r = env["result"]
    assert r["ok"] is False and "not-enforcement-bound" in [f["code"] for f in r["findings"]]
    assert "bad-signature" not in [f["code"] for f in r["findings"]]


def test_norm_freshness():
    env = call("norm_freshness", {"pins": [{"rule_id": "gate.erasure", "source": {"uri": "eli/reg/2016/679", "version": "2016-05-04", "fragment": "art_17"}}],
                                  "observed": {"eli/reg/2016/679": {"current_version": "2027-01-01", "change_kind": "editorial"}}})
    v = env["result"]["verdicts"][0]
    assert v["freshness"] == "editorial-drift" and "2016-05-04" in v["detail"]


def test_obligation_admit():
    env = call("obligation_admit", {"obligations": [{"id": "log-access", "type": "audit", "mandatory": True, "deadline_s": 60}],
                                    "declaration": {"pep": "api-gateway", "supports": ["audit"]}})
    assert env["result"]["status"] == "ADMISSIBLE" and env["result"]["may_permit"] is True


def test_effect_reconcile():
    env = call("effect_reconcile", {
        "auths": [{"id": "a1", "action": "fs.write", "subject": "/out/report.pdf", "at": "2026-03-01T10:00:00Z"}],
        "effects": [{"id": "e1", "action": "fs.write", "subject": "/out/report.pdf", "at": "2026-03-01T10:00:01Z", "authorisation_id": "a1"},
                    {"id": "e2", "action": "fs.write", "subject": "/out/other.pdf", "at": "2026-03-01T10:00:02Z"}],
        "since": "2026-03-01T00:00:00Z", "until": "2026-03-02T00:00:00Z"})
    r = env["result"]
    assert r["status"] == "diverged" and [e["id"] for e in r["observed_not_authorised"]] == ["e2"]


def test_enforcement_compare():
    on = {"engine": "opa", "controls": [{"name": "deny-egress", "enabled": True}], "effective_from": "2026-03-01T00:00:00Z", "effective_to": "2026-03-02T00:00:00Z"}
    off = {"engine": "opa", "controls": [{"name": "deny-egress", "enabled": False}], "effective_from": "2026-03-02T00:00:00Z"}
    assert call("enforcement_compare", {"a": on, "b": off})["result"]["change"] == "weakened"


def test_nd_digest():
    env = call("nd_digest", {"ref": {"dimensions": ["temporal", "relational"], "anchor": "versum://policy/p1#span-150-240"}})
    r = env["result"]
    assert r["valid"] is True and r["digest"] == {"sha256": "4da8b3468ad57b8a4e6c6d2a741876e1b3f00eb8c974df29e540c9517e2a88d2"}
    assert call("nd_digest", {"ref": {"dimensions": ["spooky"], "anchor": "x"}})["result"]["valid"] is False


# the signed audit chain and the runtime controls

LEASE = {"agent": "bot", "granted_grade": "L3", "expires_at": 1000.0}
LANE = {"lane_id": "lane-research", "agent": "bot", "max_grade": "L2", "action_classes": ["summarise"],
        "footprints": ["personal-data"], "approved_by": "alice", "rationale": "bounded research assistant"}


def _append(folder, log_root, *pair_ids, note=""):
    from loomground_audit_chain import LogEvent, MutationLog
    log = MutationLog(folder, log_root=log_root)
    for pair_id in pair_ids:
        log.append(LogEvent(event="ingest", folder_path=folder, pair_id=pair_id, extra={"note": note}))
    return log


def test_audit_chain_verify(chain):
    folder, log_root = chain
    log = _append(folder, log_root, "doc:0", "doc:1", "doc:2")
    env = call("audit_chain_verify", {"folder": folder, "log_root": log_root})
    r = env["result"]
    assert env["plane"] == "loomground-audit-chain" and r["count"] == 3 and r["head_hash"] == log.head_hash()
    assert r["verification"]["ok"] is True and r["verification"]["total_events"] == 3
    assert r["intact"]["verified"] is True and r["intact"]["intact"]["type"] == "native-chain"
    lines = (log.log_file).read_text(encoding="utf-8").splitlines()
    log.log_file.write_text("\n".join(lines[:1] + lines[2:]) + "\n", encoding="utf-8")
    broken = call("audit_chain_verify", {"folder": folder, "log_root": log_root})["result"]
    assert broken["verification"]["ok"] is False and broken["intact"]["verified"] is False
    assert [b["reason"] for b in broken["verification"]["broken_links"]] == ["prev_hash_mismatch"]


def test_lock_text():
    env = call("lock_text", {"text": "mail alex@example.com the project atlas plan", "context": "- project atlas"})
    r = env["result"]
    assert env["plane"] == "loomground-lock" and r["action"] == "refuse" and r["verdict"] == "refused"
    assert [f["tier"] for f in r["findings"]] == ["B", "C"]
    clear = call("lock_text", {"text": "the weather is fine"})["result"]
    assert clear["action"] == "allow" and clear["verdict"] == "auto" and clear["findings"] == []


def test_lane_evaluate():
    inside = call("lane_evaluate", {"lane": LANE, "request": {
        "agent": "bot", "action_class": "summarise", "autonomy_grade": "L2", "footprint": ["personal-data"]}})
    assert inside["result"] == {"lane_id": "lane-research", "allowed": True, "violations": []}
    outside = call("lane_evaluate", {"lane": LANE, "request": {
        "agent": "bot", "action_class": "publish", "autonomy_grade": "L3", "footprint": ["personal-data", "web"]}})
    assert outside["result"]["allowed"] is False and outside["result"]["violations"] == [
        "grade L3 exceeds L2", "action_class 'publish' is outside the lane", "footprints outside lane: web"]
    unapproved = call("lane_evaluate", {"lane": None, "request": {
        "agent": "bot", "action_class": "summarise", "autonomy_grade": "L0", "footprint": []}})
    assert unapproved["result"] == {"lane_id": "", "allowed": False, "violations": ["no approved governance lane"]}


def test_drift_breaker():
    live = call("drift_breaker", {"lease": LEASE, "now": 990.0})["result"]
    assert live["state"] == "RUNNING" and live["effective_grade"] == "L3" and live["verdict"] == ""
    lapsed = call("drift_breaker", {"lease": LEASE, "now": 1001.0})["result"]
    assert lapsed["state"] == "DECAYED" and lapsed["effective_grade"] == "L0"
    tripped = call("drift_breaker", {"lease": LEASE, "metrics": {"drift_structural": True}, "now": 990.0})["result"]
    assert tripped["state"] == "QUARANTINED" and tripped["verdict"] == "refused"
    assert tripped["tripped"][0].startswith("tripwire 'drift'")
    gap = call("drift_breaker", {"lease": LEASE, "metrics": {"drift_structural": None}, "now": 990.0})["result"]
    assert gap["state"] == "RUNNING"


def test_erasure_sweep(chain):
    folder, log_root = chain
    _append(folder, log_root, "doc:0", note="Jane Doe")
    env = call("erasure_sweep", {"folder": folder, "subject": "Jane Doe", "log_root": log_root})
    r = env["result"]
    assert env["plane"] == "loomground-erasure" and r["subject"] == "Jane Doe"
    assert sum(len(v) for v in r["hits_by_kind"].values()) == 1
    assert r["estimated_tombstone"]["affected_pair_count"] == 1 and r["estimated_tombstone"]["subject_preview"] == "[REDACTED]"
    assert "scan_cards" in r["blind_spots"] and "pair_from_event" in r["blind_spots"]
    clean = call("erasure_sweep", {"folder": folder, "subject": "Someone Else", "log_root": log_root})["result"]
    assert clean["estimated_tombstone"]["affected_pair_count"] == 0


ABSENT = [("audit_chain_verify", {"folder": "."}, "loomground_audit_chain"),
          ("lock_text", {"text": "hello"}, "loomground_lock"),
          ("lane_evaluate", {"lane": None, "request": {"agent": "bot", "action_class": "summarise",
                                                       "autonomy_grade": "L0", "footprint": []}}, "loomground_lane"),
          ("drift_breaker", {"lease": LEASE}, "loomground_drift"),
          ("erasure_sweep", {"folder": ".", "subject": "Jane Doe"}, "loomground_erasure")]


@pytest.mark.parametrize("name, arguments, module", ABSENT, ids=[m for _, _, m in ABSENT])
def test_absent_plane_is_unavailable(monkeypatch, name, arguments, module):
    """The plane's package is not installed: the tool degrades to `unavailable` and never raises."""
    monkeypatch.setitem(sys.modules, module, None)
    env = call(name, arguments)
    assert env["ok"] is False and env["unavailable"] is True and env["reason"].startswith(f"{module} is not installed")


def test_audit_chain_verify_is_read_only(tmp_path, monkeypatch):
    """A verification must not mint a signing identity: no key, no write, `unavailable`."""
    keys = tmp_path / "keys"
    monkeypatch.setenv("WORKSPACE_KEY_DIR", str(keys))
    env = call("audit_chain_verify", {"folder": str(tmp_path)})
    assert env["unavailable"] and "will not mint" in env["reason"]
    assert not keys.exists()


def test_privacy_scan_refuses_a_serialiser_that_carries_originals(monkeypatch):
    """The backstop: a privacy-shield inside the range whose to_dict still reflects
    SpanFinding.value/.context (the pre-release 2.0.0 commits) yields `unavailable`, not
    an envelope with the original in it."""
    runner = pytest.importorskip("privacy_shield.runner")
    leaky = runner.ScanReport.to_dict
    monkeypatch.setattr(runner.ScanReport, "to_dict", lambda self, **_: leaky(self, include_original=True))
    env = call("privacy_scan", {"text": "Ada: ada@example.com IBAN DE89370400440532013000"})
    assert env["ok"] is False and env.get("unavailable") is True
    blob = json.dumps(env, ensure_ascii=False)
    assert "ada@example.com" not in blob and "DE89370400440532013000" not in blob


@pytest.mark.parametrize("redaction_mode", ["detect_only", "redact", "pseudonymize", "block"])
def test_privacy_scan_withholds_a_span_whose_value_is_not_its_original(monkeypatch, redaction_mode):
    """The local-model layer records a `value_hint`, not the matched text, with
    end = start + 10: a residual read from `value` alone let the untouched overlay out
    under detect_only, and under redact the rest of the address after ten characters."""
    runtime = pytest.importorskip("privacy_shield.services.local_model_runtime")
    text = "treffpunkt ist wie immer am alten wasserturm 7 hinten."
    hit = {"type": "address", "value_hint": "Alter Wasserturm 7", "start_pos": text.index("am alten")}
    monkeypatch.setattr(runtime, "is_local_model_available", lambda *a, **k: True)
    monkeypatch.setattr(runtime, "detect_pii_with_local_model", lambda t, **k: {
        "detected_pii": [hit], "confidence": 0.9, "categories": ["address"],
        "safe_to_send_external": False, "error": None})
    env = call("privacy_scan", {"text": text, "redaction_mode": redaction_mode})
    doc = env["result"]["documents"][0]
    assert [s["layer"] for s in doc["spans"]] == [5]
    assert doc["overlay"] is None and "overlay_withheld" in doc
    assert "asserturm" not in json.dumps(env, ensure_ascii=False)
