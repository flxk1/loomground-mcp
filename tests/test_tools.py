# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""One in-process test per tool, through the mcp client."""
import asyncio
import base64
import json

from mcp import Client

from conftest import PATCH, SOLVER_SAMPLES, TRANSPORT, call
from loomground_mcp import build_server
from loomground_mcp.tools import ALL


def test_lists_every_tool_with_plane_and_function():
    async def go():
        async with Client(build_server()) as client:
            return (await client.list_tools()).tools
    tools = asyncio.run(go())
    assert len(tools) == len(ALL) == 34
    assert all(t.description.startswith("[") and " · " in t.description for t in tools)
    assert "patch_lg" in next(t for t in tools if t.name == "solver_evaluate").input_schema["properties"]


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
    assert call("deontic_conflicts", {"statements": ["O(a : x)", "F(a : ¬ x)"]})["result"]["candidates"] == []


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
