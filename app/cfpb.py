"""Official CFPB Consumer Complaint Database downloader for the V0.1 data pack."""

from __future__ import annotations

from datetime import date
from hashlib import sha256
from io import BytesIO
from typing import Any

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
import csv
from hashlib import sha256
from io import StringIO
from urllib.parse import urlencode

from app.schemas import ComplaintRecord, SourceDocument

CFPB_SEARCH_API = "https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/"
CFPB_RECORD_URL = "https://www.consumerfinance.gov/data-research/consumer-complaints/search/detail/"
CFPB_SEARCH_PAGE = "https://www.consumerfinance.gov/data-research/consumer-complaints/search/"
USER_AGENT = "OpenSupport-RAG-v0.1 (educational open-source project)"

OFFICIAL_GUIDANCE_SOURCES = [
    {
        "title": "CFPB complaint process",
        "source_type": "guidance",
        "url": "https://www.consumerfinance.gov/complaint/process/",
    },
    {
        "title": "CFPB company complaint response process",
        "source_type": "guidance",
        "url": "https://www.consumerfinance.gov/compliance/consumer-complaint-program/company-process/",
    },
    {
        "title": "How to dispute a charge on a credit card bill",
        "source_type": "guidance",
        "url": "https://www.consumerfinance.gov/ask-cfpb/how-do-i-dispute-a-charge-on-my-credit-card-bill-en-61/",
    },
    {
        "title": "How to fix mistakes in a credit card bill",
        "source_type": "guidance",
        "url": "https://www.consumerfinance.gov/consumer-tools/credit-cards/how-to-fix-mistakes-in-your-credit-card-bill/",
        "fallback_pdf": "https://files.consumerfinance.gov/f/documents/cfpb_adult-fin-ed_how-to-fix-mistakes-in-your-credit-bill.pdf",
    },
    {
        "title": "What is an unauthorized use of a credit card",
        "source_type": "guidance",
        "url": "https://www.consumerfinance.gov/ask-cfpb/what-is-an-unauthorized-use-of-a-credit-card-en-26/",
    },
    {
        "title": "Regulation Z 1026.13 Billing error resolution",
        "source_type": "regulation",
        "url": "https://www.consumerfinance.gov/rules-policy/regulations/1026/13/",
        "fallback_pdf": "https://files.consumerfinance.gov/f/documents/201502_cfpb_credit-card-account-management-examination-procedures.pdf",
    },
]


def source_url(complaint_id: str) -> str:
    return f"{CFPB_RECORD_URL}{complaint_id}"


def normalize_hit(hit: dict[str, Any]) -> ComplaintRecord | None:
    source = hit.get("_source", {})
    narrative = (source.get("complaint_what_happened") or "").strip()
    complaint_id = str(source.get("complaint_id") or hit.get("_id") or "")
    if not complaint_id or not narrative:
        return None
    return ComplaintRecord(
        complaint_id=complaint_id,
        narrative=narrative,
        product=source.get("product"),
        sub_product=source.get("sub_product"),
        issue=source.get("issue"),
        sub_issue=source.get("sub_issue"),
        company=source.get("company"),
        company_response=source.get("company_response"),
        timely=source.get("timely"),
        date_received=source.get("date_received"),
        source_url=source_url(complaint_id),
        identity_source="api",
    )


def _csv_export_url(year: int) -> str:
    params = {
        "product": "Credit card",
        "date_received_min": date(year, 1, 1).isoformat(),
        "date_received_max": date(year, 12, 31).isoformat(),
        "format": "csv",
    }
    return f"{CFPB_SEARCH_API}?{urlencode(params)}"


