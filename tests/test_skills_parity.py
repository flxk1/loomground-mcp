# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Every skill against its repository at the pinned commit: the vendored directory holds that commit's
``skills/<name>/`` entire — the same file names, each byte-equal — and the index record's name, description and
allowed_tools equal the SKILL.md frontmatter (a private repository: the frontmatter only). The checkout is
resolved by ``tools/vendor_skills.py``, the script that wrote the tree, so the test cannot look somewhere else
than the vendoring did; a repository whose commit is in no reachable checkout skips.
"""
import os
from pathlib import Path

import pytest
import vendor_skills

from loomground_mcp.tools.skills import body_path, frontmatter_fields, load_index

HERE = Path(__file__).resolve().parents[1]
MANIFEST = {(r["repo"], r["name"]): r for r in vendor_skills.manifest()["skills"]}
FIXTURE_FILES = ("LOOMGROUND_CATALOGUE", "LOOMGROUND_RELEASES")
FIXTURE_DIRS = ("LOOMGROUND_SOLVER_SKILLS", "LOOMGROUND_TOPOS_EXAMPLES")


def checkout(repo: str, commit: str) -> Path:
    for co in vendor_skills.checkouts(repo):
        if (co / ".git").exists() and vendor_skills.has_commit(co, commit):
            return co
    pytest.skip(f"{repo}@{commit[:7]} in no reachable checkout (set LOOMGROUND_SKILLS_ROOT)")


@pytest.mark.skipif(not os.environ.get("CI"), reason="a skip budget is a local convenience; CI has none")
def test_ci_has_every_pinned_source():
    """In CI every parity source must be there. The job fetches them at their pins; if a fetch is lost, the parity
    items would quietly turn into `s` and the byte-equality they assert would stop being asserted at all. This is
    the test that goes red instead."""
    missing = [f"{repo}@{commit[:7]}" for repo, commit in
               sorted({(e["repo"], e["commit"]) for e in load_index() if not e.get("private")})
               if not any((co / ".git").exists() and vendor_skills.has_commit(co, commit)
                          for co in vendor_skills.checkouts(repo))]
    missing += [f"${v}" for v in FIXTURE_FILES if not Path(os.environ.get(v, "")).is_file()]
    missing += [f"${v}" for v in FIXTURE_DIRS if not Path(os.environ.get(v, "")).is_dir()]
    assert not missing, f"parity sources absent in CI: {', '.join(missing)}"


@pytest.mark.parametrize("entry", load_index(), ids=lambda e: f"{e['repo']}/{e['name']}")
def test_vendored_skill_matches_repository(entry):
    repo, name, commit = entry["repo"], entry["name"], entry["commit"]
    co = checkout(repo, commit)
    upstream = vendor_skills.tree(co, commit, vendor_skills.source_path(name))
    blob = vendor_skills.git(co, "cat-file", "blob", upstream["SKILL.md"][1])
    fm = frontmatter_fields(blob.decode("utf-8"))
    assert (fm["name"], fm["description"], vendor_skills.split_allowed_tools(fm.get("allowed-tools", ""))) == \
        (name, entry["description"], entry["allowed_tools"])
    if entry.get("private"):
        assert not body_path(entry).is_file()
        return
    dest = HERE / "src" / "loomground_mcp" / "skills" / repo / name
    assert vendor_skills.vendored_files(dest) == set(upstream) == set(MANIFEST[(repo, name)]["files"])
    for rel, (_mode, sha) in sorted(upstream.items()):
        assert (dest / rel).read_bytes() == vendor_skills.git(co, "cat-file", "blob", sha), rel
