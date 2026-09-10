# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""loomground-versum: index a folder, read its span-anchored claims, search them."""
import csv
from pathlib import Path
from typing import Any, Optional

from ._result import Unavailable, tool

PLANE = "loomground-versum"
_INT = ("span_start", "span_end")


def _folder(folder: str) -> Path:
    p = Path(folder).expanduser()
    if not p.is_dir():
        raise FileNotFoundError(f"not a directory: {folder}")
    return p


def _claims_path(folder: str) -> Path:
    p = _folder(folder) / ".versum" / "claims.csv"
    if not p.is_file():
        raise Unavailable(f"{folder} has no .versum/claims.csv; run versum_index first")
    return p


def _rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k in _INT:
            if r.get(k, "").lstrip("-").isdigit():
                r[k] = int(r[k])
    return rows


@tool(PLANE, "versum.store.index.index_folder")
def versum_index(folder: str, profile: str = "generic") -> dict[str, Any]:
    """Index a folder of documents into <folder>/.versum (span claims, concepts, nD). Returns the index summary."""
    from versum.store.index import index_folder
    return index_folder(str(_folder(folder)), profile)


@tool(PLANE, "<folder>/.versum/claims.csv")
def versum_claims(folder: str, limit: int = 100) -> dict[str, Any]:
    """Rows of the folder's claims.csv, each with source_urn, span_start, span_end, marker, text and the projected predicates."""
    rows = _rows(_claims_path(folder))
    return {"columns": list(rows[0].keys()) if rows else [], "n_total": len(rows), "rows": rows[:max(limit, 0)]}


@tool(PLANE, "versum.store.retrieve.SearchIndex / from_kg")
def versum_search(folder: str, query: str, k: int = 10, filters: Optional[dict[str, str]] = None) -> dict[str, Any]:
    """Search the folder's claims. A materialised KG (by-domain/) uses versum's hybrid index; a plain .versum index uses versum's BM25 over its claim rows."""
    from versum.store.retrieve import Doc, SearchIndex, from_kg
    root = _folder(folder)
    kg = root / "by-domain"
    if kg.is_dir():
        hits = from_kg(root).search(query, filters=filters or {}, k=k)
        return {"layout": "kg", "hits": hits}
    rows = _rows(_claims_path(folder))
    if not rows:
        raise Unavailable(f"{folder}/.versum/claims.csv holds no claims; nothing to search")
    docs = [Doc(doc_id=f"claim:{r['item_id']}", type="claim", text=r.get("text", ""),
                canonical_urn=r.get("source_urn", ""),
                facets={"type": "claim", "polarity": r.get("polarity", ""), "predicate": r.get("predicate", ""),
                        "dimension": r.get("dimension", ""), "modality": r.get("modality", ""),
                        "marker": r.get("marker", ""), "unit_id": r.get("unit_id", "")})
            for r in rows if r.get("item_id")]
    spans = {f"claim:{r['item_id']}": {"span_start": r.get("span_start"), "span_end": r.get("span_end")} for r in rows}
    hits = SearchIndex(docs).search(query, filters=filters or {}, k=k)
    for h in hits:
        h.update(spans.get(h.get("doc_id", ""), {}))
    return {"layout": "index", "retrieval": "bm25", "hits": hits}


TOOLS = [versum_index, versum_claims, versum_search]