def normalize_csv_row(row: dict[str, str], *, export_url: str) -> ComplaintRecord | None:
    """Normalize the official filtered CSV export when JSON is WAF-blocked.

    The current CFPB CSV export omits complaint_id.  We therefore derive a
    stable row identity from the published fields and label it explicitly in
    metadata instead of presenting it as an official complaint ID.
    """

    narrative = (row.get("Consumer complaint narrative") or "").strip()
    if not narrative:
        return None
    identity_material = "|".join(
        (row.get(field) or "").strip()
        for field in [
            "Date received",
            "Product",
            "Sub-product",
            "Issue",
            "Sub-issue",
            "Company",
            "Consumer complaint narrative",
        ]
    )
    derived_id = f"csv-{sha256(identity_material.encode('utf-8')).hexdigest()[:20]}"
    return ComplaintRecord(
        complaint_id=derived_id,
        narrative=narrative,
        product=row.get("Product") or None,
        sub_product=row.get("Sub-product") or None,
        issue=row.get("Issue") or None,
        sub_issue=row.get("Sub-issue") or None,
        company=row.get("Company") or None,
        company_response=row.get("Company public response") or None,
        date_received=row.get("Date received") or None,
        source_url=export_url,
        identity_source="csv_row_sha256",
        export_url=export_url,
    )


async def fetch_credit_card_complaints_csv(limit: int, year: int) -> list[ComplaintRecord]:
    """Fetch a filtered official CSV export as a transparent API fallback."""

    export_url = _csv_export_url(year)
    headers = {"User-Agent": USER_AGENT, "Accept": "text/csv"}
    async with httpx.AsyncClient(timeout=120, headers=headers, follow_redirects=True) as client:
        response = await client.get(export_url)
        response.raise_for_status()
    if "text/csv" not in response.headers.get("content-type", "").lower():
        raise RuntimeError(f"CFPB CSV fallback returned unexpected content type: {response.headers.get('content-type')}")
    rows = csv.DictReader(StringIO(response.content.decode("utf-8-sig", errors="replace")))
    records: list[ComplaintRecord] = []
    seen: set[str] = set()
    for row in rows:
        record = normalize_csv_row(row, export_url=export_url)
        if record is None or record.complaint_id in seen:
            continue
        seen.add(record.complaint_id)
        records.append(record)
        if len(records) >= limit:
            break
    return records


def load_credit_card_complaints_csv(path: str | bytes, limit: int, year: int) -> list[ComplaintRecord]:
    """Load an official CSV export saved locally after a WAF/rate-limit event."""

    if isinstance(path, bytes):
        content = path
        file_label = "local-export.csv"
    else:
        from pathlib import Path

        file_path = Path(path)
        content = file_path.read_bytes()
        file_label = file_path.name
    export_url = f"{CFPB_SEARCH_PAGE}?source=cfpb-official-csv&file={file_label}"
    rows = csv.DictReader(StringIO(content.decode("utf-8-sig", errors="replace")))
    records: list[ComplaintRecord] = []
    seen: set[str] = set()
    start = date(year, 1, 1).isoformat()
    end = date(year, 12, 31).isoformat()
    for row in rows:
        received = (row.get("Date received") or "").strip()
        if received and not (start <= received <= end):
            continue
        if (row.get("Product") or "").strip().lower() != "credit card":
            continue
        record = normalize_csv_row(row, export_url=export_url)
        if record is None or record.complaint_id in seen:
            continue
        seen.add(record.complaint_id)
        records.append(record)
        if len(records) >= limit:
            break
    return records


CFPB_MIRROR_URL = "https://huggingface.co/datasets/claritystorm/cfpb-consumer-complaints/resolve/main/sample_1000.csv"


def normalize_mirror_row(row: dict[str, str], *, mirror_url: str = CFPB_MIRROR_URL) -> ComplaintRecord | None:
    """Normalize a public CFPB-derived mirror row while preserving its real ID."""

    normalized = normalize_csv_row(
        {
            "Date received": row.get("date_received", ""),
            "Product": row.get("product", ""),
            "Sub-product": row.get("sub_product", ""),
            "Issue": row.get("issue", ""),
            "Sub-issue": row.get("sub_issue", ""),
            "Consumer complaint narrative": row.get("consumer_narrative", ""),
            "Company public response": row.get("company_public_response", ""),
            "Company": row.get("company", ""),
        },
        export_url=mirror_url,
    )
    if normalized is None:
        return None
    complaint_id = (row.get("complaint_id") or "").strip()
    if not complaint_id:
        return normalized
    return normalized.model_copy(
        update={
            "complaint_id": complaint_id,
            "source_url": source_url(complaint_id),
            "identity_source": "cfpb_mirror_huggingface",
            "export_url": mirror_url,
        }
    )


