# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Each solver_* skill tool agrees with its skill script: the same JSON on stdin, the same JSON out.

The scripts live in the loomground-solver checkout, not the wheel: ``LOOMGROUND_SOLVER_SKILLS`` names its
``skills/`` directory (CI fetches the pinned commit); a sibling checkout is found by convention; otherwise skip.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import SOLVER_SAMPLES, call

HERE = Path(__file__).resolve().parents[1]
CANDIDATES = [os.environ.get("LOOMGROUND_SOLVER_SKILLS", ""),
              HERE.parent / "loomground-repos" / "loomground-solver" / "skills",
              HERE.parent / "loomground-solver" / "skills"]


def skills_dir() -> Path:
    for c in CANDIDATES:
        if c and (Path(c) / "analyse-risks" / "scripts" / "run.py").is_file():
            return Path(c)
    pytest.skip("loomground-solver skills checkout not found (set LOOMGROUND_SOLVER_SKILLS)")


@pytest.mark.parametrize("tool", sorted(SOLVER_SAMPLES))
def test_tool_matches_script(tool):
    skill, script, sample = SOLVER_SAMPLES[tool]
    path = skills_dir() / skill / "scripts" / script
    proc = subprocess.run([sys.executable, str(path)], input=json.dumps(sample), capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    env = call(tool, sample)
    assert env["ok"] is True
    assert json.loads(proc.stdout) == env["result"]


def test_script_error_is_tool_error():
    path = skills_dir() / "analyse-risks" / "scripts" / "run.py"
    sample = {"method": "no-such-method", "vectors": {"a": [1]}}
    proc = subprocess.run([sys.executable, str(path)], input=json.dumps(sample), capture_output=True, text=True)
    env = call("solver_analyse_risks", sample)
    assert proc.returncode == 2 and env["ok"] is False and env["error"]["type"] == "KeyError"
