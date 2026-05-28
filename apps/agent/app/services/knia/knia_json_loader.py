from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from app.services.knia.knia_json_media_extractor import extract_media_from_json
from app.services.knia.knia_json_parser import build_rag_chunks_from_document, parse_visible_items_to_menu_nodes
from app.services.knia.knia_json_repository import (
    fail_import_run,
    finish_import_run,
    replace_reference_chunks,
    start_import_run,
    upsert_media_assets,
    upsert_myaccident_page,
    upsert_knia_fault_charts,
    upsert_reference_document,
)
from app.services.knia.knia_json_vectorizer import rebuild_knia_json_embeddings

DEFAULT_CANDIDATES = [
    "/app/project_scripts/knia_fault_ratio/knia_fault_ratio.json",
    "/app/project_scripts/knia_fault_ratio.json",
    "/app/scripts/knia_fault_ratio/knia_fault_ratio.json",
    "/app/scripts/knia_fault_ratio.json",
    "scripts/knia_fault_ratio/knia_fault_ratio.json",
    "scripts/knia_fault_ratio.json",
    "../../scripts/knia_fault_ratio/knia_fault_ratio.json",
    "../../scripts/knia_fault_ratio.json",
]


def resolve_knia_json_path(path: str | None = None) -> Path:
    candidates = []
    if path:
        candidates.append(path)
    env_path = os.getenv("KNIA_FAULT_RATIO_JSON_PATH")
    if env_path:
        candidates.append(env_path)
    candidates.extend(DEFAULT_CANDIDATES)
    checked: list[str] = []
    for item in candidates:
        p = Path(item)
        checked.append(str(p))
        if p.exists() and p.is_file():
            return p.resolve()
    raise FileNotFoundError("KNIA JSON 파일을 찾을 수 없습니다. 확인 경로: " + ", ".join(checked))


def compute_file_hash(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_knia_json_file(path: str | None = None) -> dict[str, Any]:
    resolved = resolve_knia_json_path(path)
    with resolved.open("r", encoding="utf-8") as f:
        data = json.load(f)
    warnings = validate_knia_json(data)
    data["_resolved_path"] = str(resolved)
    data["_file_hash"] = compute_file_hash(resolved)
    data["_validation_warnings"] = warnings
    return data


def validate_knia_json(data: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        raise ValueError("KNIA JSON root must be an object")
    if not isinstance(data.get("metadata"), dict):
        raise ValueError("metadata가 필요합니다")
    if not isinstance(data.get("pages"), list):
        raise ValueError("pages 배열이 필요합니다")
    if not isinstance(data.get("rag_documents"), list):
        raise ValueError("rag_documents 배열이 필요합니다")
    warnings: list[dict[str, Any]] = []
    for index, chart in enumerate(data.get("charts") or []):
        if not isinstance(chart, dict):
            warnings.append({"section": "charts", "index": index, "field": "*", "message": "chart must be an object"})
            continue
        for field in CHART_REQUIRED_FIELDS:
            if _missing(chart, field):
                warnings.append({"section": "charts", "index": index, "chart_no": chart.get("chart_no"), "field": field, "message": "required field missing"})
    if data.get("charts"):
        for index, doc in enumerate(data.get("rag_documents") or []):
            if not isinstance(doc, dict):
                warnings.append({"section": "rag_documents", "index": index, "field": "*", "message": "rag_document must be an object"})
                continue
            for field in RAG_DOCUMENT_REQUIRED_FIELDS:
                if _missing(doc, field):
                    warnings.append({"section": "rag_documents", "index": index, "doc_id": doc.get("doc_id"), "field": field, "message": "required field missing"})
    return warnings


def import_knia_json(path: str | None = None, rebuild_chunks: bool = True, force: bool = False, rebuild_embeddings: bool = False) -> dict[str, Any]:
    data = load_knia_json_file(path)
    metadata = data.get("metadata", {})
    source_path = data["_resolved_path"]
    file_hash = data["_file_hash"]
    run_id = start_import_run(source_path, file_hash, metadata)
    validation_warnings = data.get("_validation_warnings") or []
    stats = {
        "imported_pages": 0,
        "imported_documents": 0,
        "imported_menu_nodes": 0,
        "imported_media_assets": 0,
        "imported_chunks": 0,
        "charts_total": len(data.get("charts") or []),
        "charts_imported": 0,
        "charts_review_required": 0,
        "rag_documents_total": len(data.get("rag_documents") or []),
        "rag_documents_imported": 0,
        "skipped_count": 0,
        "validation_warnings_count": len(validation_warnings),
    }
    try:
        if data.get("charts"):
            chart_stats = upsert_knia_fault_charts(file_hash, data.get("charts") or [])
            stats["charts_imported"] += chart_stats.get("charts_imported", 0)
            stats["charts_review_required"] += chart_stats.get("charts_review_required", 0)
            stats["skipped_count"] += chart_stats.get("charts_skipped", 0)

        is_structured_review_json = bool(data.get("charts"))
        for page in data.get("pages", []):
            page_result = upsert_myaccident_page(page, file_hash)
            if page_result.get("page_id"):
                stats["imported_pages"] += 1
                nodes = parse_visible_items_to_menu_nodes(page)
                node_count = page_result["upsert_nodes"](nodes, file_hash)
                stats["imported_menu_nodes"] += node_count

        for doc in data.get("rag_documents", []):
            if is_structured_review_json and _should_skip_structured_rag_document(doc):
                stats["skipped_count"] += 1
                continue
            doc_result = upsert_reference_document(doc, file_hash)
            stats["imported_documents"] += 1 if doc_result.get("changed", True) else 0
            stats["rag_documents_imported"] += 1
            if rebuild_chunks and (force or doc_result.get("changed", True)):
                chunks = build_rag_chunks_from_document(doc)
                stats["imported_chunks"] += replace_reference_chunks(doc.get("doc_id") or doc_result["document_id"], chunks)

        media = extract_media_from_json(data)
        stats["imported_media_assets"] = upsert_media_assets(media, file_hash)
        if rebuild_embeddings:
            emb = rebuild_knia_json_embeddings(limit=None, force=False)
            stats["embedding"] = emb
        finish_import_run(run_id, stats)
        return {"ok": True, "run_id": str(run_id), "source_file_hash": file_hash, **stats}
    except Exception as exc:
        fail_import_run(run_id, str(exc))
        raise


CHART_REQUIRED_FIELDS = (
    "chart_no",
    "title",
    "major_party_type",
    "scenario_type",
    "scenario_subtype",
    "page_start",
    "page_end",
    "vehicle_roles",
    "base_fault",
    "adjustments",
    "related_laws",
    "accident_situation",
    "base_fault_explanation",
    "usage_notes",
    "raw_text",
    "parsing_confidence",
    "review_required",
)

RAG_DOCUMENT_REQUIRED_FIELDS = (
    "doc_id",
    "chart_no",
    "major_party_type",
    "scenario_type",
    "title",
    "body",
    "page_start",
    "page_end",
    "chunk_type",
)


def _missing(item: dict[str, Any], field: str) -> bool:
    if field in {"page_start", "page_end"}:
        return item.get(field) is None and item.get(f"{field}_pdf") is None
    return item.get(field) in (None, "")


def _should_skip_structured_rag_document(doc: dict[str, Any]) -> bool:
    return not (doc.get("chart_no") and doc.get("major_party_type") and doc.get("scenario_type"))
