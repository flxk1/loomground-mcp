# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The MCP server and its command line."""
import argparse
import hmac
import json
import os
from typing import Any, Callable, Optional

from mcp.server.mcpserver import MCPServer

from ._version import __version__
from .tools import ALL
from .tools.skills import prompts

INSTRUCTIONS = (
    "Tools wrap the Loomground planes one function each. Every result is an envelope "
    "{plane, function, ok, result | error | unavailable+reason}; ok=false is never a result. "
    "Call loomground_catalogue first for the family map and pipeline order. The family's skills — the roles an "
    "agent can take — are the prompts (prompts/list, one per vendored SKILL.md) and loomground_skill(name)."
)


def build_server() -> MCPServer:
    server = MCPServer("loomground-mcp", instructions=INSTRUCTIONS, version=__version__)
    for fn in ALL:
        server.add_tool(fn)
    for p in prompts():
        server.add_prompt(p)
    return server


def tool_table() -> list[dict[str, str]]:
    return [{"tool": fn.__name__, "plane": fn.plane, "function": fn.function} for fn in ALL]  # type: ignore[attr-defined]


UNAUTHORIZED = json.dumps({"error": "unauthorized"}).encode()


def bearer_gate(app: Callable[..., Any], token: str) -> Callable[..., Any]:
    """ASGI wrapper: every HTTP request must carry `Authorization: Bearer <token>`; lifespan passes through."""
    expected = token.encode()

    async def gate(scope, receive, send):
        if scope["type"] != "http":
            return await app(scope, receive, send)
        auth = dict(scope["headers"]).get(b"authorization", b"")
        if auth[:7].lower() == b"bearer " and hmac.compare_digest(auth[7:], expected):
            return await app(scope, receive, send)
        await send({"type": "http.response.start", "status": 401,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(UNAUTHORIZED)).encode())]})
        await send({"type": "http.response.body", "body": UNAUTHORIZED})

    return gate


def http_app(server: MCPServer, transport: str, host: str, token: Optional[str] = None) -> Callable[..., Any]:
    app = server.sse_app(host=host) if transport == "sse" else server.streamable_http_app(host=host)
    return bearer_gate(app, token) if token else app


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="loomground-mcp")
    root.add_argument("--version", action="version", version=__version__)
    sub = root.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="run the server")
    serve.add_argument("--transport", choices=("stdio", "sse", "streamable-http"), default="stdio")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--token", default=None, help="bearer token for the HTTP transports (env LOOMGROUND_MCP_TOKEN)")
    sub.add_parser("tools", help="print the tool table as JSON")
    return root


def main(argv: Optional[list[str]] = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "tools":
        print(json.dumps(tool_table(), indent=2))
        return 0
    server = build_server()
    if args.transport == "stdio":
        server.run("stdio")
        return 0
    import uvicorn
    token = args.token or os.environ.get("LOOMGROUND_MCP_TOKEN") or None
    uvicorn.run(http_app(server, args.transport, args.host, token), host=args.host, port=args.port,
                log_level=server.settings.log_level.lower())
    return 0
