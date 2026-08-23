# V0.2 Dense + Qdrant Sparse/BM25 + RRF

```text
Question → Qwen Embedding → Dense candidates ──────────┐
          Qdrant `qdrant/bm25` Sparse candidates ──────┤→ RRF → prompt → R1
```

Trace adds: `sparse_backend → retrieve_dense_* → bm25_* → fusion_rrf`.

The previous in-process BM25 implementation remains available only as a
fallback and historical comparison. V0.2's production-shaped path uses a
named Dense/Sparse collection (`opensupport_qwen_v02_sparse`) and Qdrant native
multilingual BM25 inference.

Gate: compare Dense/BM25/Hybrid on the same frozen Benchmark with Hit@3, MRR, nDCG, citation metrics, p95 and cost. Hybrid is not accepted merely because it has more components.
