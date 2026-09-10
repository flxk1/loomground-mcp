# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
import asyncio
import logging

import pytest
from mcp import Client

from loomground_mcp import build_server

logging.disable(logging.CRITICAL)  # planes log their refusals; the envelope carries them

POLICY = ("The operator must delete personal data within 30 days after the contract ends. "
          "The operator must not transfer personal data outside the EU. "
          "The operator may retain invoices for ten years.\n")

PATCH = """actor  agent
human  dpo  role legal
gate   transfer  risk high  grant agent
reserve data_transfer by legal when risk >= high
cord agent    -> transfer
cord transfer -> master
"""

TRANSPORT = {"activations": [{"actor": "agent", "source": "transfer", "token": {
    "id": "t1", "kind": "data_transfer", "risk": "high", "party": "customer-42",
    "provenance": ["urn:dls:sha256:b3421929b6310f99781cd8fe287294d0a152acc15ee6b3cfcdcbdde340812d40#para-1:150-240"]}}]}


def call(name: str, arguments: dict | None = None) -> dict:
    """Call one tool in-process over the mcp client and return the structured envelope."""
    async def go():
        async with Client(build_server()) as client:
            return await client.call_tool(name, arguments or {})
    result = asyncio.run(go())
    env = result.structured_content
    assert env is not None and env["ok"] is (not result.is_error)
    return env


@pytest.fixture
def policy_folder(tmp_path):
    (tmp_path / "policy.txt").write_text(POLICY, encoding="utf-8")
    return str(tmp_path)


@pytest.fixture
def keypair():
    from cryptography.hazmat.primitives import serialization as s
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    priv = Ed25519PrivateKey.generate()
    return (priv.private_bytes(s.Encoding.PEM, s.PrivateFormat.PKCS8, s.NoEncryption()).decode(),
            priv.public_key().public_bytes(s.Encoding.PEM, s.PublicFormat.SubjectPublicKeyInfo).decode())


CORPUS = {
    "a.md": ("The operator must delete personal data within 30 days after the contract ends. "
             "The operator must not transfer personal data outside the EU. "
             "'Personal data' means any information relating to a person.\n"),
    "b.md": ("The processor must not transfer personal data outside the EU without safeguards. "
             "The processor may retain invoices for ten years.\n"),
}


@pytest.fixture
def corpus_folder(tmp_path):
    """Two sources sharing a defined term: what the curation loop needs to find a cross-source concept."""
    for name, text in CORPUS.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    return str(tmp_path)


# solver_* skill tools: (skill directory, script file, the JSON the script reads on stdin)
SOLVER_SAMPLES = {
    "solver_analyse_risks": ("analyse-risks", "run.py", {
        "vectors": {"data-breach": [5, 3], "vendor-lock-in": [2, 4], "typo-in-footer": [1, 1]}}),
    "solver_estimate_liability": ("estimate-liability", "run.py", {
        "prior": {"liable": 0.3, "not-liable": 0.7},
        "likelihoods": {"liable": {"breach-documented": 0.9}, "not-liable": {"breach-documented": 0.2}},
        "evidence": "breach-documented"}),
    "solver_litigation_risk": ("litigation-risk-assessor", "run.py", {
        "options": ["fight", "settle"],
        "payoffs": {"fight": {"win": 100, "lose": -80}, "settle": {"win": 20, "lose": 20}},
        "probabilities": {"win": 0.4, "lose": 0.6}}),
    "solver_opponent_model": ("opponent-modeler", "run.py", {
        "options": ["escalate", "concede"],
        "payoffs": {"escalate": {"we-fold": 10, "we-fight": -5}, "concede": {"we-fold": 2, "we-fight": 2}}}),
    "solver_probability": ("probability-tracker", "run.py", {
        "prior": {"delay": 0.5, "on-time": 0.5},
        "likelihoods": {"delay": {"vendor-late": 0.8}, "on-time": {"vendor-late": 0.3}},
        "evidence": "vendor-late"}),
    "solver_strategy": ("strategic-analysis", "run.py", {
        "options": ["build", "buy"],
        "payoffs": {"build": {"boom": 90, "bust": -30}, "buy": {"boom": 60, "bust": 10}}}),
    "solver_advise_addons": ("advise-solver-addons", "advise.py", {
        "policy": {"world_model": {"mode": "recommend", "threshold": 2},
                   "metacognition": {"mode": "manual", "minimum_runs": 3}},
        "problem": {"as_of": "2026-07-19T00:00:00Z", "sources": ["source:a", "source:b"],
                    "claims_may_conflict": True, "available_inputs": ["context_provider", "reference_time"]},
        "runs": []}),
}
