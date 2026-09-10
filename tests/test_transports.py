# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Smoke over the network transports: the server starts on a free port and an mcp client lists its tools."""
import asyncio
import socket
import subprocess
import sys
import time
import urllib.request

import pytest
from mcp import Client, ClientSession
from mcp.client.sse import sse_client

from conftest import PATCH, TRANSPORT
from loomground_mcp.tools import ALL


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def server(request):
    transport = request.param
    port = _free_port()
    proc = subprocess.Popen([sys.executable, "-m", "loomground_mcp", "serve", "--transport", transport, "--port", str(port)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
    assert len(names) == len(ALL) == 34 and env["result"]["trace"]["evaluation"]["transfer"]["verdict"] == "reserved"


@pytest.mark.parametrize("server", ["streamable-http"], indirect=True)
def test_streamable_http_tool_list(server):
    _, port = server

    async def go():
        async with Client(f"http://127.0.0.1:{port}/mcp") as client:
            return [t.name for t in (await client.list_tools()).tools]
    assert len(asyncio.run(go())) == len(ALL) == 34
