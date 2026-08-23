from app.config import Settings
from app.reranker import CrossEncoderReranker, RerankerUnavailable
from app.schemas import SourceHit


def test_v04_reranker_is_opt_in_and_explains_installation():
    reranker = CrossEncoderReranker(Settings(reranker_enabled=False))
    status = reranker.status()
    assert status["state"] == "disabled"
    try:
        reranker.rerank("question", [], 3)
    except RerankerUnavailable:
        raise AssertionError("empty candidate sets should be a no-op")


def test_v04_reranker_disabled_rejects_non_empty_candidates():
    reranker = CrossEncoderReranker(Settings(reranker_enabled=False))
    class Hit:
        text = "candidate"
    try:
        reranker.rerank("question", [Hit()], 1)
    except RerankerUnavailable as exc:
        assert "RERANKER_ENABLED" in str(exc)
    else:
        raise AssertionError("disabled V0.4 must fail closed")


def test_remote_llama_reranker_maps_indices_and_preserves_scores(monkeypatch):
    settings = Settings(
        reranker_enabled=True,
        reranker_provider="llama_cpp",
        reranker_base_url="http://localhost:23146",
        reranker_model="qwen3-reranker-0.6b-q8_0.gguf",
    )
    hits = [
        SourceHit(citation="S1", source_type="guidance", authority_level="official", title="A", score=.2, text="a", metadata={}, source_url="https://a"),
        SourceHit(citation="S2", source_type="guidance", authority_level="official", title="B", score=.1, text="b", metadata={}, source_url="https://b"),
    ]

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"results": [{"index": 1, "relevance_score": .9}, {"index": 0, "relevance_score": .2}]}

    monkeypatch.setattr("app.reranker.httpx.post", lambda *args, **kwargs: Response())
    ranked = CrossEncoderReranker(settings).rerank("question", hits, 2)
    assert [item.citation for item in ranked] == ["S2", "S1"]
    assert ranked[0].metadata["rerank_score"] == .9
