from app.guardrails import analyze_answer
from app.schemas import SourceHit


def source(citation: str = "S1") -> SourceHit:
    return SourceHit(
        citation=citation,
        source_type="guidance",
        authority_level="official",
        title="Guidance",
        score=1.0,
        text="Official evidence.",
        metadata={},
        source_url="https://example.test/guidance",
    )


def test_guardrail_requires_citation_support_coverage():
    result = analyze_answer("事实一 [S1]。事实二没有引用。", [source()])
    assert result["citation_coverage"] < 0.8
    assert result["needs_human_review"] is True


def test_guardrail_flags_refund_promise_and_unknown_citation():
    result = analyze_answer("银行保证今天退款 [S7]。", [source()])
    assert "refund_promise" in result["safety_flags"]
    assert result["invalid_citations"] == ["S7"]
    assert result["needs_human_review"] is True


def test_guardrail_allows_bounded_cited_answer():
    result = analyze_answer("官方流程是联系发卡机构。[S1]\n\n这不是法律、金融或账户处理决定。", [source()])
    assert result["citation_coverage"] == 1.0
    assert result["needs_human_review"] is False
from app.guardrails import analyze_answer, normalize_citations


class Source:
    def __init__(self, citation: str):
        self.citation = citation


def test_full_width_citations_are_canonicalized_and_supported():
    assert normalize_citations("事实【S1】以及［C1］") == "事实[S1]以及[C1]"
    result = analyze_answer("事实【S1】。这不是法律、金融或账户处理决定。", [Source("S1")])
    assert result["citation_coverage"] == 1.0
    assert result["needs_human_review"] is False
