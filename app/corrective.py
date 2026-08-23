"""Bounded, deterministic corrective retrieval helpers for V0.6."""

from __future__ import annotations

import re
from typing import Any, Sequence

QUERY_EXPANSIONS: dict[str, str] = {
    "陌生扣款": "unauthorized credit card transaction dispute charge",
    "不认识的消费": "unrecognized credit card transaction unauthorized use",
    "账单错误": "credit card billing error statement dispute",
    "账单有误": "credit card billing error statement dispute",
    "重复收费": "duplicate credit card charge billing error",
    "投诉流程": "CFPB consumer complaint submission process",
    "提交投诉": "CFPB submit consumer complaint process",
    "billing error": "credit card statement dispute Regulation Z 1026.13",
    "unauthorized transaction": "credit card unauthorized use dispute charge",
}


def build_retry_query(question: str) -> tuple[str, str]:
    normalized = " ".join(question.split())
    lower = normalized.lower()
    expansions = [value for key, value in QUERY_EXPANSIONS.items() if key.lower() in lower]
    if expansions:
        return f"{normalized} {' '.join(expansions)}", "domain_term_expansion"
    # A conservative fallback removes conversational filler without inventing
    # facts; the retry budget remains one.
    stripped = re.sub(r"\b(please|could you|can you|请问|请帮我|我想知道)\b", " ", normalized, flags=re.IGNORECASE)
    stripped = " ".join(stripped.split())
    return stripped, "filler_normalization"


def grade_evidence(hits: Sequence[Any]) -> dict[str, Any]:
    official = [hit for hit in hits if hit.source_type in {"guidance", "regulation"}]
    underlying_scores = [
        float(value)
        for hit in hits
        for value in (hit.metadata.get("dense_score"), hit.metadata.get("bm25_score"), hit.score)
        if value is not None
    ]
    max_score = max(underlying_scores, default=0.0)
    official_scores = [
        float(value)
        for hit in official
        for value in (hit.metadata.get("dense_score"), hit.metadata.get("bm25_score"), hit.score)
        if value is not None
    ]
    official_max_score = max(official_scores, default=0.0)
    uses_rrf = any(str(hit.metadata.get("retrieval_method")) == "rrf" for hit in hits)
    score_floor = 0.35
    sufficient = bool(official) and len(hits) >= 2 and official_max_score >= score_floor
    reasons: list[str] = []
    if not official:
        reasons.append("no_official_evidence")
    if len(hits) < 2:
        reasons.append("too_few_candidates")
    if max_score < score_floor:
        reasons.append("low_relevance_score")
    if official and official_max_score < score_floor:
        reasons.append("official_evidence_low_relevance")
    return {
        "sufficient": sufficient,
        "official_count": len(official),
        "hit_count": len(hits),
        "max_score": round(max_score, 6),
        "official_max_score": round(official_max_score, 6),
        "score_floor": score_floor,
        "score_semantics": "underlying_dense_or_sparse" if uses_rrf else "retriever",
        "reasons": reasons,
    }
