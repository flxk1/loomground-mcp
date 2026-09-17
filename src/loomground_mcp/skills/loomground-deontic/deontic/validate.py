#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Validate a deontic statement with the engine bundled with this skill.

Usage:
  python3 validate.py "O(controller : implement TOMs)"
  python3 validate.py --file statement.deo

Prints `WELL-FORMED` and the projection, or `REJECTED (parse|validate): reason`.
The bundled engine (deontic_engine.py) is the checker; this script only runs it.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deontic_engine as eng  # noqa: E402


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--file":
        with open(argv[1], encoding="utf-8") as fh:
            source = fh.read().strip()
    else:
        source = argv[0]
    try:
        formula = eng.parse(source)
    except eng.DeonticSyntaxError as exc:
        print(f"REJECTED (parse): {exc}")
        return 1
    report = eng.validate(formula)
    if not report["ok"]:
        print(f"REJECTED (validate): {'; '.join(report['errors'])}")
        return 1
    print("WELL-FORMED")
    print(json.dumps(eng.project(formula), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
