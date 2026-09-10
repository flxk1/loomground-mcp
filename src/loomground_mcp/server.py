# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The MCP server and its command line."""
import argparse
import json
from typing import Optional

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


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="loomground-mcp")
    root.add_argument("--version", action="version", version=__version__)
    sub = root.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="run the server")
    serve.add_argument("--transport", choices=("stdio", "sse", "streamable-http"), default="stdio")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
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
    else:
        server.run(args.transport, host=args.host, port=args.port)
    return 0
