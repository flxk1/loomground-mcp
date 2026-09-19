# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The vendored releases.json is byte-equal to RELEASES.json in the loomground repository at the pinned commit,
every repository its edges name has a record in it, and every dependency this repository declares has an edge.

``LOOMGROUND_RELEASES`` names the file (CI fetches the pinned commit); otherwise the commit is read out of a
reachable checkout; otherwise skip.
"""
import re
from pathlib import Path

from conftest import upstream

from loomground_mcp.tools.releases import SOURCE, load

HERE = Path(__file__).resolve().parents[1]
VENDORED = HERE / "src" / "loomground_mcp" / "releases.json"
THIRD_PARTY = {"mcp"}


def declared() -> set[str]:
    """What pyproject declares this server depends on, third-party aside — the register should carry each as an edge."""
    text = (HERE / "pyproject.toml").read_text(encoding="utf-8")
    block = text.split("dependencies = [", 1)[1].split("]", 1)[0]
    return {re.match(r'"([A-Za-z0-9._-]+)', line.strip()).group(1)
            for line in block.splitlines() if line.strip().startswith('"')} - THIRD_PARTY


def test_vendored_releases_matches_upstream():
    assert VENDORED.read_bytes() == upstream("loomground", SOURCE["commit"], "RELEASES.json", "LOOMGROUND_RELEASES")


def test_every_edge_names_a_repository_the_register_carries():
    doc = load()
    named = {e[side] for group in ("edges", "accepted") for e in doc[group] for side in ("consumer", "dependency")}
    assert named <= set(doc["repos"])


def test_every_dependency_this_repository_declares_has_an_edge():
    doc = load()
    ours = {e["dependency"] for e in doc["edges"] if e["consumer"] == "loomground-mcp"}
    ours |= {a["dependency"] for a in doc["accepted"] if a["consumer"] == "loomground-mcp"}
    assert declared() <= ours
