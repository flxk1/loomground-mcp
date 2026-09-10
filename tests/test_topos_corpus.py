# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Every ```lt block in loomground-topos's examples/*.md parses with no error.

The examples live in the loomground-topos checkout: ``LOOMGROUND_TOPOS_EXAMPLES`` names its ``examples/``
directory (CI fetches the pinned commit); a sibling checkout is found by convention; otherwise skip.
"""
import os
import re
from pathlib import Path

import pytest

from conftest import call

HERE = Path(__file__).resolve().parents[1]
CANDIDATES = [os.environ.get("LOOMGROUND_TOPOS_EXAMPLES", ""),
              HERE.parent / "legal-topology-grammar" / "examples",
              HERE.parent / "loomground-topos" / "examples"]
FENCE = re.compile(r"^```lt\n(.*?)^```", re.S | re.M)


def examples_dir() -> Path:
    for c in CANDIDATES:
        if c and any(Path(c).glob("*.md")):
            return Path(c)
    pytest.skip("loomground-topos examples checkout not found (set LOOMGROUND_TOPOS_EXAMPLES)")


def test_every_lt_block_parses():
    blocks = [(p.name, i, m.group(1)) for p in sorted(examples_dir().glob("*.md"))
              for i, m in enumerate(FENCE.finditer(p.read_text(encoding="utf-8")))]
    assert blocks, "no ```lt blocks found"
    failures, n = [], 0
    for name, i, text in blocks:
        r = call("topos_parse", {"text": text})["result"]
        n += r["n_statements"]
        failures.extend((name, i, e) for e in r["errors"])
    assert failures == []
    assert n > 0 and all(s["kind"] in ("system", "organ", "level", "instrument", "competence", "rel", "assert")
                         for name, i, text in blocks for s in call("topos_parse", {"text": text})["result"]["statements"])
