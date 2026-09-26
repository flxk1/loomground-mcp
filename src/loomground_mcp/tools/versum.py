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


def _capture_preview(folder: str, source_path: str, profile: str) -> dict[str, Any]:
    """Everything capture_file does up to (not including) the write: validate, resolve identity,
    check dedupe against the folder's existing registry. Writes nothing; the folder is untouched."""
    from versum.write import _validated_source, content_hash, dedup, load_registry, resolve_identity
    source, profile_obj = _validated_source(source_path, profile)
    folder_path = _folder(folder)
    registry = load_registry(folder_path)
    ident = resolve_identity(source, profile_obj)
    sha1 = content_hash(source)
    hit = dedup(registry, ident.urn, sha1, ident.title)
    if hit:
        reason, existing = hit
        return {"status": "duplicate", "admitted": False, "reason": reason, "profile": profile,
                "source_path": str(source), "target_path": existing.get("path", ""), "urn": ident.urn,
                "existing_urn": existing.get("urn")}
    return {"status": "would_admit", "admitted": False, "profile": profile, "source_path": str(source),
            "urn": ident.urn, "method": ident.method, "title": ident.title}


@tool(PLANE, "versum.write.capture_file")
def versum_capture(folder: str, source_path: str, profile: str = "generic", confirm: bool = False) -> dict[str, Any]:
    """Admit one local source (.txt/.md/.pdf) into <folder>: identity → dedupe → stub + sidecar → re-index. A
    graph write, so this is a dry run by default — it validates, resolves identity, checks dedupe, and writes
    nothing; pass `confirm=True` to actually admit. Returns the capture report (status admitted|duplicate|would_admit,
    urn, claim_count, index) plus `dry_run`; an unsupported or unreadable source is a CaptureError either way."""
    if not confirm:
        return {**_capture_preview(folder, source_path, profile), "dry_run": True}
    from versum.write import capture_file
    return {**capture_file(source_path, str(_folder(folder)), profile), "dry_run": False}


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


def _confirm_preview(folder: str, concept_ids: Optional[list[str]], min_sources: int) -> dict[str, Any]:
    """What confirm_folder would keep, computed by the same filter it applies, without saving concepts.csv /
    semantic_edges.csv."""
    from versum.store import graph as g
    q = _folder(folder) / ".versum" / "curation"
    sc = _rows(q / "suggested_concepts.csv")
    se = g.load_edges(q / "suggested_edges.csv")
    only_concepts = {c.strip() for c in concept_ids if c.strip()} if concept_ids else None
    keep = {c["concept_id"] for c in sc
            if (only_concepts and c["concept_id"] in only_concepts)
            or (not only_concepts and int(c["n_sources"]) >= min_sources)}
    edges = [e for e in se if e["dst_id"] in keep]
    return {"n_concepts": len(keep), "n_edges": len(edges), "concept_ids": sorted(keep)}


@tool(PLANE, "versum.concept.curate.confirm_folder")
def versum_confirm(folder: str, concept_ids: Optional[list[str]] = None, min_sources: int = 1,
                    confirm: bool = False) -> dict[str, Any]:
    """Promote suggested concepts into <folder>/.versum/concepts.csv + semantic_edges.csv: an explicit `concept_ids`
    pick, else every candidate with at least `min_sources` sources (2 = convergent only). Requires versum_suggest
    first. A graph write, so this is a dry run by default — it reports which concepts/edges would be kept and writes
    nothing; pass `confirm=True` to actually promote them. Returns the same counts (n_concepts, n_edges, concept_ids)
    plus `dry_run`."""
    _queue_path(folder)
    if not confirm:
        return {**_confirm_preview(folder, concept_ids, min_sources), "dry_run": True}
    from versum.concept.curate import confirm_folder
    picked = {c.strip() for c in concept_ids if c.strip()} if concept_ids else None
    return {**confirm_folder(str(_folder(folder)), min_sources, picked), "dry_run": False}


