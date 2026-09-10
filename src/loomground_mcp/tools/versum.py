# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""loomground-versum: index a folder, read its span-anchored claims, search them; admit one source, curate
(suggest → confirm) and build the coordinate canon."""
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


def _queue_path(folder: str) -> Path:
    p = _folder(folder) / ".versum" / "curation" / "suggested_concepts.csv"
    if not p.is_file():
        raise Unavailable(f"{folder} has no .versum/curation queue; run versum_suggest first")
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


@tool(PLANE, "versum.write.capture_file")
def versum_capture(folder: str, source_path: str, profile: str = "generic") -> dict[str, Any]:
    """Admit one local source (.txt/.md/.pdf) into <folder>: identity → dedupe → stub + sidecar → re-index. Returns the capture report (status admitted|duplicate, urn, claim_count, index); an unsupported or unreadable source is a CaptureError."""
    from versum.write import capture_file
    return capture_file(source_path, str(_folder(folder)), profile)


@tool(PLANE, "versum.concept.curate.suggest_folder")
def versum_suggest(folder: str, min_sources: int = 1) -> dict[str, Any]:
    """Propose concepts from definitions and cross-source recurrence and link claims to them by mention, into <folder>/.versum/curation (never the graph). Returns the queue counts plus the candidates with at least `min_sources` distinct sources, for versum_confirm to pick from."""
    from versum.concept.curate import suggest_folder
    _claims_path(folder)
    report = suggest_folder(str(_folder(folder)))
    rows = _rows(_queue_path(folder))
    for r in rows:
        for k in ("n_claims", "n_sources"):
            r[k] = int(r[k])
    return {**report, "min_sources": min_sources, "candidates": [r for r in rows if r["n_sources"] >= min_sources]}


@tool(PLANE, "versum.concept.curate.confirm_folder")
def versum_confirm(folder: str, concept_ids: Optional[list[str]] = None, min_sources: int = 1) -> dict[str, Any]:
    """Promote suggested concepts into <folder>/.versum/concepts.csv + semantic_edges.csv: an explicit `concept_ids` pick, else every candidate with at least `min_sources` sources (2 = convergent only). Requires versum_suggest first."""
    from versum.concept.curate import confirm_folder
    _queue_path(folder)
    picked = {c.strip() for c in concept_ids if c.strip()} if concept_ids else None
    return confirm_folder(str(_folder(folder)), min_sources, picked)


@tool(PLANE, "versum.concept.canon.curate_kg / curate_domain_folder")
def versum_canon(folder: str, config: Optional[str] = None, m_max: int = 1) -> dict[str, Any]:
    """Cluster claims into the coordinate-identity canon and (over)write the concept tables. `config` (a sync config path) or a materialised KG root (`by-domain/`) curates the whole KG into canon.json + convergence.json; a by-domain folder (`claims.csv`) or a plain index (`.versum/claims.csv`) curates that one folder in place."""
    from versum.concept.canon import curate_domain_folder, curate_kg
    if config:
        return {"layout": "kg", **curate_kg(config, m_max=m_max)}
    root = _folder(folder)
    if (root / "by-domain").is_dir():
        return {"layout": "kg", **curate_kg({"kg_root": str(root)}, m_max=m_max)}
    if (root / "claims.csv").is_file():
        return {"layout": "domain", **curate_domain_folder(root, m_max=m_max)}
    _claims_path(folder)
    return {"layout": "index", **curate_domain_folder(root / ".versum", domain=root.name, m_max=m_max)}


TOOLS = [versum_index, versum_claims, versum_search, versum_capture, versum_suggest, versum_confirm, versum_canon]
