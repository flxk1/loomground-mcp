# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Every skill record against its repository at the pinned commit: a vendored body is byte-equal to
``git show <commit>:<path>``, and the record's name, description and allowed_tools equal that file's frontmatter
(a private repository: the frontmatter only). A checkout is ``$LOOMGROUND_SKILLS_ROOT/<repo>`` or a sibling
directory; a repository whose commit is in no reachable checkout skips.
"""
import os
import subprocess
from pathlib import Path

import pytest

from loomground_mcp.tools.skills import body_path, frontmatter_fields, load_index

HERE = Path(__file__).resolve().parents[1]
ALIASES = {"loomground": ["loomground-repos/Loomground Core"], "loomground-topos": ["legal-topology-grammar"]}


def candidates(repo: str):
    root = os.environ.get("LOOMGROUND_SKILLS_ROOT")
    if root:
        yield Path(root) / repo
    for rel in ALIASES.get(repo, []) + [f"loomground-repos/{repo}", repo]:
        yield HERE.parent / rel


def show(repo: str, commit: str, path: str) -> bytes:
    for co in candidates(repo):
        if (co / ".git").exists():
            r = subprocess.run(["git", "-C", str(co), "show", f"{commit}:{path}"], capture_output=True)
            if r.returncode == 0:
                return r.stdout
    pytest.skip(f"{repo}@{commit[:7]} in no reachable checkout (set LOOMGROUND_SKILLS_ROOT)")


@pytest.mark.parametrize("entry", load_index(), ids=lambda e: f"{e['repo']}/{e['name']}")
def test_vendored_skill_matches_repository(entry):
    upstream = show(entry["repo"], entry["commit"], entry["path"])
    fm = frontmatter_fields(upstream.decode("utf-8"))
    assert (fm["name"], fm["description"], fm.get("allowed-tools", "").split()) == \
        (entry["name"], entry["description"], entry["allowed_tools"])
    if entry.get("private"):
        assert not body_path(entry).is_file()
    else:
        assert body_path(entry).read_bytes() == upstream
