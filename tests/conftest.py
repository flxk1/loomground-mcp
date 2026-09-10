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
