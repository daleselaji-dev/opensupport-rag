import json

from app.golden_review import case_ids, record_signoff, review_status


def test_golden_review_requires_two_complete_distinct_reviewers(tmp_path, monkeypatch):
    import app.golden_review as module

    monkeypatch.setattr(module, "SIGNOFFS", tmp_path / "signoffs.json")
    ids = case_ids()
    assert review_status()["approved"] is False
    record_signoff("reviewer_a", "Alice", ids)
    assert review_status()["approved"] is False
    final = record_signoff("reviewer_b", "Bob", ids)
    assert final["approved"] is True
