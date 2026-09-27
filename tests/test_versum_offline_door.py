# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The offline door (OPTION a): `confirm=True` on versum_capture/confirm/canon writes only into a
LOCAL, UNSIGNED working folder, never the governed (signed) graph. Dry-run stays the untouched
default. No tool description may claim the write is governed, chained, signed or receipted."""
import asyncio
import os
import re

import pytest
from mcp import Client

from conftest import call
from loomground_mcp import build_server

CLAIM_WORDS = re.compile(r"\b(governed|signed|chain\w*|receipt\w*)\b", re.IGNORECASE)


def _listing(root):
    """Relative path + size, so a pre-existing empty scaffold file that gets populated counts
    as changed, not merely as an already-there name."""
    return sorted(
        (os.path.relpath(os.path.join(dirpath, name), root), os.path.getsize(os.path.join(dirpath, name)))
        for dirpath, _, names in os.walk(root) for name in names
    )


def _under(path, working_folder):
    return os.path.commonpath([os.path.abspath(path), os.path.abspath(working_folder)]) == os.path.abspath(working_folder)


# --- versum_capture ---------------------------------------------------------

def test_capture_dry_run_writes_nothing(policy_folder, tmp_path):
    src = tmp_path / "inbox"; src.mkdir()
    (src / "policy.md").write_text("The controller must notify the authority within 72 hours.\n", encoding="utf-8")
    before = _listing(policy_folder)
    env = call("versum_capture", {"folder": policy_folder, "source_path": str(src / "policy.md"), "profile": "law-eu"})
    r = env["result"]
    assert r["dry_run"] is True
    assert r["governed"] is False and r["signed"] is False
    assert "working_folder" not in r  # nothing was written, so nothing to point at
    assert before == _listing(policy_folder)


def test_capture_confirm_is_local_unsigned(policy_folder, tmp_path):
    src = tmp_path / "inbox"; src.mkdir()
    (src / "policy.md").write_text("The controller must notify the authority within 72 hours.\n", encoding="utf-8")
    before = _listing(policy_folder)
    env = call("versum_capture", {"folder": policy_folder, "source_path": str(src / "policy.md"),
                                   "profile": "law-eu", "confirm": True})
    r = env["result"]
    assert r["dry_run"] is False
    assert r["governed"] is False and r["signed"] is False
    assert r["working_folder"] == os.path.abspath(policy_folder)
    assert isinstance(r.get("note"), str) and r["note"]
    after = _listing(policy_folder)
    new_files = set(after) - set(before)
    assert new_files  # confirm=True does write
    assert all(_under(os.path.join(policy_folder, f), r["working_folder"]) for f, _ in new_files)


# --- versum_confirm ----------------------------------------------------------

def test_confirm_dry_run_writes_nothing(corpus_folder):
    call("versum_index", {"folder": corpus_folder, "profile": "law-eu"})
    call("versum_suggest", {"folder": corpus_folder})
    before = _listing(corpus_folder)
    env = call("versum_confirm", {"folder": corpus_folder, "min_sources": 2})
    r = env["result"]
    assert r["dry_run"] is True
    assert r["governed"] is False and r["signed"] is False
    assert "working_folder" not in r
    assert before == _listing(corpus_folder)


def test_confirm_confirm_is_local_unsigned(corpus_folder):
    call("versum_index", {"folder": corpus_folder, "profile": "law-eu"})
    call("versum_suggest", {"folder": corpus_folder})
    before = _listing(corpus_folder)
    env = call("versum_confirm", {"folder": corpus_folder, "min_sources": 2, "confirm": True})
    r = env["result"]
    assert r["dry_run"] is False
    assert r["governed"] is False and r["signed"] is False
    expected = os.path.abspath(os.path.join(corpus_folder, ".versum"))
    assert r["working_folder"] == expected
    assert isinstance(r.get("note"), str) and r["note"]
    after = _listing(corpus_folder)
    new_files = set(after) - set(before)
    assert new_files
    assert all(_under(os.path.join(corpus_folder, f), r["working_folder"]) for f, _ in new_files)


# --- versum_canon -------------------------------------------------------------

def test_canon_dry_run_writes_nothing(corpus_folder):
    call("versum_index", {"folder": corpus_folder, "profile": "law-eu"})
    before = _listing(corpus_folder)
    env = call("versum_canon", {"folder": corpus_folder})
    r = env["result"]
    assert r["dry_run"] is True
    assert r["governed"] is False and r["signed"] is False
    assert "working_folder" not in r
    assert before == _listing(corpus_folder)


def test_canon_confirm_is_local_unsigned_index_layout(corpus_folder):
    call("versum_index", {"folder": corpus_folder, "profile": "law-eu"})
    before = _listing(corpus_folder)
    env = call("versum_canon", {"folder": corpus_folder, "confirm": True})
    r = env["result"]
    assert r["dry_run"] is False and r["layout"] == "index"
    assert r["governed"] is False and r["signed"] is False
    expected = os.path.abspath(os.path.join(corpus_folder, ".versum"))
    assert r["working_folder"] == expected
    assert isinstance(r.get("note"), str) and r["note"]
    after = _listing(corpus_folder)
    new_files = set(after) - set(before)
    assert new_files
    assert all(_under(os.path.join(corpus_folder, f), r["working_folder"]) for f, _ in new_files)


def test_canon_confirm_is_local_unsigned_kg_layout(tmp_path):
    import csv
    kg = tmp_path / "kg"
    dom = kg / "by-domain" / "dom-a"; dom.mkdir(parents=True)
    cols = ["canonical_urn", "library", "item_id", "source_urn", "text", "polarity", "predicate", "modality", "quantification"]
    with (dom / "claims.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
        w.writerow(dict(zip(cols, ["urn:x:1", "lib", "i1", "urn:x:1", "A 'processor' duty.", "N", "obligation", "req", "null"])))
        w.writerow(dict(zip(cols, ["urn:x:2", "lib", "i2", "urn:x:2", "The 'processor' duty recurs.", "N", "obligation", "req", "null"])))

    before = _listing(kg)
    env = call("versum_canon", {"folder": str(kg), "confirm": True})
    r = env["result"]
    assert r["dry_run"] is False and r["layout"] == "kg"
    assert r["governed"] is False and r["signed"] is False
    assert r["working_folder"] == os.path.abspath(kg)
    assert isinstance(r.get("note"), str) and r["note"]
    after = _listing(kg)
    new_files = set(after) - set(before)
    assert new_files
    assert all(_under(os.path.join(kg, f), r["working_folder"]) for f, _ in new_files)


# --- tool descriptions make no governed/signed-write claim --------------------

def test_tool_descriptions_make_no_governed_write_claim():
    async def go():
        async with Client(build_server()) as client:
            return (await client.list_tools()).tools
    tools = asyncio.run(go())
    watched = {"versum_capture", "versum_confirm", "versum_canon"}
    checked = 0
    for t in tools:
        if t.name in watched:
            checked += 1
            for m in CLAIM_WORDS.finditer(t.description):
                # the only permitted use is stating explicitly that the write is NOT governed/signed
                window = t.description[max(0, m.start() - 40):m.end() + 40].lower()
                assert "not" in window or "never" in window or "false" in window, (
                    f"{t.name} description makes an unqualified governed/signed/chain/receipt claim: {window!r}")
    assert checked == len(watched)
