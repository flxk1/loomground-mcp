#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Validate a .lg patch with the validation engine bundled with this skill.

Usage: python3 validate.py PATCH.lg

Prints `WELL-FORMED` and the projection, or `REJECTED (parse|apply): reason`.
The bundled engine is the checker; this script only locates it.
"""
import json
import os
import sys


def _load_impl():
    try:
        import loomground
        return loomground
    except ImportError:
        pass
    here = os.path.dirname(os.path.abspath(__file__))
    # The implementation ships beside this script; PYTHONPATH may override it.
    if os.path.exists(os.path.join(here, "loomground.py")):
        sys.path.insert(0, here)
        import loomground
        return loomground
    return None


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python3 validate.py PATCH.lg")
    L = _load_impl()
    if L is None:
        sys.exit("Loomground implementation not found. loomground.py ships beside "
                 "this script; put it there or on PYTHONPATH.")
    with open(sys.argv[1], encoding="utf-8") as f:
        src = f.read()
    try:
        patch = L.check(L.parse(src))
    except L.Reject as e:
        print(f"REJECTED ({e.stage}): {e}")
        sys.exit(1)
    print("WELL-FORMED")
    print(json.dumps(L.project(patch), indent=2))


if __name__ == "__main__":
    main()
