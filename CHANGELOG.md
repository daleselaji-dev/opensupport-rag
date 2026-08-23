# Changelog

## Unreleased / V0.7–V0.9 lab

- Added local Qwen3 Reranker 0.6B GGUF + llama.cpp `/reranking` adapter.
- Added V0.5 contextual parent-child isolated index and V0.6 bounded corrective retrieval.
- Added optional Neo4j structured graph profile and V0.8 PDF page baseline.
- Added Redis embedding cache, model timeouts/concurrency, rate limiting, PII/injection scans, Celery contextual rebuild, stability smoke and blue/green alias rollback.
- Redesigned workbench as Swiss minimal / ASCII / glass interaction surface with version-specific diagrams and live Trace.
- V1 controlled Agent remains explicitly locked behind production gates.

## 2026-08-24 evidence

- V0.4 8-case seed: Hit@3 1.0, MRR 0.9375, p95 35,168.92ms; not promoted.
- V0.5 40-case draft: Hit@3 0.975, MRR 0.8958, p95 108.28ms.
- V0.6 40-case draft: Hit@3 0.975, MRR 0.8958, p95 110.09ms.
- V0.5 answer/safety seed: citation validity/coverage/refusal correctness 1.0, forbidden claims 0.
- V1 agent preflight seed: routing accuracy 1.0, dangerous action count 0; public Agent API still locked.
