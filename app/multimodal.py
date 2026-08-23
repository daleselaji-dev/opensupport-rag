"""Page-level PDF evidence baseline for V0.8.

This first slice preserves page provenance and extracted text. Visual table/
chart retrieval is intentionally a later A/B module; a text-only PDF page is
never labelled as visual evidence.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from pypdf import PdfReader

from app.schemas import SourceDocument


def extract_pdf_pages(path: str, *, source_url: str | None = None, title: str | None = None) -> list[SourceDocument]:
    pdf_path = Path(path)
    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        raise ValueError("只允许读取已存在的本地 PDF 文件。")
    reader = PdfReader(str(pdf_path))
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:16]
    document_title = title or pdf_path.stem
    url = source_url or f"file://{pdf_path.resolve()}"
    pages: list[SourceDocument] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = " ".join((page.extract_text() or "").split())
        if len(text) < 20:
            continue
        pages.append(
            SourceDocument(
                chunk_id=f"pdf:{digest}:page:{page_number}",
                source_type="guidance",
                authority_level="official",
                title=f"{document_title} · page {page_number}",
                text=f"Title: {document_title}\nPage: {page_number}\n{text}",
                source_url=url,
                metadata={
                    "publisher": "CFPB",
                    "page": page_number,
                    "modality": "pdf_text_baseline",
                    "pdf_sha256": digest,
                    "visual_region": None,
                },
            )
        )
    return pages
