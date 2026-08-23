# OpenSupport RAG versioned assemblies

Each folder is a reproducible design checkpoint, not a second copy of the whole repository. The active implementation stays under `app/`; each version folder records the assembly, trace contract, acceptance gates, and the exact upgrade delta.

| Version | Assembly | Status |
|---|---|---|
| `v0_0_data_foundation` | Normalize → Validate → Deduplicate → Lineage → Derived index | Implemented first slice; Postgres/MinIO adapter next |
| `v0_1_dense` | Qwen Embedding → Qdrant Dense → evidence-aware R1 | Running baseline, data gate incomplete |
| `v0_2_hybrid` | Dense + BM25 → RRF → evidence-aware R1 | Implemented, quality gain not yet proven |
| `v0_3_intent_metadata` | Intent → Metadata filter → Dense/BM25 → RRF | First problem-driven upgrade in construction |
| `v0_4_reranker` | Hybrid candidates → local Qwen3 Reranker/llama.cpp | Experimental; same-set MRR/latency did not justify default |
| `v0_5_contextual_hierarchical` | Deterministic contextual prefix + parent-child and long-document retrieval | Implemented; 432 isolated points, same-set eval positive signal |
| `v0_6_adaptive_corrective` | Evidence grading, domain query variant and one bounded retry | Implemented; no unnecessary retry on current Golden Draft |
| `v0_7_graph_augmented` | Neo4j structured complaint graph + text evidence | Optional profile planned |
| `v0_8_multimodal` | PDF layout/table/page retrieval | Planned |
| `v0_9_production_rag` | Versioning, PII, timeout, monitoring, rollback | Locked until quality gates pass |
| `v1_0_controlled_agent` | Human-approved information completion/ticket draft | Code scaffolded and API/UI locked until production RAG passes |

To compare versions, run the same customer-support Benchmark against the same frozen data snapshot. Do not compare a new component on a different corpus and call the difference an improvement.