def _canon_domain_preview(folder: Path, domain: str, m_max: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """What curate_domain_folder would compute (build_canon is pure — no write), without writing
    concepts.csv / semantic_edges.csv / canon.partial.json. Returns (summary, canon) so a kg-level
    preview can merge the canons."""
    from versum.concept.canon import build_canon
    claims = _rows(folder / "claims.csv")
    domain = domain or folder.name
    for c in claims:
        c.setdefault("domain", domain)
    canon = build_canon(claims, m_max=m_max, domain_of=lambda c: c.get("domain", domain))
    summary = {"domain": domain, "n_claims": canon["n_claims"], "n_sources": canon["n_sources"],
               "n_concepts": len(canon["concepts"]), "n_edges": len(canon["edges"]),
               "n_unclustered": canon.get("n_unclustered", 0)}
    return summary, canon


def _canon_kg_preview(root: Path, m_max: int) -> dict[str, Any]:
    """What curate_kg would compute over a materialised by-domain/ root, without writing any per-domain
    table, canon.partial.json, canon.json or convergence.json."""
    from versum.concept.canon import domain_partial, merge_partials
    domains = sorted(p for p in root.iterdir() if p.is_dir() and (p / "claims.csv").is_file())
    partials, per_domain = [], []
    for d in domains:
        summary, canon = _canon_domain_preview(d, d.name, m_max)
        per_domain.append(summary)
        partials.append(domain_partial(canon, d.name))
    merged = merge_partials(partials)
    return {"n_domains": len(domains), "n_concepts": merged["n_concepts"], "n_claims": merged["n_claims"],
            "n_unclustered": merged["n_unclustered"], "clustered_rate": merged["clustered_rate"],
            "n_sources": merged["n_sources"], "canon_by_domain": merged["canon_by_domain"],
            "per_domain": per_domain}


@tool(PLANE, "versum.concept.canon.curate_kg / curate_domain_folder")
def versum_canon(folder: str, config: Optional[str] = None, m_max: int = 1, confirm: bool = False) -> dict[str, Any]:
    """Cluster claims into the coordinate-identity canon and (over)write the concept tables. `config` (a sync config
    path) or a materialised KG root (`by-domain/`) curates the whole KG into canon.json + convergence.json; a
    by-domain folder (`claims.csv`) or a plain index (`.versum/claims.csv`) curates that one folder in place. The
    curation run IS a graph write, so this is a dry run by default — it clusters and reports the counts it would
    write and writes nothing; pass `confirm=True` to actually (over)write the tables. Returns the same counts
    (layout plus n_concepts/n_domains/etc.) plus `dry_run`."""
    from versum.concept.canon import curate_domain_folder, curate_kg
    if config:
        if not confirm:
            from versum.sync import load_config
            cfg = load_config(config) if isinstance(config, str) else config
            kg_root = Path(cfg["kg_root"]).expanduser()
            root = kg_root / "by-domain" if (kg_root / "by-domain").is_dir() else kg_root
            return {"layout": "kg", **_canon_kg_preview(root, m_max), "dry_run": True}
        return {"layout": "kg", **curate_kg(config, m_max=m_max), "dry_run": False}
    root = _folder(folder)
    if (root / "by-domain").is_dir():
        if not confirm:
            return {"layout": "kg", **_canon_kg_preview(root / "by-domain", m_max), "dry_run": True}
        return {"layout": "kg", **curate_kg({"kg_root": str(root)}, m_max=m_max), "dry_run": False}
    if (root / "claims.csv").is_file():
        if not confirm:
            summary, _ = _canon_domain_preview(root, "", m_max)
            return {"layout": "domain", **summary, "dry_run": True}
        return {"layout": "domain", **curate_domain_folder(root, m_max=m_max), "dry_run": False}
    _claims_path(folder)
    if not confirm:
        summary, _ = _canon_domain_preview(root / ".versum", root.name, m_max)
        return {"layout": "index", **summary, "dry_run": True}
    return {"layout": "index", **curate_domain_folder(root / ".versum", domain=root.name, m_max=m_max), "dry_run": False}


TOOLS = [versum_index, versum_claims, versum_search, versum_capture, versum_suggest, versum_confirm, versum_canon]