def load_cfpb_mirror_csv(path: str | bytes, limit: int, year: int | None = None, product_filter: str = "any") -> list[ComplaintRecord]:
    """Load a versioned CFPB-derived mirror with explicit provenance."""

    if isinstance(path, bytes):
        content = path
        file_label = "cfpb-mirror.csv"
    else:
        from pathlib import Path

        file_path = Path(path)
        content = file_path.read_bytes()
        file_label = file_path.name
    mirror_url = f"{CFPB_MIRROR_URL}?local_file={file_label}"
    rows = csv.DictReader(StringIO(content.decode("utf-8-sig", errors="replace")))
    records: list[ComplaintRecord] = []
    seen: set[str] = set()
    normalized_product = product_filter.strip().lower()
    for row in rows:
        received = (row.get("date_received") or "").strip()
        if year is not None and received and not (date(year, 1, 1).isoformat() <= received <= date(year, 12, 31).isoformat()):
            continue
        product = (row.get("product") or "").strip()
        if normalized_product not in {"any", "all"} and product.lower() != normalized_product:
            continue
        record = normalize_mirror_row(row, mirror_url=mirror_url)
        if record is None or record.complaint_id in seen:
            continue
        seen.add(record.complaint_id)
        records.append(record)
        if len(records) >= limit:
            break
    return records


async def fetch_credit_card_complaints(limit: int, year: int) -> list[ComplaintRecord]:
    """Fetch public narratives. The API returns only real CFPB records."""

    start = date(year, 1, 1).isoformat()
    end = date(year, 12, 31).isoformat()
    records: list[ComplaintRecord] = []
    seen_ids: set[str] = set()
    offset = 0
    page_size = min(100, limit)

    try:
        async with httpx.AsyncClient(timeout=45, headers={"User-Agent": USER_AGENT}) as client:
            while len(records) < limit:
                response = await client.get(
                    CFPB_SEARCH_API,
                    params={
                        "product": "Credit card",
                        "date_received_min": start,
                        "date_received_max": end,
                        "size": page_size,
                        # The CFPB CCDB API calls its zero-based offset `frm`.
                        # `from` is silently ignored and would repeat page zero.
                        "frm": offset,
                    },
                )
                response.raise_for_status()
                hits = response.json().get("hits", {}).get("hits", [])
                if not hits:
                    break

                for hit in hits:
                    record = normalize_hit(hit)
                    if record is not None and record.complaint_id not in seen_ids:
                        seen_ids.add(record.complaint_id)
                        records.append(record)
                        if len(records) >= limit:
                            break
                offset += len(hits)
                if len(hits) < page_size:
                    break
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != 403:
            raise
        # The public site can WAF-block JSON while allowing its official CSV
        # export.  Keep the fallback explicit and provenance-labelled.
        try:
            return await fetch_credit_card_complaints_csv(limit, year)
        except httpx.HTTPStatusError as csv_error:
            raise RuntimeError(
                "CFPB JSON API 和官方 CSV fallback 都返回了 403。"
                "请稍后重试，或从 CFPB Consumer Complaint Database 的官方 CSV 下载页下载后走离线摄取。"
            ) from csv_error
    return records


def _document_date(soup: BeautifulSoup) -> str | None:
    for selector in ["meta[property='article:modified_time']", "meta[property='article:published_time']", "time[datetime]"]:
        node = soup.select_one(selector)
        if node:
            return node.get("content") or node.get("datetime")
    return None


