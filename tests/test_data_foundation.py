from app.data_foundation import (
    canonical_url,
    detect_language,
    finalize_quality_report,
    normalize_text,
    prepare_documents,
)
from app.schemas import SourceDocument


def make_document(chunk_id: str, text: str, *, source_type: str = "guidance", url: str = "https://example.test/a/") -> SourceDocument:
    return SourceDocument(
        chunk_id=chunk_id,
        source_type=source_type,  # type: ignore[arg-type]
        authority_level="official" if source_type != "complaint" else "consumer_allegation",
        title="  Billing   guidance ",
        text=text,
        source_url=url,
        complaint_id=chunk_id if source_type == "complaint" else None,
        metadata={"issue": "billing"},
    )


def test_normalize_text_and_url_are_deterministic():
    assert normalize_text("A\u00a0  B\n\nC") == "A B C"
    assert canonical_url("HTTPS://EXAMPLE.TEST/a/#section") == "https://example.test/a"


def test_language_bucket_supports_cross_language_slice():
    assert detect_language("信用卡账单有错误") == "zh"
    assert detect_language("What is a billing error?") == "en"


def test_prepare_documents_quarantines_short_and_deduplicates_guidance():
    good = make_document("g1", "Official guidance sentence. " * 4)
    duplicate = make_document("g2", " Official guidance sentence. " * 4)
    short = make_document("bad", "too short")

    accepted, report = prepare_documents([good, duplicate, short])

    assert [item.chunk_id for item in accepted] == ["g1"]
    assert report.duplicate_documents == 1
    assert report.quarantined_documents == 1
    assert report.snapshot_id
    assert report.stage_counts["deduplicated"] == 1


def test_complaints_with_distinct_source_identity_are_retained():
    first = make_document("c1", "The same public narrative text. " * 4, source_type="complaint", url="https://example.test/c1")
    second = make_document("c2", "The same public narrative text. " * 4, source_type="complaint", url="https://example.test/c2")

    accepted, report = prepare_documents([first, second])

    assert len(accepted) == 2
    assert report.duplicate_documents == 0


def test_finalize_quality_report_records_derived_index_count():
    accepted, report = prepare_documents([make_document("g1", "Official guidance sentence. " * 4)])
    final = finalize_quality_report(report, len(accepted), manifest_consistent=True)
    assert final.indexed_documents == 1
    assert final.stage_counts["active"] == 1
    assert final.manifest_consistent is True
