# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""loomground: the family catalogue — every repository as a record, the pipeline order, and how documents
become an ``.lg`` patch.

``catalogue.json`` is ``CATALOGUE.json`` from the loomground repository at ``SOURCE_COMMIT``, vendored byte for
byte (``tests/test_catalogue_parity.py`` checks it against a checkout). ``query`` filters the records only.
"""
import json
from importlib import resources
from typing import Any, Optional

from ._result import tool

PLANE = "loomground"
SOURCE = {"repo": "https://github.com/flxk1/loomground", "commit": "782e745be23bbd12a5a067e4b67b889d10037faf"}
FIELDS = ("repo", "family", "role", "tools", "skills")


def load() -> dict[str, Any]:
    return json.loads(resources.files("loomground_mcp").joinpath("catalogue.json").read_text(encoding="utf-8"))


def _haystack(record: dict[str, Any]) -> str:
    parts = []
    for f in FIELDS:
        v = record.get(f)
        parts.extend(v if isinstance(v, list) else [str(v)])
    return "\n".join(parts).lower()


@tool(PLANE, "CATALOGUE.json")
def loomground_catalogue(query: Optional[str] = None) -> dict[str, Any]:
    """The Loomground family map: `repos` (one record per repository: repo, family, role, description, pipeline_position, depends_on, tools, skills, install, url), `pipeline` (source → ingest → versum → solver → applied | diagnostic, with the tool at each step) and `patch_from_documents` (how documents become an .lg patch). Call it first. `query` is a case-insensitive substring over repo, family, role, tools and skills and filters `repos` only."""
    doc = load()
    repos = doc["repos"]
    if query:
        needle = query.lower()
        repos = [r for r in repos if needle in _haystack(r)]
    return {"repos": repos, "pipeline": doc["pipeline"], "patch_from_documents": doc["patch_from_documents"],
            "source": dict(SOURCE)}


TOOLS = [loomground_catalogue]
