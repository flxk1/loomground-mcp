# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The vendored catalogue.json is byte-equal to CATALOGUE.json in the loomground repository at the pinned commit.

``LOOMGROUND_CATALOGUE`` names the file (CI fetches the pinned commit when it is public); a sibling checkout is
found by convention; otherwise skip.
"""
import os
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
