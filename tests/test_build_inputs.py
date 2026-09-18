# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""What this repository reads to build and test itself may only be a published repository.

A product that reads from a working repository at build time inherits that repository's churn and its visibility:
a working repo is where rules are drafted, renamed and reverted, and it can be made private without notice — at
which point a default CI token cannot read it and every consumer goes red. The catalogue is the family's own list
of what is published, so it is the test: every repository the workflow fetches, and every git-pinned requirement,
has to be in it. Anything else is vendored at a commit instead (`skills/vendored.json`), never fetched.
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "main.yml"
CATALOGUE = json.loads((ROOT / "src" / "loomground_mcp" / "catalogue.json").read_text(encoding="utf-8"))
PUBLISHED = {r["repo"] for r in CATALOGUE["repos"]}
MANIFEST = json.loads((ROOT / "src" / "loomground_mcp" / "skills" / "vendored.json").read_text(encoding="utf-8"))
INDEX = json.loads((ROOT / "src" / "loomground_mcp" / "skills" / "index.json").read_text(encoding="utf-8"))
# A build input the catalogue does not carry, with the reason it is nonetheless allowed. Empty: an addition has to
# be argued for here rather than passing unnoticed.
NOT_CATALOGUED: dict[str, str] = {}
FETCH = re.compile(r"git\s+-C\s+\S+\s+fetch[^\n]*https://github\.com/flxk1/([A-Za-z0-9._$-]+)")
PINNED = re.compile(r"^([A-Za-z0-9._-]+) @ git\+https://github\.com/flxk1/([A-Za-z0-9._-]+)@", re.M)


def fetched() -> set[str]:
    """Every repository a workflow step fetches. `$repo` is the loop over the skill index, so it stands for those."""
    text = WORKFLOW.read_text(encoding="utf-8")
    names = set(FETCH.findall(text))
    if "$repo" in names:
        names = (names - {"$repo"}) | {e["repo"] for e in INDEX if not e.get("private")}
    return names


@pytest.mark.parametrize("repo", sorted(fetched() | {r for _, r in PINNED.findall(
    (ROOT / "requirements-dev.txt").read_text(encoding="utf-8"))}))
def test_every_build_input_is_a_published_repository(repo):
    assert repo in PUBLISHED or repo in NOT_CATALOGUED, (
        f"{repo} is not in the catalogue, so it is not a published family repository. Vendor what you need from "
        f"it at a commit through skills/vendored.json, or name it in NOT_CATALOGUED with the reason.")


def test_a_vendored_repository_is_not_also_fetched():
    """The point of vendoring it: after this, no step reads from it at all."""
    assert not {r["repo"] for r in MANIFEST.get("tools", [])} & fetched()


def test_the_workflow_reads_nothing_from_repo_standards():
    """Named, because it is the one this repository used to fetch, and the owner may make it private."""
    assert "repo-standards" not in fetched()
    assert "repo-standards" not in (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
