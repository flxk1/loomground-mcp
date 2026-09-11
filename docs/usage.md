<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# Usage

## Transports

```bash
loomground-mcp serve --transport stdio                      # a host launches the process
loomground-mcp serve --transport sse --port 8765            # server already running
loomground-mcp serve --transport streamable-http --port 8765
loomground-mcp tools                                        # the tool table as JSON
```

`--host` binds the HTTP transports. `loomground-mcp --version` prints the package version.

## Bearer auth

`--token <str>` or `LOOMGROUND_MCP_TOKEN` (the flag wins) turns on bearer auth for the HTTP
transports. Every request to the MCP endpoints without `Authorization: Bearer <token>` is
answered `401 {"error": "unauthorized"}`. stdio is unaffected: it carries no network surface.
Set a token before exposing the server beyond localhost.

## A client session

The server can be driven in-process, which is how the test-suite exercises it:

```python
import asyncio, json
from mcp import Client
from loomground_mcp import build_server

PATCH = """actor  agent
human  dpo  role legal
gate   transfer  risk high  grant agent
reserve data_transfer by legal when risk >= high
cord agent    -> transfer
cord transfer -> master
"""
TRANSPORT = {"activations": [{"actor": "agent", "source": "transfer", "token": {
    "id": "t1", "kind": "data_transfer", "risk": "high", "party": "customer-42"}}]}

async def go():
    async with Client(build_server()) as c:
        tools = await c.list_tools()
        print(f"{len(tools.tools)} tools")
        r = await c.call_tool("solver_evaluate",
                              {"patch_lg": PATCH, "transport_json": json.dumps(TRANSPORT)})
        print(json.dumps(r.structured_content))

asyncio.run(go())
```

The six-line patch is the one from the `loomground` README; the transport activates token `t1`,
risk `high`, at gate `transfer`. Output:

```
46 tools
{"plane": "loomground-solver", "function": "loomground_solver.loomground.reason", "ok": true, "result": {"method": "loomground", "language": "loomground", "language_version": "0.11.1", "status": "escalate", "accepted": [], "undecided": ["t1"], "rejected": {}, "trace": {"observation": {"nodes": [{"id": "agent", "class": "actor"}, {"id": "dpo", "class": "human", "role": "legal"}, {"id": "transfer", "class": "gate", "risk_floor": "high"}, {"id": "master", "class": "master"}], "cords": [{"from": "agent", "to": "transfer", "type": "authority"}, {"from": "transfer", "to": "master", "type": "egress"}], "reservations": [{"kind": "data_transfer", "by": "legal", "when": "risk >= high"}]}, "evaluation": {"transfer": {"verdict": "reserved", "master": "withhold"}}, "log": [{"gate": "transfer", "verdict": "reserved"}]}}}
```

The gate is reserved for `legal`, so the master verdict is `withhold` and `t1` stays undecided.

Over a running HTTP transport the same session connects with the SDK's `sse_client` or
`streamablehttp_client` against `http://127.0.0.1:8765/sse` (the SSE handshake answers with an
`event: endpoint` line carrying the per-session `/messages/` path).

Host-side configuration for Claude Code, Codex, n8n and Langdock, the SKILL.md converter and
two importable n8n workflows: [`hosts/README.md`](../hosts/README.md).
