# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The vendored releases.json is byte-equal to RELEASES.json in the loomground repository at the pinned commit.

``LOOMGROUND_RELEASES`` names the file (CI fetches the pinned commit when it is public); the sibling checkout is
found by convention; otherwise skip.
"""
import os
from pathlib import Path

import pytest

from loomground_mcp.tools.releases import SOURCE

HERE = Path(__file__).resolve().parents[1]
VENDORED = HERE / "src" / "loomground_mcp" / "releases.json"
CANDIDATES = [os.environ.get("LOOMGROUND_RELEASES", ""),
              HERE.parent / "loomground-repos" / "Loomground Core" / "RELEASES.json"]


def upstream() -> Path:
    for c in CANDIDATES:
        if c and Path(c).is_file():
            return Path(c)
    pytest.skip(f"loomground RELEASES.json at {SOURCE['commit'][:7]} not found (set LOOMGROUND_RELEASES)")


def test_vendored_releases_matches_upstream():
    assert VENDORED.read_bytes() == upstream().read_bytes()
