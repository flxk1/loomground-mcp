# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The vendored skills are whole, and ship whole.

``skills/vendored.json`` records every file ``tools/vendor_skills.py`` copied out of each source repository at the
pinned commit. These tests hold the package to that record — nothing missing, nothing unrecorded, nothing altered,
no body pointing at a path that is not next to it (skills_lint's rule, in this repository's own suite so a dropped
file fails here rather than in someone else's sweep) — and hold the wheel's package-data to the same file list, so
a skill cannot be complete in the repository and incomplete in the wheel. They need no checkout and no network:
they read the installed package, which is the source tree under an editable install and site-packages otherwise.
"""
import glob
import json
import os
import subprocess
import sys
from importlib import resources
from pathlib import Path

import pytest

import vendor_skills
from conftest import SOLVER_SAMPLES, call

PACKAGE = Path(str(resources.files("loomground_mcp")))
SKILLS = PACKAGE / "skills"
ROOT = Path(__file__).resolve().parents[1]
MANIFEST = vendor_skills.manifest(SKILLS)
RECORDS = MANIFEST["skills"]


def test_vendored_tree_matches_the_manifest():
    assert vendor_skills.check(SKILLS) == []


def test_manifest_records_a_revision_per_skill():
    assert [(r["repo"], r["name"]) for r in RECORDS] == sorted((r["repo"], r["name"]) for r in RECORDS)
    assert {(r["repo"], r["name"]) for r in RECORDS} == {(e["repo"], e["name"]) for e in json.loads(
        (SKILLS / "index.json").read_text(encoding="utf-8"))}
    for r in RECORDS:
        assert vendor_skills.SHA_RE.match(r["commit"]), r
        assert r["source"] == f"skills/{r['name']}"
        assert r["url"] == f"https://github.com/flxk1/{r['repo']}/tree/{r['commit']}/{r['source']}"
        assert ("SKILL.md" in r["files"]) is not bool(r.get("private"))


@pytest.mark.parametrize("record", RECORDS, ids=lambda r: f"{r['repo']}/{r['name']}")
def test_every_vendored_file_is_covered_by_package_data(record):
    """The packaging drop that made this repository ship instructions pointing at nothing: a glob matching only
    SKILL.md. Every file the manifest records must be matched by a package-data pattern."""
    tomllib = pytest.importorskip("tomllib")
    patterns = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "tool"]["setuptools"]["package-data"]["loomground_mcp"]
    src = ROOT / "src" / "loomground_mcp"
    packaged = {Path(p).relative_to(src).as_posix()
                for pat in patterns for p in glob.glob(str(src / pat), recursive=True) if Path(p).is_file()}
    for rel in record["files"]:
        assert f"skills/{record['repo']}/{record['name']}/{rel}" in packaged


@pytest.mark.parametrize("tool", sorted(SOLVER_SAMPLES))
def test_the_vendored_solver_script_runs_and_agrees_with_its_tool(tool):
    """The scripts now ship, so the SKILL.md shell fallback is executable from the installed package."""
    skill, script, sample = SOLVER_SAMPLES[tool]
    path = SKILLS / "loomground-solver" / skill / "scripts" / script
    proc = subprocess.run([sys.executable, str(path)], input=json.dumps(sample), capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout) == call(tool, sample)["result"]


def test_skills_lint_passes_on_the_vendored_tree():
    """The canonical linter (flxk1/repo-standards tools/skills_lint.py), when it is reachable: CI pins and fetches
    it, a checkout is found by convention, and the rule it enforces on referenced paths is checked unconditionally
    by test_vendored_tree_matches_the_manifest either way."""
    for c in [os.environ.get("REPO_STANDARDS", ""), ROOT.parent / "repo-standards",
              ROOT.parent.parent / "repo-standards"]:
        lint = Path(c) / "tools" / "skills_lint.py" if c else None
        if lint and lint.is_file():
            proc = subprocess.run([sys.executable, str(lint), str(SKILLS)], capture_output=True, text=True)
            assert proc.returncode == 0, proc.stdout + proc.stderr
            assert f"{len(RECORDS)}/{len(RECORDS)} skills conform" in proc.stdout
            return
    pytest.skip("repo-standards not found (set REPO_STANDARDS)")
