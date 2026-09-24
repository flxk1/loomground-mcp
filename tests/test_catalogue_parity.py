# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The vendored catalogue.json is byte-equal to CATALOGUE.json in the loomground repository at the pinned commit.

``LOOMGROUND_CATALOGUE`` names the file (CI fetches the pinned commit); otherwise the commit is read out of a
reachable checkout; otherwise skip. What the catalogue names — every tool and every skill — is held against what
this server serves by test_tools.py and test_skills.py, so a record pointing at nothing does not pass either.
"""
from pathlib import Path

from conftest import upstream

from loomground_mcp.tools.catalogue import SOURCE

HERE = Path(__file__).resolve().parents[1]
VENDORED = HERE / "src" / "loomground_mcp" / "catalogue.json"


def test_vendored_catalogue_matches_upstream():
    assert VENDORED.read_bytes() == upstream("loomground", SOURCE["commit"], "CATALOGUE.json", "LOOMGROUND_CATALOGUE")
