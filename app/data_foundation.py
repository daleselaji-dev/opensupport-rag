"""Deterministic data foundation for OpenSupport ingestion.

The RAG index is a derived read model.  This module keeps the first part of
the ingestion contract deterministic and dependency-light so it can be used
before PostgreSQL/MinIO are available, and then persisted by the production
adapters in a later milestone.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from typing import Iterable

from app.schemas import DataQualityIssue, DataQualityReport, SourceDocument
from app.security import scan_text

PIPELINE_VERSION = "v0.0-data-foundation-1"
_CONTROL_CHARS = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]")
_SPACE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    """Collapse formatting noise without changing the evidence meaning."""

    value = _CONTROL_CHARS.sub(" ", value or "")
    value = value.replace("\u00a0", " ")
    return _SPACE.sub(" ", value).strip()


def canonical_url(value: str) -> str:
    """Remove URL fragments and harmless trailing separators for stable lineage."""

    parsed = urlsplit((value or "").strip())
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ""))


def text_hash(document: SourceDocument) -> str:
    normalized = "\n".join(
        [
            normalize_text(document.title),
            normalize_text(document.text),
            canonical_url(document.source_url),
        ]
    )
    return sha256(normalized.encode("utf-8")).hexdigest()


def normalized_text_hash(document: SourceDocument) -> str:
    return sha256(normalize_text(document.text).encode("utf-8")).hexdigest()


def detect_language(text: str) -> str:
    """Small deterministic language bucket used for routing and data QA."""

    compact = normalize_text(text)
    if not compact:
        return "unknown"
    cjk = sum("\u4e00" <= char <= "\u9fff" for char in compact)
    alpha = sum(char.isalpha() for char in compact)
    if cjk and cjk >= max(2, alpha * 0.15):
        return "zh"
    if alpha:
        return "en"
    return "other"


def _identity_key(document: SourceDocument) -> str:
    """Use source identity for complaints and URL+content for official pages."""

    if document.source_type == "complaint" and document.complaint_id:
        return f"complaint:{document.complaint_id}"
    return f"{canonical_url(document.source_url)}:{normalized_text_hash(document)}"


def normalize_document(document: SourceDocument) -> SourceDocument:
    """Return a normalized, lineage-enriched copy of a source chunk."""

    metadata = dict(document.metadata)
    normalized = document.model_copy(
        update={
            "title": normalize_text(document.title) or "Untitled source",
            "text": normalize_text(document.text),
            "source_url": canonical_url(document.source_url),
            "metadata": metadata,
        }
    )
    metadata.update(
        {
            "content_sha256": text_hash(normalized),
            "normalized_text_sha256": normalized_text_hash(normalized),
            "canonical_source_url": normalized.source_url,
            "language": detect_language(normalized.text),
            "lifecycle_status": "normalized",
            "pipeline_version": PIPELINE_VERSION,
        }
    )
    return normalized.model_copy(update={"metadata": metadata})


def validate_document(document: SourceDocument) -> list[DataQualityIssue]:
    issues: list[DataQualityIssue] = []
    if not document.chunk_id.strip():
        issues.append(DataQualityIssue(code="missing_chunk_id", severity="error", message="Chunk ID 为空"))
    if not document.source_url.startswith(("http://", "https://")):
        issues.append(DataQualityIssue(code="invalid_source_url", severity="error", message="来源 URL 不是 HTTP(S)", chunk_id=document.chunk_id, source_url=document.source_url))
    if len(normalize_text(document.text)) < 40:
        issues.append(DataQualityIssue(code="text_too_short", severity="error", message="证据文本少于 40 个字符", chunk_id=document.chunk_id, source_url=document.source_url))
    if len(normalize_text(document.text)) > 20_000:
        issues.append(DataQualityIssue(code="text_too_long", severity="warning", message="单 Chunk 超过 20,000 字符，后续需要层级切分", chunk_id=document.chunk_id, source_url=document.source_url))
    if document.source_type == "complaint" and not document.complaint_id:
        issues.append(DataQualityIssue(code="complaint_id_missing", severity="error", message="投诉 Chunk 缺少 complaint_id", chunk_id=document.chunk_id, source_url=document.source_url))
    safety = scan_text(document.text)
    if safety["pii_flags"]:
        issues.append(DataQualityIssue(code="pii_detected", severity="error", message=f"内容疑似包含敏感信息：{', '.join(safety['pii_flags'])}", chunk_id=document.chunk_id, source_url=document.source_url))
    if safety["prompt_injection_flags"]:
        issues.append(DataQualityIssue(code="prompt_injection_content", severity="warning", message="内容包含疑似提示注入指令，生成时必须视为不可信文本", chunk_id=document.chunk_id, source_url=document.source_url))
    return issues


def prepare_documents(documents: Iterable[SourceDocument]) -> tuple[list[SourceDocument], DataQualityReport]:
    """Normalize, validate and deterministically deduplicate documents."""

    raw = list(documents)
    accepted: list[SourceDocument] = []
    duplicate_ids: list[str] = []
    issues: list[DataQualityIssue] = []
    seen_identity: set[str] = set()
    seen_chunk: set[str] = set()

    for original in raw:
        document = normalize_document(original)
        document_issues = validate_document(document)
        errors = [issue for issue in document_issues if issue.severity == "error"]
        issues.extend(document_issues)
        if errors:
            continue
        identity = _identity_key(document)
        if document.chunk_id in seen_chunk or identity in seen_identity:
            duplicate_ids.append(document.chunk_id)
            continue
        seen_chunk.add(document.chunk_id)
        seen_identity.add(identity)
        accepted.append(document)

    hashes = sorted(str(document.metadata["content_sha256"]) for document in accepted)
    snapshot_id = sha256((PIPELINE_VERSION + "\n" + "\n".join(hashes)).encode("utf-8")).hexdigest()[:16]
    languages = Counter(str(document.metadata.get("language", "unknown")) for document in accepted)
    source_types = Counter(document.source_type for document in accepted)
    metadata_fields = ["product", "issue", "company", "audience", "language", "source_url"]
    coverage: dict[str, float] = {}
    for field in metadata_fields:
        populated = sum(bool(document.metadata.get(field) or getattr(document, field, None)) for document in accepted)
        coverage[field] = round(populated / len(accepted), 4) if accepted else 0.0

    stage_counts = {
        "discovered": len(raw),
        "downloaded": len(raw),
        "validated": len(raw) - len([issue for issue in issues if issue.severity == "error"]),
        "normalized": len(raw),
        "deduplicated": len(accepted),
        "quarantined": len(raw) - len(accepted) - len(duplicate_ids),
        "indexed": 0,
        "active": 0,
    }
    report = DataQualityReport(
        pipeline_version=PIPELINE_VERSION,
        snapshot_id=snapshot_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        raw_documents=len(raw),
        accepted_documents=len(accepted),
        duplicate_documents=len(duplicate_ids),
        quarantined_documents=stage_counts["quarantined"],
        languages=dict(languages),
        source_types=dict(source_types),
        stage_counts=stage_counts,
        metadata_coverage=coverage,
        issues=issues[:200],
        duplicate_chunk_ids=duplicate_ids[:200],
        notes=[
            "投诉文本是消费者主张，不是 CFPB 核实事实。",
            "Qdrant 是派生索引；PostgreSQL/MinIO 保存源快照、版本、Chunk 和索引血缘。",
        ],
    )
    return accepted, report


def finalize_quality_report(report: DataQualityReport, indexed_documents: int, batch_indexed_documents: int | None = None) -> DataQualityReport:
    stages = dict(report.stage_counts)
    stages["indexed"] = indexed_documents
    stages["active"] = indexed_documents
    return report.model_copy(update={"indexed_documents": indexed_documents, "batch_indexed_documents": batch_indexed_documents if batch_indexed_documents is not None else report.accepted_documents, "stage_counts": stages})


def save_quality_report(report: DataQualityReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")


def load_quality_report(path: Path) -> DataQualityReport | None:
    if not path.exists():
        return None
    try:
        return DataQualityReport.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
