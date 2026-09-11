# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONVERTER = ROOT / "hosts" / "skill_to_platform.py"
SKILLS = ROOT / "src" / "loomground_mcp" / "skills"
REPO, NAME = "loomground-deontic", "deontic"
SKILL = SKILLS / REPO / NAME / "SKILL.md"
DEFAULT_SERVER_URL = "http://127.0.0.1:8765/mcp"
N8N_TYPES = {"@n8n/n8n-nodes-langchain.chatTrigger", "@n8n/n8n-nodes-langchain.agent",
             "@n8n/n8n-nodes-langchain.lmChatAnthropic", "@n8n/n8n-nodes-langchain.mcpClientTool"}


def allowed_tools() -> list[str]:
    index = json.loads((SKILLS / "index.json").read_text(encoding="utf-8"))
    return next(e for e in index if e["repo"] == REPO and e["name"] == NAME)["allowed_tools"]


def convert(target: str, *extra: str) -> str:
    argv = [sys.executable, str(CONVERTER), str(SKILL), "--target", target,
            "--repo-url", f"https://github.com/flxk1/{REPO}", *extra]
    run = subprocess.run(argv, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    return run.stdout


@pytest.fixture(scope="module", autouse=True)
def _present():
    if not SKILL.exists():
        pytest.skip(f"{SKILL} not vendored")


def test_n8n_workflow_is_json_with_the_expected_nodes():
    wf = json.loads(convert("n8n", "--server-url", "https://mcp.example/mcp"))
    nodes = {n["type"]: n for n in wf["nodes"]}
    assert set(nodes) == N8N_TYPES
    mcp = nodes["@n8n/n8n-nodes-langchain.mcpClientTool"]["parameters"]
    assert mcp["endpointUrl"] == "https://mcp.example/mcp"
    assert mcp["serverTransport"] == "httpStreamable"
    assert mcp["include"] == "selected" and mcp["includeTools"] == allowed_tools()
    agent = nodes["@n8n/n8n-nodes-langchain.agent"]["parameters"]["options"]["systemMessage"]
    assert agent.startswith(f"# {NAME}\n") and "deontic_engine.py" in agent
    assert wf["meta"]["skill"] == NAME and wf["connections"]["loomground-mcp"]["ai_tool"]


def test_langdock_document_names_the_allowed_tools():
    doc = convert("langdock", "--server-url", "https://mcp.example/mcp")
    assert doc.startswith(f"# Langdock assistant: {NAME}")
    for tool in allowed_tools():
        assert f"`{tool}`" in doc
    assert "https://mcp.example/mcp" in doc and "## Instructions" in doc


def test_server_url_defaults_to_the_local_endpoint():
    wf = json.loads(convert("n8n"))
    mcp = next(n for n in wf["nodes"] if n["type"] == "@n8n/n8n-nodes-langchain.mcpClientTool")
    assert mcp["parameters"]["endpointUrl"] == DEFAULT_SERVER_URL
    help_text = subprocess.run([sys.executable, str(CONVERTER), "--help"],
                               capture_output=True, text=True, check=True).stdout
    assert DEFAULT_SERVER_URL in help_text and "--server-url URL" in help_text
