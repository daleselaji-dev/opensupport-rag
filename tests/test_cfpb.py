from app.cfpb import chunk_guidance_html, load_cfpb_mirror_csv, load_credit_card_complaints_csv, normalize_csv_row, normalize_hit


def test_normalize_requires_real_narrative():
    assert normalize_hit({"_id": "1", "_source": {"complaint_id": "1", "complaint_what_happened": ""}}) is None


def test_normalize_preserves_source_identity():
    record = normalize_hit(
        {
            "_id": "42",
            "_source": {
                "complaint_id": "42",
                "complaint_what_happened": "A public narrative retained for parser testing.",
                "product": "Credit card",
                "issue": "Billing disputes",
            },
        }
    )
    assert record is not None
    assert record.complaint_id == "42"
    assert record.source_url.endswith("42")


def test_complaint_becomes_consumer_allegation_document():
    record = normalize_hit(
        {
            "_id": "42",
            "_source": {"complaint_id": "42", "complaint_what_happened": "A public narrative.", "product": "Credit card"},
        }
    )
    document = record.to_document()
    assert document.source_type == "complaint"
    assert document.authority_level == "consumer_allegation"


def test_csv_fallback_marks_derived_identity_transparently():
    record = normalize_csv_row(
        {
            "Date received": "2024-01-02",
            "Product": "Credit card",
            "Sub-product": "",
            "Issue": "Billing errors",
            "Sub-issue": "",
            "Consumer complaint narrative": "A public CSV narrative retained for fallback testing.",
            "Company public response": "Closed with explanation",
            "Company": "Example Bank",
        },
        export_url="https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/?format=csv",
    )
    assert record is not None
    assert record.complaint_id.startswith("csv-")
    assert record.identity_source == "csv_row_sha256"
    document = record.to_document()
    assert document.metadata["identity_source"] == "csv_row_sha256"


def test_local_csv_loader_filters_product_and_year(tmp_path):
    csv_path = tmp_path / "complaints.csv"
    csv_path.write_text(
        "Date received,Product,Sub-product,Issue,Sub-issue,Consumer complaint narrative,Company public response,Company\n"
        "2024-01-02,Credit card,,Billing errors,,A valid published narrative for the local loader.,Closed with explanation,Example Bank\n"
        "2023-01-02,Credit card,,Billing errors,,Wrong year narrative,Closed with explanation,Example Bank\n"
        "2024-01-03,Mortgage,,Billing errors,,Wrong product narrative,Closed with explanation,Example Bank\n",
        encoding="utf-8",
    )
    records = load_credit_card_complaints_csv(str(csv_path), limit=10, year=2024)
    assert len(records) == 1
    assert records[0].identity_source == "csv_row_sha256"


def test_cfpb_mirror_loader_preserves_real_complaint_id(tmp_path):
    csv_path = tmp_path / "mirror.csv"
    csv_path.write_text(
        "date_received,product,sub_product,issue,sub_issue,consumer_narrative,company_public_response,company,complaint_id\n"
        "2024-01-02,Credit reporting,Credit reporting,Incorrect information,,A public credit reporting narrative.,Closed,Example Bank,12345\n"
        "2024-01-03,Credit card,,Billing errors,,A public narrative with a real source ID.,Closed,Example Bank,67890\n",
        encoding="utf-8",
    )
    records = load_cfpb_mirror_csv(str(csv_path), limit=10, product_filter="any")
    assert len(records) == 2
    assert records[0].complaint_id == "12345"
    assert records[0].identity_source == "cfpb_mirror_huggingface"
    assert records[0].source_url.endswith("12345")


def test_guidance_chunker_preserves_heading_and_authority():
    html = "<main><h1>Billing disputes</h1><p>" + ("Official guidance sentence. " * 8) + "</p></main>"
    chunks = chunk_guidance_html(
        html,
        {"title": "Billing disputes", "source_type": "guidance", "url": "https://example.test/guidance"},
    )
    assert len(chunks) == 1
    assert chunks[0].authority_level == "official"
    assert "Billing disputes" in chunks[0].text


def test_guidance_chunker_splits_long_paragraphs():
    html = "<main><h1>Long page</h1><p>" + ("A sentence. " * 500) + "</p></main>"
    chunks = chunk_guidance_html(
        html,
        {"title": "Long page", "source_type": "guidance", "url": "https://example.test/long"},
        max_chars=300,
    )
    assert len(chunks) > 1
    assert all(len(chunk.text) <= 310 for chunk in chunks)
