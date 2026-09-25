# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The vendored skills: the index, the ``loomground_skill`` tool, the prompts, and the catalogue's ``skills[]``
against the index per repository."""
import asyncio

import pytest
from mcp import Client

from conftest import call
from loomground_mcp import build_server
from loomground_mcp.tools.catalogue import load as catalogue
from loomground_mcp.tools.skills import body_path, header, load_index, prompt_names, split_frontmatter

INDEX = load_index()
PUBLIC = [e for e in INDEX if not e.get("private")]
PRIVATE = [e for e in INDEX if e.get("private")]
KEYS = {"repo", "name", "description", "allowed_tools", "commit", "path", "url"}


def test_index_records():
    assert len(INDEX) == 33 and len(PUBLIC) == 33 and len(PRIVATE) == 0
    assert [(e["repo"], e["name"]) for e in INDEX] == sorted((e["repo"], e["name"]) for e in INDEX)
    for e in INDEX:
        assert set(e) - {"private"} == KEYS and len(e["commit"]) == 40 and e["description"]
        assert e["path"] == f"skills/{e['name']}/SKILL.md"
        assert e["url"] == f"https://github.com/flxk1/{e['repo']}/blob/{e['commit']}/{e['path']}"
        assert body_path(e).is_file() is not bool(e.get("private"))


def test_skill_index_tool():
    env = call("loomground_skill")
    assert env["plane"] == "loomground"
    rows = env["result"]
    assert [(r["repo"], r["name"]) for r in rows] == [(e["repo"], e["name"]) for e in INDEX]
    prompts = [r["prompt"] for r in rows]
    assert prompts.count(None) == len(PRIVATE) and {"loomground/loomground", "loomground-governance/loomground", "analyse-risks"} <= set(prompts)
    assert len(set(p for p in prompts if p)) == 33


def test_skill_by_name():
    r = call("loomground_skill", {"name": "analyse-risks"})["result"]
    assert (r["repo"], r["allowed_tools"], r["prompt"]) == ("loomground-solver", ["solver_analyse_risks"], "analyse-risks")
    assert r["body"] == split_frontmatter(body_path(r).read_text(encoding="utf-8"))[1].lstrip("\n")
    assert not r["body"].startswith("---") and "solver_analyse_risks" in r["body"]


def test_skill_shared_name_is_qualified():
    env = call("loomground_skill", {"name": "loomground"})
    assert env["unavailable"] and "loomground-governance/loomground" in env["reason"]
    r = call("loomground_skill", {"name": "loomground-governance/loomground"})["result"]
    assert r["allowed_tools"] == ["solver_evaluate", "solver_verify"] and r["prompt"] == "loomground-governance/loomground"
    assert call("loomground_skill", {"name": "loomground/loomground"})["result"]["allowed_tools"] == []


def test_skill_unknown():
    assert call("loomground_skill", {"name": "no-such-skill"})["unavailable"]


def test_prompts_in_process():
    async def go():
        async with Client(build_server()) as c:
            return (await c.list_prompts()).prompts, await c.get_prompt("analyse-risks")
    listed, got = asyncio.run(go())
    by_name = {p.name: p for p in listed}
    assert len(listed) == 33 and set(by_name) == set(prompt_names(INDEX))
    entry = prompt_names(INDEX)["analyse-risks"]
    assert by_name["analyse-risks"].description == entry["description"] and by_name["analyse-risks"].arguments == []
    assert len(got.messages) == 1 and got.messages[0].role == "user"
    head, body = got.messages[0].content.text.split("\n\n", 1)
    assert head == header(entry) == f"Skill analyse-risks from loomground-solver @ {entry['commit']}; tools: solver_analyse_risks"
    assert body == call("loomground_skill", {"name": "analyse-risks"})["result"]["body"]


CATALOGUE = {r["repo"]: r["skills"] for r in catalogue()["repos"]}
BY_REPO: dict[str, list[str]] = {}
for _e in INDEX:
    BY_REPO.setdefault(_e["repo"], []).append(_e["name"])
# A repository whose skills this server vendors must agree with the catalogue exactly.
# A catalogued skill this server does not vendor is a gap in the index, named below, not a
# disagreement: NOT_VENDORED lists why each is absent, so an omission cannot pass silently.
NOT_VENDORED: dict[str, str] = {}  # every conformant public skill is vendored


@pytest.mark.parametrize("repo", sorted(r for r in CATALOGUE if CATALOGUE[r] or r in BY_REPO))
def test_catalogue_skills_equal_index(repo):
    if repo in NOT_VENDORED:
        assert CATALOGUE[repo] and repo not in BY_REPO, (
            f"{repo} is listed as not vendored ({NOT_VENDORED[repo]}) but the index carries it — "
            "vendor it and drop the entry")
        return
    assert sorted(CATALOGUE[repo]) == sorted(BY_REPO.get(repo, []))


def test_a_folded_description_is_read():
    """`description: >-` starts empty; its indented lines still belong to it."""
    from loomground_mcp.tools.skills import frontmatter_fields
    fm = frontmatter_fields("---\nname: demo\ndescription: >-\n  First half\n  and second half.\nallowed-tools: a b\n---\n\n# demo\n")
    assert fm["description"] == "First half and second half."
    assert fm["name"] == "demo" and fm["allowed-tools"] == "a b"


@pytest.mark.parametrize("raw,tools", [
    ("", []),
    ("a b", ["a", "b"]),
    ("privacy_scan, Bash(privacy-shield:*), Read", ["privacy_scan", "Bash(privacy-shield:*)", "Read"]),
    ("Bash(a:*, b:*),Read", ["Bash(a:*, b:*)", "Read"]),
])
def test_allowed_tools_split_at_paren_depth_zero(raw, tools):
    """Agent Skills writes `allowed-tools` comma-separated; a whitespace split kept the
    commas (`privacy_scan,`), and splitting every comma took a scoped grant apart."""
    import vendor_skills
    assert vendor_skills.split_allowed_tools(raw) == tools


def test_a_host_grant_is_named_apart_in_the_prompt_header():
    """privacy-shield asks its host for `Bash(privacy-shield:*)` and `Read` beside
    `privacy_scan`; the header must not present those as this server's tools."""
    entry = next(e for e in INDEX if e["repo"] == "privacy-shield")
    assert entry["allowed_tools"] == ["privacy_scan", "Bash(privacy-shield:*)", "Read"]
    assert header(entry).endswith("; tools: privacy_scan; host grants: Bash(privacy-shield:*) Read")
