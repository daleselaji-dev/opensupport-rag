"""Extract a bounded narrative snapshot from CFPB's official bulk ZIP.

The full ZIP is intentionally kept outside the Git repository. This produces a
small, reproducible CSV with the same schema used by the ingest pipeline while
preserving complaint IDs and the official bulk export URL as provenance.
"""

from __future__ import annotations

import argparse
import csv
import io
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OFFICIAL_BULK_URL = "https://files.consumerfinance.gov/ccdb/complaints.csv.zip"
OUTPUT_FIELDS = [
    "date_received", "product", "sub_product", "issue", "sub_issue", "consumer_narrative",
    "company_public_response", "company", "state", "zip_code", "tags", "consumer_consent",
    "submitted_via", "date_sent_to_company", "company_response", "timely_response",
    "consumer_disputed", "complaint_id", "year", "month", "has_narrative", "product_normalised",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", default="data/raw/cfpb_complaints_full.csv.zip")
    parser.add_argument("--output", default="data/raw/cfpb_official_narratives_10000.csv")
    parser.add_argument("--limit", type=int, default=12000)
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 15000:
        raise SystemExit("--limit 必须在 1 到 15000 之间")
    zip_path = (ROOT / args.zip).resolve()
    output_path = (ROOT / args.output).resolve()
    if not zip_path.exists():
        raise SystemExit(f"找不到官方 ZIP：{zip_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    written = 0
    with zipfile.ZipFile(zip_path) as archive:
        member = "complaints.csv" if "complaints.csv" in archive.namelist() else archive.namelist()[0]
        with archive.open(member) as raw, output_path.open("w", encoding="utf-8-sig", newline="") as target:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline=""))
            writer = csv.DictWriter(target, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
            writer.writeheader()
            for row in reader:
                narrative = (row.get("Consumer complaint narrative") or "").strip()
                complaint_id = (row.get("Complaint ID") or "").strip()
                if not narrative or not complaint_id or complaint_id in seen:
                    continue
                seen.add(complaint_id)
                received = (row.get("Date received") or "").strip()
                try:
                    parsed = datetime.strptime(received, "%m/%d/%Y")
                    date_received = parsed.date().isoformat()
                    year, month = parsed.year, parsed.month
                except ValueError:
                    date_received = received
                    year, month = "", ""
                writer.writerow({
                    "date_received": date_received,
                    "product": row.get("Product", ""),
                    "sub_product": row.get("Sub-product", ""),
                    "issue": row.get("Issue", ""),
                    "sub_issue": row.get("Sub-issue", ""),
                    "consumer_narrative": narrative,
                    "company_public_response": row.get("Company public response", ""),
                    "company": row.get("Company", ""),
                    "state": row.get("State", ""),
                    "zip_code": row.get("ZIP code", ""),
                    "tags": row.get("Tags", ""),
                    "consumer_consent": "",
                    "submitted_via": row.get("Submitted via", ""),
                    "date_sent_to_company": row.get("Date sent to company", ""),
                    "company_response": row.get("Company response to consumer", ""),
                    "timely_response": row.get("Timely response?", ""),
                    "consumer_disputed": row.get("Consumer disputed?", ""),
                    "complaint_id": complaint_id,
                    "year": year,
                    "month": month,
                    "has_narrative": 1,
                    "product_normalised": row.get("Product", ""),
                })
                written += 1
                if written >= args.limit:
                    break
    print({"status": "ready", "output": str(output_path), "rows": written, "source_url": OFFICIAL_BULK_URL})


if __name__ == "__main__":
    main()
