# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The vendored catalogue.json is byte-equal to CATALOGUE.json in the loomground repository at the pinned commit.

``LOOMGROUND_CATALOGUE`` names the file (CI fetches the pinned commit when it is public); a sibling checkout is
found by convention; otherwise skip.
"""
import json
import os
import re
from pathlib import Path

import pytest

from loomground_mcp.tools.catalogue import SOURCE

HERE = Path(__file__).resolve().parents[1]
VENDORED = HERE / "src" / "loomground_mcp" / "catalogue.json"
CANDIDATES = [os.environ.get("LOOMGROUND_CATALOGUE", ""),
              HERE.parent / "_local" / "worktrees" / "Loomground Core" / "presence" / "CATALOGUE.json",
              HERE.parent / "loomground-repos" / "loomground" / "CATALOGUE.json",
              HERE.parent / "loomground" / "CATALOGUE.json"]


def upstream() -> Path:
    for c in CANDIDATES:
        if c and Path(c).is_file():
            return Path(c)
    pytest.skip(f"loomground CATALOGUE.json at {SOURCE['commit'][:7]} not found (set LOOMGROUND_CATALOGUE)")


def test_vendored_catalogue_matches_upstream():
    assert VENDORED.read_bytes() == upstream().read_bytes()

def _vtuple(v: str) -> tuple[int, ...]:
    parts = []
    for piece in v.split("."):
        m = re.match(r"\d+", piece)
        if not m:
            break
        parts.append(int(m.group()))
    return tuple(parts)


def _in_range(version: str, spec: str) -> bool:
    """`version` satisfies a comma-joined spec of >=/>/<=/</==/!= clauses, compared as
    version tuples — `0.11.0` against `<0.12` is a minor-level question, not a major one."""
    v = _vtuple(version)
    for clause in filter(None, (c.strip() for c in spec.split(","))):
        m = re.match(r"^(===|==|!=|<=|>=|<|>|~=)\s*(\S+)$", clause)
        if not m:
            return False
        op, want = m.group(1), _vtuple(m.group(2))
        n = max(len(v), len(want))
        a, b = v + (0,) * (n - len(v)), want + (0,) * (n - len(want))
        c = (a > b) - (a < b)
        ok = {"==": c == 0, "===": c == 0, "!=": c != 0, "<": c < 0,
              "<=": c <= 0, ">": c > 0, ">=": c >= 0, "~=": c >= 0}[op]
        if not ok:
            return False
    return True


def test_vendored_install_pins_agree_with_the_declared_ranges():
    """Every catalogue `install` tag sits inside the range pyproject declares for that
    package. Upstream check_catalogue validates the record's shape and the tree, not the
    version it tells a reader to install, so a dependency can be bumped and leave the
    catalogue naming a tag this distribution would refuse — as privacy-shield's @v1.0.0
    did once the range moved to >=2,<3."""
    import tomllib
    catalogue = json.loads(VENDORED.read_text(encoding="utf-8"))
    pyproject = tomllib.loads((HERE / "pyproject.toml").read_text(encoding="utf-8"))
    ranges = {}
    for dep in pyproject["project"]["dependencies"]:
        m = re.match(r"^([A-Za-z0-9][\w.-]*)\s*(.*)$", dep)
        if m and m.group(2):
            ranges[m.group(1).replace("_", "-").lower()] = m.group(2)
    stale = []
    checked = 0
    for record in catalogue["repos"]:
        tag = re.search(r"@(?:[\w.-]*?-)?v(\d[\w.]*)", record.get("install") or "")
        spec = ranges.get(record["repo"].replace("_", "-").lower())
        if not tag or not spec:
            continue
        checked += 1
        if not _in_range(tag.group(1), spec):
            stale.append(f"{record['repo']}: install names v{tag.group(1)}, pyproject declares {spec}")
    assert not stale, "catalogue install pins outside the declared range: " + "; ".join(stale)
    assert checked >= 5, f"only {checked} install pins compared against a declared range"
