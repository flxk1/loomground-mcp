# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Smoke over the network transports: the server starts on a free port and an mcp client lists its tools;
with a token, the HTTP endpoints answer 401 until `Authorization: Bearer <token>` is presented."""
import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest
from mcp import Client, ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client

from conftest import PATCH, TRANSPORT
from mcp.client.stdio import StdioServerParameters, stdio_client

from loomground_mcp.tools import ALL
from loomground_mcp.tools.skills import load_index, prompt_names

PROMPTS = len(prompt_names(load_index()))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


TOKEN = "s3cret-token"


@pytest.fixture
def server(request):
    """param: transport, or (transport, argv extras, env extras)."""
    transport, argv, env = (request.param, [], {}) if isinstance(request.param, str) else request.param
    port = _free_port()
    proc = subprocess.Popen([sys.executable, "-m", "loomground_mcp", "serve", "--transport", transport, "--port", str(port), *argv],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env={**os.environ, **env})
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            with socket.socket() as s:
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    break
            time.sleep(0.1)
        else:
            raise RuntimeError("server did not open its port")
        yield transport, port
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.mark.parametrize("server", ["sse"], indirect=True)
def test_sse_endpoint_and_tool_list(server):
    _, port = server
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/sse", timeout=5) as r:
        assert r.status == 200 and r.headers["content-type"].startswith("text/event-stream")
        assert r.readline() == b"event: endpoint\r\n"

    async def go():
        async with sse_client(f"http://127.0.0.1:{port}/sse") as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                names = [t.name for t in (await session.list_tools()).tools]
                out = await session.call_tool("solver_evaluate", {"patch_lg": PATCH, "transport_json": TRANSPORT})
                return names, out.structured_content
    names, env = asyncio.run(go())
    assert len(names) == len(ALL) == 55 and env["result"]["trace"]["evaluation"]["transfer"]["verdict"] == "reserved"


@pytest.mark.parametrize("server", ["streamable-http"], indirect=True)
def test_streamable_http_tool_and_prompt_list(server):
    _, port = server

    async def go():
        async with Client(f"http://127.0.0.1:{port}/mcp") as client:
            tools = [t.name for t in (await client.list_tools()).tools]
            prompts = [p.name for p in (await client.list_prompts()).prompts]
            got = await client.get_prompt("deontic")
            return tools, prompts, got
    tools, prompts, got = asyncio.run(go())
    assert len(tools) == len(ALL) == 55 and len(prompts) == PROMPTS == 26
    assert got.messages[0].content.text.startswith("Skill deontic from loomground-deontic @ ")


def test_stdio_tool_and_prompt_list():
    params = StdioServerParameters(command=sys.executable, args=["-m", "loomground_mcp", "serve", "--transport", "stdio"])

    async def go():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = [t.name for t in (await session.list_tools()).tools]
                prompts = [p.name for p in (await session.list_prompts()).prompts]
                got = await session.get_prompt("analyse-risks")
                return tools, prompts, got
    tools, prompts, got = asyncio.run(go())
    assert len(tools) == len(ALL) == 55 and len(prompts) == PROMPTS == 26
    assert sorted(prompts) == sorted(prompt_names(load_index()))
    assert got.messages[0].role == "user" and got.messages[0].content.text.startswith("Skill analyse-risks from loomground-solver @ ")


def _status(url: str, headers: dict[str, str] | None = None) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.readline()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


UNAUTHORIZED = b'{"error": "unauthorized"}'
BEARER = {"Authorization": f"Bearer {TOKEN}"}
WRONG = {"Authorization": "Bearer not-the-token"}


@pytest.mark.parametrize("server", [("sse", ["--token", TOKEN], {})], indirect=True)
def test_sse_token_gate(server):
    _, port = server
    url = f"http://127.0.0.1:{port}/sse"
    assert _status(url) == (401, UNAUTHORIZED)
    assert _status(url, WRONG) == (401, UNAUTHORIZED)
    assert _status(f"http://127.0.0.1:{port}/messages/?session_id=0", WRONG)[0] == 401
    status, first = _status(url, BEARER)
    assert status == 200 and first == b"event: endpoint\r\n"

    async def go():
        async with sse_client(url, headers=BEARER) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return [t.name for t in (await session.list_tools()).tools]
    assert len(asyncio.run(go())) == len(ALL) == 55


@pytest.mark.parametrize("server", [("streamable-http", [], {"LOOMGROUND_MCP_TOKEN": TOKEN})], indirect=True)
def test_streamable_http_token_gate_from_env(server):
    _, port = server
    url = f"http://127.0.0.1:{port}/mcp"
    status, body = _status(url)
    assert status == 401 and json.loads(body) == {"error": "unauthorized"}
    assert _status(url, WRONG) == (401, UNAUTHORIZED)

    async def go(headers):
        async with Client(streamable_http_client(url, http_client=create_mcp_http_client(headers=headers))) as client:
            return [t.name for t in (await client.list_tools()).tools]
    assert len(asyncio.run(go(BEARER))) == len(ALL) == 55
    with pytest.raises(Exception):
        asyncio.run(go(WRONG))


@pytest.mark.parametrize("server", [("streamable-http", ["--token", TOKEN], {"LOOMGROUND_MCP_TOKEN": "env-loses"})], indirect=True)
def test_streamable_http_flag_wins_over_env(server):
    _, port = server
    url = f"http://127.0.0.1:{port}/mcp"
    assert _status(url, {"Authorization": "Bearer env-loses"}) == (401, UNAUTHORIZED)

    async def go():
        async with Client(streamable_http_client(url, http_client=create_mcp_http_client(headers=BEARER))) as client:
            return [t.name for t in (await client.list_tools()).tools]
    assert len(asyncio.run(go())) == len(ALL) == 55
