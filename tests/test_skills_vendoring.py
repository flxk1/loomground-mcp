# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The vendored skills are whole, and ship whole.

``skills/vendored.json`` records every file ``tools/vendor_skills.py`` copied out of each source repository at the
pinned commit. These tests hold the package to that record in both directions — nothing missing, nothing altered,
nothing empty, and nothing present that no record vouches for, walked from the disk so an added file cannot hide —
re-derive each index entry from the vendored body, and apply skills_lint's referenced-path rule in this
repository's own suite, so a dropped file fails here rather than in someone else's sweep. The packaging globs are
held to the same list, so a skill cannot be whole in the repository and truncated in the wheel, and the shipped
solver scripts are executed. No checkout, no network: they read the installed package, which is the source tree
under an editable install and site-packages otherwise.
"""
import glob
import json
import shutil
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
LINT = ROOT / "tools" / "vendored" / "skills_lint.py"
RECORDS = vendor_skills.manifest(SKILLS)["skills"]


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


def packaged_skill_files() -> set[str]:
    """What setuptools would put under `skills/` — its package-data globs minus its exclude-package-data globs."""
    tomllib = pytest.importorskip("tomllib")
    cfg = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["setuptools"]
    src = ROOT / "src" / "loomground_mcp"

    def expand(patterns):
        return {Path(p).relative_to(src).as_posix()
                for pat in patterns for p in glob.glob(str(src / pat), recursive=True) if Path(p).is_file()}
    included = expand(cfg["package-data"]["loomground_mcp"])
    excluded = expand(cfg.get("exclude-package-data", {}).get("loomground_mcp", []))
    return {p for p in included - excluded if p.startswith("skills/")}


def test_package_data_ships_exactly_the_manifest():
    """The packaging drop that made this repository ship instructions pointing at nothing: a glob matching only
    SKILL.md. What ships under skills/ is now exactly the manifest, its own record, and the index — no file the
    manifest does not vouch for, and no recorded file left behind."""
    expected = {f"skills/{r['repo']}/{r['name']}/{rel}" for r in RECORDS for rel in r["files"]}
    assert packaged_skill_files() == expected | {"skills/index.json", "skills/vendored.json"}


@pytest.mark.parametrize("record", RECORDS, ids=lambda r: f"{r['repo']}/{r['name']}")
def test_every_vendored_file_is_covered_by_package_data(record):
    packaged = packaged_skill_files()
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


def test_the_vendored_tools_match_the_manifest():
    """The linter is vendored like everything else — by commit, with a hash — so nothing here reads from the
    repository it came from, at build time or ever."""
    assert vendor_skills.check_tools(ROOT, SKILLS) == []


def lint(*roots) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(LINT), *(str(r) for r in roots)], capture_output=True, text=True)


def test_skills_lint_passes_on_the_vendored_tree():
    """The family's Agent Skills linter, vendored from flxk1/repo-standards: no env var, no checkout, no network,
    no `if present` — this cannot skip. Asserting the conform line as well as the exit code means a silent
    nothing-to-do (the linter's own exit 2) cannot read as a pass."""
    proc = lint(SKILLS)
    assert f"{len(RECORDS)}/{len(RECORDS)} skills conform" in proc.stdout, proc.stdout + proc.stderr
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_skills_lint_does_not_care_where_the_tree_sits(tmp_path):
    """The linter's skip list contains `work`, and a GitHub runner's workspace is `/home/runner/work/<repo>/<repo>`.
    Matched against an absolute path's parts, that skipped every skill and reported nothing linted. The pinned
    commit matches the list relative to the scan root instead; this holds a re-pin to that, rather than working
    around it by passing a relative path."""
    nested = tmp_path / "work" / "pkg" / "skills"
    shutil.copytree(SKILLS, nested)
    assert lint(nested).stdout == lint(SKILLS).stdout
    assert lint(nested).returncode == 0


# (the frontmatter, the rule it breaks) — the three rules no other check in this repository enforces
BREAKS = [
    ("name: x-skill\ndescription: " + "a" * 1100 + "\n", "description 1100 > 1024"),
    ("name: x-skill\ndescription: Use when a key is not in the standard.\nauthor: nobody\n",
     "key not in standard: author"),
    ("name: x-skill\ndescription: A description that never says on what occasion to reach for it.\n",
     "description does not say when to use it"),
]


@pytest.mark.parametrize("frontmatter,finding", BREAKS, ids=["description-length", "allowed-keys", "trigger"])
def test_the_vendored_linter_still_enforces_its_three_rules(tmp_path, frontmatter, finding):
    """What vendoring must not quietly lose: these are the rules this repository has no other check for, so a
    re-pin that dropped one would otherwise go unnoticed."""
    skill = tmp_path / "root" / "x-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(f"---\n{frontmatter}---\n\n# x-skill\n", encoding="utf-8")
    proc = lint(tmp_path / "root")
    assert finding in proc.stdout, proc.stdout + proc.stderr
    assert proc.returncode == 1 and "0/1 skills conform" in proc.stdout
