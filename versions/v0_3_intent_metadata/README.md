# V0.3 Intent + Metadata filtering

This is the next problem-driven assembly. It targets the observed failure where consumer complaint submission and company complaint response are semantically confused.

```text
Question → Intent classification
         → audience/source_url_family Metadata filter
         → Qwen Embedding → Dense + BM25 → RRF → prompt → R1
```

New Trace: `route_intent → metadata_filter` before `embed_query`.

Initial router is deterministic and auditable. A learned/LLM router can be compared later behind the same `intent/confidence/matched_terms/source_url_families` contract.

Gate: complaint-process consumer/company hard cases must retrieve the correct official URL; overall quality must improve without unacceptable recall loss, latency or unexplained routing errors.

First seed result after implementation: Dense + Intent/Metadata and Hybrid + Intent/Metadata both reached Hit@3=1.0 and MRR=1.0 on the 8-case seed. This is an early regression signal, not final production proof; the data gate and 50-case human-reviewed set remain incomplete.