def chunk_guidance_html(html: str, source: dict[str, str], max_chars: int = 1100) -> list[SourceDocument]:
    """Keep headings with their paragraphs so legal guidance remains inspectable."""

    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select("script, style, noscript, nav, footer, header, aside"):
        node.decompose()
    root = soup.select_one("main") or soup.body or soup
    published_at = _document_date(soup)
    chunks: list[SourceDocument] = []
    heading = source["title"]
    buffer: list[str] = []

    def flush() -> None:
        if not buffer:
            return
        text = "\n".join(buffer).strip()
        if len(text) < 80:
            return
        index = len(chunks) + 1
        digest = sha256(f"{source['url']}:{heading}:{index}".encode()).hexdigest()[:12]
        chunks.append(
            SourceDocument(
                chunk_id=f"guidance:{digest}",
                source_type=source["source_type"],  # type: ignore[arg-type]
                authority_level="official",
                title=heading,
                text=text,
                source_url=source["url"],
                published_at=published_at,
                metadata={"publisher": "CFPB", "parent_title": source["title"]},
            )
        )

    def split_long_text(value: str) -> list[str]:
        if len(value) <= max_chars:
            return [value]
        sentences = value.replace(". ", ".\n").replace("; ", ";\n").splitlines()
        parts: list[str] = []
        current = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence) > max_chars:
                if current:
                    parts.append(current)
                    current = ""
                parts.extend(sentence[index : index + max_chars] for index in range(0, len(sentence), max_chars))
                continue
            candidate = f"{current} {sentence}".strip()
            if len(candidate) > max_chars and current:
                parts.append(current)
                current = sentence
            else:
                current = candidate
        if current:
            parts.append(current)
        return parts

    for element in root.find_all(["h1", "h2", "h3", "p", "li"]):
        value = element.get_text(" ", strip=True)
        if not value:
            continue
        if element.name in {"h1", "h2", "h3"}:
            flush()
            buffer = [value]
            heading = value
            continue
        for fragment in split_long_text(value):
            candidate = "\n".join(buffer + [fragment])
            if len(candidate) > max_chars and buffer:
                flush()
                buffer = [heading, fragment]
            else:
                buffer.append(fragment)
    flush()
    return chunks


def chunk_guidance_pdf(content: bytes, source: dict[str, str], max_chars: int = 1100) -> list[SourceDocument]:
    """Extract readable page text from official PDFs while preserving source page metadata."""

    reader = PdfReader(BytesIO(content))
    documents: list[SourceDocument] = []
    for page_number, page in enumerate(reader.pages, start=1):
        page_text = " ".join((page.extract_text() or "").split())
        if len(page_text) < 80:
            continue
        for part_index, start in enumerate(range(0, len(page_text), max_chars), start=1):
            text = page_text[start : start + max_chars]
            digest = sha256(f"{source['url']}:{page_number}:{part_index}".encode()).hexdigest()[:12]
            documents.append(
                SourceDocument(
                    chunk_id=f"guidance:{digest}",
                    source_type=source["source_type"],  # type: ignore[arg-type]
                    authority_level="official",
                    title=source["title"],
                    text=text,
                    source_url=source["url"],
                    metadata={"publisher": "CFPB", "page": page_number, "fallback_format": "pdf"},
                )
            )
    return documents


async def _get_with_retry(client: httpx.AsyncClient, url: str, attempts: int = 3) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
    raise RuntimeError(f"无法获取 {url}: {last_error}")


async def fetch_official_guidance() -> tuple[list[SourceDocument], list[str]]:
    documents: list[SourceDocument] = []
    failures: list[str] = []
    async with httpx.AsyncClient(timeout=45, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for source in OFFICIAL_GUIDANCE_SOURCES:
            try:
                response = await _get_with_retry(client, source["url"])
                response.encoding = "utf-8"
                documents.extend(chunk_guidance_html(response.text, source))
            except RuntimeError as primary_error:
                fallback_url = source.get("fallback_pdf")
                if not fallback_url:
                    failures.append(str(primary_error))
                    continue
                try:
                    response = await _get_with_retry(client, fallback_url)
                    documents.extend(chunk_guidance_pdf(response.content, {**source, "url": fallback_url}))
                except RuntimeError as fallback_error:
                    failures.append(f"{primary_error}; fallback failed: {fallback_error}")
    return documents, failures
