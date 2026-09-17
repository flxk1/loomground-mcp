# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The vendored releases.json is byte-equal to RELEASES.json in the loomground repository at the pinned commit,
and every repository its edges name has a record in it.

``LOOMGROUND_RELEASES`` names the file (CI fetches the pinned commit); otherwise the commit is read out of a
reachable checkout; otherwise skip.
"""
from pathlib import Path

from conftest import upstream

from loomground_mcp.tools.releases import SOURCE, load

HERE = Path(__file__).resolve().parents[1]
VENDORED = HERE / "src" / "loomground_mcp" / "releases.json"


def test_vendored_releases_matches_upstream():
    assert VENDORED.read_bytes() == upstream("loomground", SOURCE["commit"], "RELEASES.json", "LOOMGROUND_RELEASES")


def test_every_edge_names_a_repository_the_register_carries():
    doc = load()
    named = {e[side] for group in ("edges", "accepted") for e in doc[group] for side in ("consumer", "dependency")}
    assert named <= set(doc["repos"])
