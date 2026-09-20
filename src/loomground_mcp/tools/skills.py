# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""loomground: the family's Agent Skills (SKILL.md), vendored at each repository's pushed main commit and served
as MCP prompts (one per vendored body) and as the ``loomground_skill`` tool.

``skills/index.json`` is the record set — {repo, name, description, allowed_tools, commit, path, url[, private]} —
and ``skills/<repo>/<name>/SKILL.md`` the bodies. A private repository has a record and no body: no prompt, and
``loomground_skill`` answers ``unavailable``. A skill name shared by two repositories is qualified ``<repo>/<name>``
(prompt name, and accepted by ``loomground_skill``); every other prompt is named after its skill.
"""
import json
import re
from collections import Counter
from importlib import resources
from typing import Any, Optional

from mcp.server.mcpserver.prompts.base import Prompt

from ._result import Unavailable, tool

PLANE = "loomground"
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def load_index() -> list[dict[str, Any]]:
    return json.loads(resources.files("loomground_mcp").joinpath("skills", "index.json").read_text(encoding="utf-8"))


def body_path(entry: dict[str, Any]):
    return resources.files("loomground_mcp").joinpath("skills", entry["repo"], entry["name"], "SKILL.md")


def split_frontmatter(text: str) -> tuple[Optional[str], str]:
    m = FRONTMATTER.match(text)
    return (m.group(1), text[m.end():]) if m else (None, text)


def frontmatter_fields(text: str) -> dict[str, str]:
    """The scalar fields of an Agent Skills frontmatter: one line per key, quoted or folded values; nested keys skipped."""
    raw, _ = split_frontmatter(text)
    fields: dict[str, str] = {}
    key = None
    folded = False
    for line in (raw or "").splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            folded = value in (">", ">-", "|", "|-")
            fields[key] = "" if folded else value
        elif key and line[:1] in (" ", "\t") and (folded or fields[key]):
            # a folded block starts empty, so an indented line still belongs to it
            fields[key] = f"{fields[key]} {line.strip()}".strip()
    for k, v in fields.items():
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
            fields[k] = v[1:-1].replace("''", "'") if v[0] == "'" else v[1:-1].replace('\\"', '"')
    return fields


def allowed_tools_of(fields: dict[str, str]) -> list[str]:
    """The `allowed-tools` frontmatter as a record list. Agent Skills writes the field
    comma-separated, so a bare `.split()` keeps the commas and yields `privacy_scan,`
    — not a tool name anything can match. Whitespace-only separation remains valid.

    A comma inside a scope does not separate: `Bash(a:*, b:*)` is ONE grant, so the
    split only fires at paren depth zero — replacing every comma would take the grant
    apart and produce the same unmatchable fragments this function exists to avoid."""
    raw, depth, token, out = fields.get("allowed-tools", ""), 0, [], []
    for ch in raw:
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


def prompt_names(index: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Prompt name → record, for every record with a body; a name held by more than one repository is qualified."""
    shared = {n for n, c in Counter(e["name"] for e in index).items() if c > 1}
    return {(f"{e['repo']}/{e['name']}" if e["name"] in shared else e["name"]): e for e in index if not e.get("private")}


MCP_TOOL = re.compile(r"[a-z][a-z0-9_]*")


def partition_tools(tools: list[str]) -> tuple[list[str], list[str]]:
    """(tools this server serves, grants for the host). `allowed-tools` mixes the two: a
    skill may ask its host for `Read` or `Bash(privacy-shield:*)` beside the tools served
    here. Every served tool is lowercase snake_case; a grant is not."""
    served = [t for t in tools if MCP_TOOL.fullmatch(t)]
    return served, [t for t in tools if t not in served]


def header(entry: dict[str, Any]) -> str:
    served, grants = partition_tools(entry["allowed_tools"])
    tools = " ".join(served) or "(none declared)"
    aside = f"; host grants: {' '.join(grants)}" if grants else ""
    return f"Skill {entry['name']} from {entry['repo']} @ {entry['commit']}; tools: {tools}{aside}"


def render(entry: dict[str, Any]) -> str:
    _, body = split_frontmatter(body_path(entry).read_text(encoding="utf-8"))
    return f"{header(entry)}\n\n{body.lstrip(chr(10))}"


def _renderer(entry: dict[str, Any]):
    def fn() -> str:
        return render(entry)
    return fn


def prompts() -> list[Prompt]:
    return [Prompt.from_function(_renderer(entry), name=name, description=entry["description"])
            for name, entry in prompt_names(load_index()).items()]


def resolve(index: list[dict[str, Any]], name: str) -> dict[str, Any]:
    by_prompt = {(f"{e['repo']}/{e['name']}"): e for e in index}
    if name in by_prompt:
        return by_prompt[name]
    hits = [e for e in index if e["name"] == name]
    if not hits:
        raise Unavailable(f"unknown skill {name!r}; call loomground_skill() for the index")
    if len(hits) > 1:
        raise Unavailable(f"{name!r} is held by more than one repository; use one of "
                          + ", ".join(f"{e['repo']}/{e['name']}" for e in hits))
    return hits[0]


@tool(PLANE, "skills/index.json")
def loomground_skill(name: Optional[str] = None) -> Any:
    """The family's skills — the roles an agent can take. Without `name`: the index, one record per SKILL.md (repo, name, description, allowed_tools, commit, path, url, prompt; `private: true` when the repository is private and only the record is carried). With `name` (a skill name, or `<repo>/<name>` when the name is shared): the record plus `body`, the SKILL.md with its frontmatter stripped — the same text `prompts/get` returns. Unknown or private → unavailable."""
    index = load_index()
    names = {id(e): n for n, e in prompt_names(index).items()}
    if name is None:
        return [{**e, "prompt": names.get(id(e))} for e in index]
    entry = resolve(index, name)
    if entry.get("private"):
        raise Unavailable(f"{entry['repo']} is a private repository; the body is not vendored (record only, see {entry['url']})")
    _, body = split_frontmatter(body_path(entry).read_text(encoding="utf-8"))
    return {**entry, "prompt": names[id(entry)], "body": body.lstrip("\n")}


TOOLS = [loomground_skill]
