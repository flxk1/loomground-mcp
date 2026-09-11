<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 flxk1 -->
# Attaching loomground-mcp to a host

One server, four hosts. Claude Code and Codex speak stdio and launch the process themselves; n8n and Langdock speak streamable HTTP and need the server already running. What has actually been executed is stated per host below.

Contents: `skill_to_platform.py` (SKILL.md → n8n workflow JSON or Langdock assistant instructions, stdlib only), `n8n/` (two importable workflows).

## Claude Code

```bash
claude mcp add loomground -- loomground-mcp serve --transport stdio
```

Or, as a plugin carrier in `.claude-plugin/plugin.json`:

```json
"mcpServers": { "loomground": { "command": "loomground-mcp", "args": ["serve", "--transport", "stdio"] } }
```

Then ask for `solver_manifest` or `loomground_catalogue`.

**Proven:** not here. A nested `claude -p … --mcp-config <file>` run started from inside a Claude Code session produced no output in 400 s and was stopped; no diagnosis was possible from that position. The stdio surface itself is covered by `tests/test_transports.py` (the standard MCP stdio client lists the tools and gets answers), so the mechanism is standard — but this configuration has not been seen to work end to end. Run the two lines above in your own session to confirm.

## Codex

`.codex/config.toml`:

```toml
[mcp_servers.loomground]
command = "loomground-mcp"
args = ["serve", "--transport", "stdio"]
```

**Proven:** yes. Codex CLI 0.147.0, a scratch `CODEX_HOME` with the block above, `codex exec --approve-for-me`: the server was discovered, `solver_manifest` and `collapse` were called, results printed. Caveat on the Codex side: in plain `codex exec` (non-interactive, approval never) every MCP tool call is auto-cancelled — openai/codex #16685 and #24135 — so `--approve-for-me` or an interactive session is required.

## n8n

Start the server:

```bash
loomground-mcp serve --transport streamable-http --host 0.0.0.0 --port 8765 --token <token>
```

The endpoint is `POST /mcp`. Two node paths consume it:

- Community node `n8n-nodes-mcp` (nerding-io): `connectionType: "http"`, credential `mcpClientHttpApi` with `httpStreamUrl: "http://127.0.0.1:8765/mcp"`. The node calls `getCredentials('mcpClientHttpApi')` unconditionally, so a credential must exist even when the URL is overridden. `n8n/loomground-mcp-proof.workflow.json` is this path: Manual Trigger → List Tools → `loomground_catalogue` → `solver_evaluate` → a Code node that summarises both.
- Built-in `@n8n/n8n-nodes-langchain.mcpClientTool` v1.2: `endpointUrl: "http://127.0.0.1:8765/mcp"`, `serverTransport: "httpStreamable"`, `include: "selected"`, `includeTools: [...]`, wired as `ai_tool` into an `agent` node. `n8n/loomground-mcp-builtin-agent.workflow.json` is this path.

```bash
n8n import:workflow --input=n8n/loomground-mcp-proof.workflow.json   # a top-level "id" is required
n8n execute --id=lgmcpproof000001 --rawOutput
```

Both files carry `REPLACE_WITH_YOUR_CREDENTIAL_ID` where a credential id belongs; set yours before importing. Against a server started with `--token`, the MCP node needs `Authorization: Bearer <token>` — the built-in node's `authentication` is emitted as `"none"` and has to be switched to a header credential in the UI. That combination has not been executed.

**Proven:** the community-node workflow, yes. n8n 2.38.6, `n8n-nodes-mcp` 0.1.37, node 24.12.0, loomground-mcp at public main `b0d2349` (39 tools at that commit; the server now exposes 41): `n8n execute` returned `"status": "success"` with `tool_count: 39`, `catalogue_record_count: 33`, `verdict: "reserved"`, `status: "escalate"`, and 21 `POST /mcp` lines in the server log. No LLM credential was involved, and the server ran without a token (the `--token` option came later). The built-in AI-Agent workflow was imported successfully but **not run** — it needs a chat-model credential. `skill_to_platform.py --target n8n` was run over the family: 29 skills converted and all 29 workflows imported into the same instance.

## Langdock

Settings → Integrations → *Add integration* → *Connect remote MCP* → the server's URL. The server must be reachable over public HTTPS, so run `loomground-mcp serve --transport streamable-http --token <token>` behind a TLS reverse proxy and give Langdock the proxied URL plus the header `Authorization: Bearer <token>`. Then create an assistant, paste a skill's instructions as its system instructions, attach the integration and enable only that skill's `allowed-tools`.

```bash
python hosts/skill_to_platform.py <SKILL.md> --target langdock --server-url https://<your-host>/mcp -o assistant.md
```

**Proven:** no. The recipe above is written from Langdock's documented remote-MCP integration; nothing in it has been executed against a Langdock workspace. Only the generator output (29 assistant documents) exists.

## The converter

```bash
python hosts/skill_to_platform.py <SKILL.md> --target n8n|langdock [--server-url URL] [-o FILE]
```

`--server-url` defaults to `http://127.0.0.1:8765/mcp`. The frontmatter `description` and the body become the system message (relative links rewritten to the enclosing repository's GitHub blob URL at `--ref`, default `main`); `allowed-tools` becomes `includeTools` with `include: "selected"`, or `include: "all"` when the skill declares none. Repository root and URL come from the nearest enclosing `.git`; override with `--repo-root` / `--repo-url`. stdlib only. `tests/test_hosts_converter.py` converts a vendored SKILL.md for both targets.
