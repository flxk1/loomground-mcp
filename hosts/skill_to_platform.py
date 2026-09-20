#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""SKILL.md (Agent Skills format) -> n8n workflow JSON | Langdock assistant instructions.

  skill_to_platform.py SKILL.md --target n8n [--server-url URL] [-o out.json]
  skill_to_platform.py SKILL.md --target langdock [--server-url URL] [-o out.md]

--server-url defaults to http://127.0.0.1:8765/mcp, the endpoint of
`loomground-mcp serve --transport streamable-http` on its default host and port. Langdock
needs a public HTTPS URL instead; pass it.

n8n: chat trigger -> AI Agent (system message = skill body, relative links rewritten to the
repo's GitHub blob URL) <- placeholder chat model + MCP Client Tool (HTTP streamable,
include: selected = the frontmatter allowed-tools this server serves; a host grant
such as Read or Bash(...) is reported separately, never as an MCP tool). The MCP node is emitted with
authentication: none; a server started with --token needs a header credential set by hand.
langdock: the same instructions text + the remote-MCP recipe.

Repo root = nearest ancestor with .git (override --repo-root); GitHub URL from that .git's
origin (override --repo-url); ref = --ref (default main). stdlib only.
"""
import argparse
import configparser
import hashlib
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath

FM_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n?", re.S)
LINK_RE = re.compile(r"(!?\[[^\]]*\]\()([^)\s]+)((?:\s+\"[^\"]*\")?\))")
DEFAULT_SERVER_URL = "http://127.0.0.1:8765/mcp"
AGENT_VERSION = 3.1
MCP_TOOL_VERSION = 1.2
MODEL_NODE = {"type": "@n8n/n8n-nodes-langchain.lmChatAnthropic", "typeVersion": 1.6, "credential": "anthropicApi"}


class SkillError(Exception):
    pass


def _scalar(s: str):
    s = s.strip()
    if not s:
        return ""
    if s[0] == s[-1] and s[0] in "'\"" and len(s) >= 2:
        body = s[1:-1]
        return body.replace("''", "'") if s[0] == "'" else body.encode().decode("unicode_escape") if "\\" in body else body
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if s in ("null", "~"):
        return None
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        return [_scalar(x) for x in inner.split(",")] if inner else []
    return s


def _block(lines, i, indent):
    """Parse a mapping or a list at `indent`; return (value, next_index)."""
    out = None
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        cur = len(raw) - len(raw.lstrip(" "))
        if cur < indent:
            break
        if cur > indent:
            raise SkillError(f"frontmatter: unexpected indent at line {i + 1}: {raw!r}")
        text = raw.strip()
        if text.startswith("- "):
            if out is None:
                out = []
            if not isinstance(out, list):
                raise SkillError(f"frontmatter: list item inside mapping at line {i + 1}")
            out.append(_scalar(text[2:]))
            i += 1
            continue
        if out is None:
            out = {}
        if not isinstance(out, dict):
            raise SkillError(f"frontmatter: key inside list at line {i + 1}")
        m = re.match(r"([A-Za-z0-9_.-]+)\s*:\s*(.*)$", text)
        if not m:
            raise SkillError(f"frontmatter: cannot parse line {i + 1}: {raw!r}")
        key, val = m.group(1), m.group(2)
        if val in ("|", ">", "|-", ">-"):
            j = i + 1
            chunk = []
            while j < len(lines) and (not lines[j].strip() or len(lines[j]) - len(lines[j].lstrip(" ")) > indent):
                chunk.append(lines[j])
                j += 1
            base = min((len(l) - len(l.lstrip(" ")) for l in chunk if l.strip()), default=indent + 2)
            body = [l[base:] if l.strip() else "" for l in chunk]
            out[key] = "\n".join(body).rstrip("\n") + ("\n" if val[0] == "|" else "") if val[0] == "|" else " ".join(x for x in body if x).strip()
            i = j
            continue
        if val == "":
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            nxt = len(lines[j]) - len(lines[j].lstrip(" ")) if j < len(lines) else -1
            if nxt > indent:
                out[key], i = _block(lines, j, nxt)
                continue
            out[key] = None
            i += 1
            continue
        out[key] = _scalar(val)
        i += 1
    return (out if out is not None else {}), i


MCP_TOOL = re.compile(r"[a-z][a-z0-9_]*")


def split_grants(raw: str):
    """`allowed-tools` as a list. Comma- or whitespace-separated, but a comma inside a
    scope does not separate: `Bash(a:*, b:*)` is ONE grant."""
    depth, token, out = 0, [], []
    for ch in raw.strip():
        if ch in "([{":
            depth += 1
        elif ch in ")]}" and depth:
            depth -= 1
        if depth == 0 and (ch.isspace() or ch == ","):
            if token:
                out.append("".join(token))
                token = []
            continue
        token.append(ch)
    if token:
        out.append("".join(token))
    return out


def partition_tools(tools):
    """(MCP tool names, host grants). `allowed-tools` mixes both: a skill may ask its host
    for `Read` or `Bash(privacy-shield:*)` alongside the tools this server serves. Only the
    former belong in an MCP node's includeTools — naming a host grant there tells an operator
    to enable a tool the server does not serve. Every tool loomground-mcp serves is
    lowercase snake_case; a grant is not (`Read`, `Bash(...)`). Matched by shape because this
    script is stdlib-only and standalone, and cannot import the tool registry.
    """
    served = [t for t in tools if MCP_TOOL.fullmatch(t)]
    return served, [t for t in tools if t not in served]


def parse_skill(path: Path):
    text = path.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m:
        raise SkillError(f"{path}: no YAML frontmatter block")
    fm, _ = _block(m.group(1).split("\n"), 0, 0)
    if not isinstance(fm, dict) or not fm.get("name"):
        raise SkillError(f"{path}: frontmatter has no `name`")
    if not fm.get("description"):
        raise SkillError(f"{path}: frontmatter has no `description`")
    tools = fm.get("allowed-tools") or fm.get("allowed_tools") or []
    if isinstance(tools, str):
        tools = split_grants(tools)
    body = text[m.end():].strip("\n")
    if not body.strip():
        raise SkillError(f"{path}: empty body")
    return fm, tools, body


def find_repo_root(start: Path):
    for d in [start] + list(start.parents):
        if (d / ".git").exists():
            return d
    return None


def origin_url(root: Path):
    git = root / ".git"
    if git.is_file():
        line = git.read_text().strip()
        if line.startswith("gitdir:"):
            gd = Path(line.split(":", 1)[1].strip())
            gd = gd if gd.is_absolute() else (root / gd)
            common = gd / "commondir"
            git = (gd / common.read_text().strip()).resolve() if common.exists() else gd
    cfg = git / "config"
    if not cfg.exists():
        return None
    cp = configparser.ConfigParser(strict=False)
    cp.read(cfg)
    url = cp.get('remote "origin"', "url", fallback=None)
    return normalise_url(url) if url else None


def normalise_url(url: str):
    url = url.strip()
    m = re.match(r"git@([^:]+):(.+)$", url)
    if m:
        url = f"https://{m.group(1)}/{m.group(2)}"
    url = re.sub(r"^ssh://git@", "https://", url)
    return url[:-4] if url.endswith(".git") else url


def rewrite_links(body: str, skill_dir_rel: PurePosixPath, repo_url: str, ref: str):
    def sub(m):
        target = m.group(2)
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#") or target.startswith("//"):
            return m.group(0)
        frag = ""
        if "#" in target:
            target, frag = target.split("#", 1)
            frag = "#" + frag
        if target.startswith("/"):
            rel = PurePosixPath(target.lstrip("/"))
        else:
            rel = PurePosixPath(os.path.normpath(str(skill_dir_rel / target)))
        if str(rel).startswith(".."):
            raise SkillError(f"link escapes the repository: {m.group(2)}")
        return f"{m.group(1)}{repo_url}/blob/{ref}/{rel}{frag}{m.group(3)}"
    return LINK_RE.sub(sub, body)


def instructions(fm, body):
    return f"# {fm['name']}\n\n{fm['description'].strip()}\n\n{body}\n"


def n8n_workflow(fm, tools, text, server_url, model, repo_url):
    name = fm["name"]
    served, grants = partition_tools(tools)
    wid = hashlib.sha1(f"{repo_url}#{name}".encode()).hexdigest()[:16]
    nodes = [
        {"id": "trigger", "name": "When chat message received", "type": "@n8n/n8n-nodes-langchain.chatTrigger",
         "typeVersion": 1.1, "position": [0, 0], "parameters": {"options": {}}, "webhookId": f"skill-{name}"},
        {"id": "agent", "name": f"{name} (AI Agent)", "type": "@n8n/n8n-nodes-langchain.agent", "typeVersion": AGENT_VERSION,
         "position": [260, 0], "parameters": {"promptType": "auto", "options": {"systemMessage": text}}},
        {"id": "model", "name": "Chat Model (set your credential)", "type": MODEL_NODE["type"], "typeVersion": MODEL_NODE["typeVersion"],
         "position": [200, 220], "parameters": {"model": {"__rl": True, "mode": "list", "value": model}, "options": {}},
         "credentials": {MODEL_NODE["credential"]: {"id": "REPLACE_WITH_YOUR_CREDENTIAL_ID", "name": "placeholder"}}},
        {"id": "mcp", "name": "loomground-mcp", "type": "@n8n/n8n-nodes-langchain.mcpClientTool", "typeVersion": MCP_TOOL_VERSION,
         "position": [420, 220],
         "parameters": {"endpointUrl": server_url, "serverTransport": "httpStreamable", "authentication": "none",
                        "include": "selected" if served else "all", "includeTools": served, "options": {}}},
    ]
    return {
        "id": wid, "name": f"skill: {name}", "active": False, "settings": {"executionOrder": "v1"}, "nodes": nodes,
        "connections": {
            "When chat message received": {"main": [[{"node": f"{name} (AI Agent)", "type": "main", "index": 0}]]},
            "Chat Model (set your credential)": {"ai_languageModel": [[{"node": f"{name} (AI Agent)", "type": "ai_languageModel", "index": 0}]]},
            "loomground-mcp": {"ai_tool": [[{"node": f"{name} (AI Agent)", "type": "ai_tool", "index": 0}]]},
        },
        "meta": {"source": "skill_to_platform.py", "skill": name, "allowed_tools": tools,
                 "mcp_tools": served, "host_grants": grants},
    }


def langdock_doc(fm, tools, text, server_url):
    name = fm["name"]
    served, grants = partition_tools(tools)
    tl = ", ".join(f"`{t}`" for t in served) if served else "all tools the server lists"
    note = ("" if not grants else
            " The skill also declares " + ", ".join(f"`{g}`" for g in grants) +
            ", which this server does not serve: they are grants for a host that has those"
            " tools, and there is nothing to enable for them on the integration.")
    recipe = (f"**Langdock recipe.** In your Langdock workspace: Settings → Integrations → *Add integration* → "
              f"*Connect remote MCP* → URL `{server_url}` (the server must be reachable over public HTTPS; "
              f"`loomground-mcp serve --transport streamable-http --token <token>` behind a TLS reverse proxy), "
              f"header `Authorization: Bearer <token>`. "
              f"Create an assistant named `{name}`, paste the instructions below as its system instructions, "
              f"attach the loomground-mcp integration and enable only these tools: {tl}.{note}")
    return f"# Langdock assistant: {name}\n\n{recipe}\n\n---\n\n## Instructions\n\n{text}"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="skill_to_platform.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("skill", type=Path, help="path to a SKILL.md")
    ap.add_argument("--target", choices=("n8n", "langdock"), required=True, help="output format")
    ap.add_argument("--server-url", default=DEFAULT_SERVER_URL,
                    help="loomground-mcp streamable-HTTP endpoint (default: %(default)s)")
    ap.add_argument("--repo-root", type=Path, help="repository root (default: nearest ancestor with .git)")
    ap.add_argument("--repo-url", help="https://github.com/<owner>/<repo> (default: origin of the enclosing git repo)")
    ap.add_argument("--ref", default="main", help="git ref for rewritten links (default: %(default)s)")
    ap.add_argument("--model", default="claude-sonnet-4-5", help="n8n chat-model node value (default: %(default)s)")
    ap.add_argument("-o", "--output", type=Path, help="write here (default: stdout)")
    a = ap.parse_args(argv)
    skill = a.skill.resolve()
    try:
        fm, tools, body = parse_skill(skill)
        root = (a.repo_root.resolve() if a.repo_root else find_repo_root(skill.parent))
        if root is None:
            raise SkillError(f"{skill}: no enclosing git repository; pass --repo-root")
        url = a.repo_url or origin_url(root)
        if not url:
            raise SkillError(f"{root}: no origin URL; pass --repo-url")
        rel = PurePosixPath(skill.parent.relative_to(root).as_posix())
        text = instructions(fm, rewrite_links(body, rel, normalise_url(url), a.ref))
        out = (json.dumps(n8n_workflow(fm, tools, text, a.server_url, a.model, normalise_url(url)), indent=2) + "\n"
               if a.target == "n8n" else langdock_doc(fm, tools, text, a.server_url))
    except (SkillError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
