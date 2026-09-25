# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""loomground: the family's release/pin register — every repository's released version, tag and commit, and every
dependency edge with its range, development pin and status.

``releases.json`` is ``RELEASES.json`` from the loomground repository at ``SOURCE["commit"]``, vendored byte for
byte (``tests/test_releases_parity.py`` checks it against a checkout). ``repo`` narrows to one record and its edges.
"""
import json
from importlib import resources
from typing import Any, Optional

from ._result import Unavailable, tool

PLANE = "loomground"
SOURCE = {"repo": "https://github.com/flxk1/loomground", "commit": "d7144d75f901641af652e5a1842f67dd85dd8c87"}


def load() -> dict[str, Any]:
    return json.loads(resources.files("loomground_mcp").joinpath("releases.json").read_text(encoding="utf-8"))


def _names(repo: str, edge: dict[str, Any]) -> bool:
    return repo in (edge["consumer"], edge["dependency"])


@tool(PLANE, "RELEASES.json")
def loomground_releases(repo: Optional[str] = None) -> dict[str, Any]:
    """The Loomground release/pin register: `repos` (one record per repository: version, tag, commit, package, pypi; tag and commit are null while nothing is released), `edges` (one per dependency: consumer, dependency, range, dev_pin, dev_pin_release, status ∈ release | unreleased-commit | out-of-range | missing-range), `accepted` (edges allowed while the dependency has no release), `skipped` (private repositories), `generated`, `source`. With `repo`: that repository's `record` and every edge naming it as consumer or dependency; an unknown repo is `unavailable`."""
    doc = load()
    if repo is None:
        return {"generated": doc["generated"], "repos": doc["repos"], "edges": doc["edges"], "accepted": doc["accepted"],
                "skipped": doc["skipped"], "source": dict(SOURCE)}
    if repo not in doc["repos"]:
        raise Unavailable(f"{repo!r} is not in the register; repos: {', '.join(sorted(doc['repos']))}")
    return {"repo": repo, "record": doc["repos"][repo], "edges": [e for e in doc["edges"] if _names(repo, e)],
            "accepted": [a for a in doc["accepted"] if _names(repo, a)], "source": dict(SOURCE)}


TOOLS = [loomground_releases]
