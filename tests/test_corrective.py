from types import SimpleNamespace

from app.corrective import build_retry_query, grade_evidence


def test_retry_query_expands_known_domain_term_only():
    query, strategy = build_retry_query("我发现一笔陌生扣款")
    assert "unauthorized" in query
    assert strategy == "domain_term_expansion"


def test_evidence_grade_uses_underlying_score_for_rrf():
    weak = [SimpleNamespace(source_type="guidance", score=.016, metadata={"retrieval_method": "rrf", "dense_score": .2})]
    strong = [SimpleNamespace(source_type="guidance", score=.016, metadata={"retrieval_method": "rrf", "dense_score": .62}), SimpleNamespace(source_type="complaint", score=.015, metadata={"retrieval_method": "rrf", "dense_score": .55})]
    assert grade_evidence(weak)["sufficient"] is False
    assert grade_evidence(strong)["sufficient"] is True
