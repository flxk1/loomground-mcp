<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# loomground-mcp

One MCP server exposing the Loomground planes as tools: versum, the four languages, solver and its skills, ingest, operators, assurance, controls; stdio or HTTP.

## Problem

Each plane is a Python package with its own call, out of reach for Claude, Codex, n8n or Langdock. One server, one tool per plane function, JSON in and out; an error comes back as a structured error.

## Install

```bash
pip install -r requirements-dev.txt   # git-pinned planes
pip install .                         # installs the `loomground-mcp` command
```

## Usage

```bash
loomground-mcp serve --transport stdio|sse|streamable-http [--port 8765]
loomground-mcp tools      # the tool table as JSON
```

`--token <str>` / `LOOMGROUND_MCP_TOKEN` (flag wins) gates the HTTP transports with bearer auth; stdio is unaffected. Transports, the auth contract and a worked client session: [docs/usage.md](docs/usage.md). Attaching the server to Claude Code, Codex, n8n or Langdock: [hosts/README.md](hosts/README.md).

## Example

```
in:  loomground-mcp tools | python -c 'import json,sys; t=json.load(sys.stdin); print(len(t), t[0]["tool"])'
out: 46 loomground_catalogue
```

## Interface

46 tools, one per plane function; the seven solver skill scripts count as functions, and the topos reader, the catalogue, the release register and the skill index are this repository's. The audit chain and the four runtime controls are served read-only: they decide, they do not write. Signatures, envelopes, enums and the tool table per plane: [docs/tools.md](docs/tools.md).

Call `loomground_catalogue` first: the family map, the pipeline order, how documents become an `.lg` patch. `loomground_releases` is the family's release and pin register, vendored from `RELEASES.json`. `loomground_skill` returns the vendored skill index; the same 22 skills are served as MCP prompts, every body checked byte for byte against its repository: [docs/skills.md](docs/skills.md).

Result envelope: `{plane, function, ok, result | error | unavailable}`; keys are passed per call as PEM.

## Family

Interface: exposes the planes over MCP. Pipeline position: beside `source → loomground-ingest → loomground-versum → loomground-solver → applied or diagnostic planes`, reachable from any MCP client.

- consumes: the four languages, versum, solver and its seven skill scripts, ingest, the six operators, the seven assurance artifacts, the signed audit chain, the four runtime controls, and the loomground catalogue and release register; declared ranges and dev pins in [docs/family.md](docs/family.md)
- consumed by: any MCP client: Claude, Codex, n8n MCP Client Tool, Langdock remote MCP
- third-party: `mcp` `>=2,<3`, the official SDK

## Status

0.1.0 · 46 tools · 26 prompts · 126 tests · Python >=3.10 · mcp 2.x. What the suite covers: [docs/testing.md](docs/testing.md).

## License

Apache-2.0 — `LICENSES/Apache-2.0.txt`, `NOTICE`.
