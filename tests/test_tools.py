# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""One in-process test per tool, through the mcp client."""
import asyncio
import base64
import json

from mcp import Client

from conftest import PATCH, TRANSPORT, call
from loomground_mcp import build_server
from loomground_mcp.tools import ALL


def test_lists_every_tool_with_plane_and_function():
    async def go():
        async with Client(build_server()) as client:
            return (await client.list_tools()).tools
    tools = asyncio.run(go())
    assert len(tools) == len(ALL) >= 15
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
