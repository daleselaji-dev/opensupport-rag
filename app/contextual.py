"""Deterministic contextual/parent-child preparation for V0.5.

The first V0.5 implementation deliberately avoids hiding an expensive LLM
call inside ingestion. It preserves the parent document identity, inherits
title/source metadata into child chunks, and splits long records before
embedding. This makes the improvement attributable and reversible; an
LLM-generated contextual prefix can later be compared under the same schema.
"""

from __future__ import annotations

import hashlib
from typing import Iterable

from app.schemas import SourceDocument


def contextual_prefix(document: SourceDocument) -> str:
    metadata = document.metadata
    fields = [
        f"Title: {document.title}",
        f"Source type: {document.source_type}",
        f"Authority: {document.authority_level}",
    ]
    for key in ("product", "issue", "sub_issue", "parent_title", "page"):
        value = metadata.get(key)
        if value not in (None, ""):
            fields.append(f"{key}: {value}")
    return " | ".join(fields)


def prepare_contextual_documents(
    documents: Iterable[SourceDocument],
    *,
    max_chars: int = 1800,
    overlap: int = 220,
) -> list[SourceDocument]:
    """Create traceable child chunks with deterministic contextual prefixes."""

    if max_chars <= 0 or overlap < 0 or overlap >= max_chars:
        raise ValueError("contextual chunk max_chars must be positive and overlap smaller than max_chars")
    prepared: list[SourceDocument] = []
    for document in documents:
        prefix = contextual_prefix(document)
        body_budget = max(256, max_chars - len(prefix) - 1)
        text = " ".join(document.text.split())
        parent_id = document.chunk_id
        parent_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        if len(text) <= body_budget:
            metadata = dict(document.metadata)
            metadata.update(
                {
                    "contextual_prefix": prefix,
                    "parent_chunk_id": parent_id,
                    "chunk_index": 0,
                    "chunk_count": 1,
                    "contextual_strategy": "deterministic_parent_context",
                }
            )
            prepared.append(document.model_copy(update={"text": f"{prefix}\n{text}", "metadata": metadata}))
            continue

        starts = list(range(0, len(text), body_budget - overlap))
        chunks: list[str] = []
        for start in starts:
            chunk = text[start : start + body_budget].strip()
            if chunk:
                chunks.append(chunk)
            if start + body_budget >= len(text):
                break
        total = len(chunks)
        for index, chunk in enumerate(chunks):
            metadata = dict(document.metadata)
            metadata.update(
                {
                    "contextual_prefix": prefix,
                    "parent_chunk_id": parent_id,
                    "parent_text_sha256": parent_hash,
                    "chunk_index": index,
                    "chunk_count": total,
                    "contextual_strategy": "deterministic_parent_context",
                }
            )
            child_id = f"{parent_id}:child:{index}"
            prepared.append(
                document.model_copy(
                    update={
                        "chunk_id": child_id,
                        "text": f"{prefix}\n{chunk}",
                        "metadata": metadata,
                    }
                )
            )
    return prepared
