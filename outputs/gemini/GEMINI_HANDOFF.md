# GEMINI HANDOFF — OpenSupport RAG

## Role

You are an independent reviewer. Do not rewrite the entire repository. First reproduce, inspect and report findings using the requested format below.

## Goal

OpenSupport RAG is a local-first, bilingual customer-support RAG MVP growing into a production RAG workbench. It answers Chinese or English questions with two separate source classes:

- `[S#]`: official CFPB guidance or regulations;
- `[C#]`: public CFPB consumer complaints, which are unverified consumer allegations.

The system is decision support only. It must not claim a company violated the law, must refund money, or completed an account investigation.

## Current architecture

```text
raw CFPB source → normalize/validate/hash/deduplicate → Data Quality snapshot
→ PostgreSQL/MinIO source-of-truth + Redis/Celery production profile
→ Chinese/English question
→ Qwen3-Embedding-0.6B embedding through LM Studio OpenAI-compatible API
→ Qdrant Dense or native named Dense + Sparse/BM25 + RRF for V0.2
→ evidence-aware prompt to DeepSeek-R1-Distill-Qwen-7B
→ Chinese answer with [S#]/[C#] citations and source cards
```

## Runtime configuration

- Windows host: LM Studio at `http://localhost:23145/v1`.
- Qdrant: Docker `v1.17.0` at `http://localhost:16333`.
- API: FastAPI at `http://localhost:18000`.
- Docker core API: `http://localhost:8000`.
- Chat model: `deepseek-r1-distill-qwen-7b` is the active local R1 model; `google/gemma-4-e4b` remains available for comparison.
- Embedding model: local `text-embedding-qwen3-embedding-0.6b`, downloaded from `https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF`.
- Embedding provider is configurable: local LM Studio Qwen3-Embedding or Alibaba Cloud Model Studio OpenAI-compatible `qwen3.7-text-embedding` (stable fallback: `text-embedding-v4`); chat remains local LM Studio. The Qwen API path batches inputs in groups of 10.
- GPU: RTX 3060 8GB.
- Production profile defaults: PostgreSQL `15432`, MinIO `19000` (console `19001`), Redis `16379`; Qdrant remains `16333`.

## Current implementation state

Completed:

- V0.0 Data Foundation: text/URL normalization, language bucket, content and normalized-text SHA256, validation, official-page deduplication, complaint identity preservation, quarantine counts, snapshot IDs and `data/data_quality_latest.json`.
- Workbench Data Foundation card: lifecycle counts from discovered through active, accepted/duplicate/quarantined totals and snapshot status.
- `infra/postgres/001_data_foundation.sql`: source documents, document versions, parsed blocks, chunks, ingestion jobs, index versions, Eval runs, trace spans and Agent drafts schema.
- Optional `core` Docker profile: PostgreSQL, MinIO, Redis, Celery worker; Qdrant-only startup remains backward compatible. `requirements-production.txt` lists optional production dependencies.
- PostgreSQL/MinIO persistence is now live in the core profile: normalized snapshot object, ingestion job, document versions, chunks, index version and Qdrant memberships are persisted. Windows host uses synchronous psycopg in a worker thread to avoid the Proactor event-loop limitation.
- Qdrant upgraded to `v1.17.0`; native `qdrant/bm25` named Sparse vectors are enabled in `opensupport_qwen_v02_sparse`.
- Existing 132-point Dense collection was migrated to Sparse and one duplicate guidance point was removed from both derived collections using an explicit audit script.
- `/api/index/migrate-sparse` and `scripts/migrate_sparse_index.py` expose the migration; `scripts/backfill_source_of_truth.py` and `scripts/dedupe_qdrant_index.py` record the migration evidence.

- FastAPI UI and API;
- CFPB credit-card complaint API downloader;
- official guidance/regulation downloader with HTML parsing and official PDF fallback;
- source metadata, authority labels, deterministic chunk IDs and idempotent Qdrant point IDs;
- separate retrieval of guidance/regulation and complaint evidence;
- selectable Dense baseline or Hybrid (Dense + BM25 + RRF), with component ranks and scores in trace metadata;
- prompt guardrails and citation ID validation;
- component assembly workbench and structured per-query trace for query, embedding, two retrieval branches, context, generation and citation validation;
- unit tests for parser, chunking, embedding normalization, API health, citation validation and RRF rank preservation.

Verified locally:

- `pytest`: 29 passed;
- live official CFPB guidance fetch: 6 sources, 109 chunks;
- LM Studio 1234/1235 returned Windows `EACCES`; the server now runs on high port 23145.
- Qwen3-Embedding-0.6B is complete; online Qwen fallback needs a DashScope API key.
- Docker/Qdrant runs on port 16333.
- The local embedding → Qdrant → DeepSeek-R1 generation chain is the active Chat path; Gemma remains available in LM Studio for comparison.
- Trace retrieval check recorded `retrieve_guidance → [S1]` and `retrieve_complaints → [C1]`.
- Workbench UI opened successfully and exposes the V0.1–V0.4 component controls, including the Cross-Encoder experiment and version-specific architecture diagram.
- Workbench now separates runtime status from project evolution status: V0.0 has the local 200-complaint data gate; V0.1/V0.2/V0.3 remain selectable; V0.4 Cross-Encoder is selectable as an explicit experiment but remains outside the default chain; production RAG and Agent remain locked by evidence gates.
- `POST /api/retrieve-preview` and the `只运行检索 Trace` control allow Embedding/Dense/BM25/RRF tracing without waiting for Chat LLM generation; clicking a component opens its input/output/dependency inspector.
- `POST /api/retrieve-stream` now emits a `running` event before each Embedding, Dense, BM25, RRF and (when enabled) Cross-Encoder stage and a completed event with real duration/results; the right-side version diagrams synchronize to those events.
- Full query now renders retrieval steps first and marks Chat generation as pending; local Chat prompt context is bounded to avoid LM Studio context overflow while keeping all retrieved source cards visible. `CHAT_MAX_TOKENS=1200` and `MAX_CONTEXT_CHARS=1000` are configurable defaults.
- Enterprise Eval is explicitly layered as P0 data/lineage, P1 retrieval, P2 answer/citation, P3 safety, and P4 operations/business outcomes. P0 data/Manifest passes locally; P1 Golden Draft remains pending two-person review; the full 50-case P2/P3 automatic run passes deterministic citation/refusal/safety gates but is not a substitute for human Citation Support.
- V0.2/V0.3 seed Eval (8 real CFPB URL-linked Chinese/English questions, same 131-point snapshot): Dense Hit@3=1.0, MRR=1.0, p95=41.70ms; native Hybrid Hit@3=1.0, MRR=1.0, p95=64.87ms. Native Hybrid has no measured quality gain yet.
- DeepSeek-R1 full-query smoke test: returned a bounded answer in about 11.5 seconds with `citation_valid=true`; a guarded `repair_citations` trace step is available when R1 omits citations, but it is never allowed to introduce new source IDs.
- Current index facts: 12,335 Qdrant points in both primary and Sparse collections, 12,335 unique chunks, 12,223 complaint chunks in the cumulative index; the official bulk snapshot added 12,000 complaint narratives in 47 checkpointed batches, plus the existing 112 official guidance/regulation source chunks. Manifest and Qdrant match.
- Two hard cases (`complaint-process-zh`, `complaint-process-en`) retrieve the company-process page instead of the consumer-process page; this is an open retrieval failure, not a hidden success.
- V0.3 Intent + Metadata first run: both Dense and Hybrid reached Hit@3=1.0 and MRR=1.0 on the 8-case seed; the two complaint-process hard cases now map to their correct official URL families. This remains seed-only evidence.
- Current lifecycle stage is V0.9 implemented-but-not-released: V0.5/V0.6 same-set evidence is recorded on the 12,335-point snapshot, V0.7 Graph has 12,223 Complaint nodes and 41,802 structured relationships, V0.8 has a page-level PDF baseline but the CFPB CDN returned 403, V0.9 operations smoke is green, and the 50-case human review is still pending. Trace includes `route_intent`, `metadata_filter`, `sparse_backend`, `guardrail_review`, `rerank_candidates`, `contextual_backend`, `expand_parent`, `evidence_grade`, `query_translation`, `corrective_retry`, and request-level safety gates; the workbench stage cards distinguish implemented, experimental, blocked and preflight states.
- `/api/health` reports Data Foundation ready, native Sparse ready, 12,335 primary/Sparse points, 19,087 contextual points, PostgreSQL/MinIO/Redis ready, and LM Studio/Reranker/Neo4j ready on the Windows host.
- Real V0.0 smoke ingest (`limit=20`, `year=2024`) exposed a genuine source failure: CFPB JSON API returned HTTP 403, and the official filtered CSV fallback was also HTTP 403 during the same run. The API now records `data/ingest_failure_latest.json` and returns an actionable 503 without a Python stack trace. This is an external source/WAF blocker, not a retrieval result.
- Added `POST /api/ingest-local`: an official CFPB CSV saved under `data/raw` can be filtered by year/product and sent through the same V0.0 quality/index/manifest contract; CSV-derived identities remain labeled `csv_row_sha256`.
- Current verified source-of-truth snapshot: official bulk worker accepted 12,004 documents (12,000 complaints + 4 guidance), skipped 12,004 already-indexed IDs on its idempotency replay, and has 0 within-snapshot duplicates, 0 quarantined; PostgreSQL/MinIO contain the normalized snapshot and lineage.
- Current runtime health on Windows host and Docker core profile: Qdrant ready, native Sparse ready, 12,335 primary/Sparse points, PostgreSQL/MinIO/Redis ready; Docker `/api/retrieve-preview` remains the deployment smoke path through host LM Studio.
- The prior CFPB-derived mirror ingest remains recorded as historical development evidence; the release snapshot is now the official bulk export and is not conflated with a live API fetch. Current official bulk ingestion recorded 12,000 new complaint documents, 4 idempotently skipped guidance IDs, and 12,335 indexed points.
- On the official 12,335-point snapshot, V0.3 Hybrid on 40 answerable cases reached Hit@3=0.975, MRR=0.8792, p95=142.82ms; V0.5 Contextual reached Hit@3=0.975, MRR=0.8958, p95=174.15ms; V0.6 reached Hit@3=0.975, MRR=0.8958, p95=164.8ms. Golden Review remains pending.
- V0.3 Golden Draft retrieval run: 50 total cases, 40 answerable retrieval cases and 10 refusal/safety cases. `reports/benchmark_review_v0_3.json` confirms no duplicate IDs or missing URL/type fields; two-person human review is still required before approval.
- V0.4 local Reranker smoke/Eval: Qwen3 Reranker 0.6B Q8_0 GGUF is served by llama.cpp at `localhost:23146/reranking`; the same 8-case seed ablation reached k=10 MRR=0.9375/p95=5346ms and k=20 MRR=1.0/p95=9908ms. It is runnable but not promoted because Hybrid baseline is about 81ms and no stable support gain is proven.
- V0.5 contextual/parent-child index: `POST /api/index/build-contextual` created 19,087 isolated contextual points from 12,335 source points, including 11,100 child chunks. It reached Hit@3=0.975, MRR=0.8958, p95=174.15ms on the 40-case slice; this is promising but still pending human Citation Support evaluation.
- P2/P3 answer Eval is now available at `/api/eval/answer-run` and the workbench. The latest full 50-case V0.6 run reports citation validity 1.0, citation coverage 1.0, refusal correctness 1.0, forbidden claims 0, answer errors/timeouts 0 and p95 26,758.29ms; this is an automatic gate, not a substitute for human blind review.
- Full 50-case Answer/Safety Eval on V0.6 now reports citation validity 1.0, citation coverage 1.0, refusal correctness 1.0, forbidden claims 0, answer errors/timeouts 0, and p95 26,758.29ms. `release_check.py` still blocks publishing only on the two-person Golden Review.
- `/metrics` exposes request/error/latency Prometheus metrics; the observability profile is running with Prometheus, Grafana and OTLP Collector. Both Docker API and Windows API are Prometheus targets; OTLP Collector debug exporter has received spans.
- `GET /api/frontier/modules` and the workbench `FRONTIER MODULE GATE` now keep the project aligned with primary-source modern RAG methods. Modules are not promoted from `planned`/`locked` until a problem slice, Trace contract, latency/cost budget and same-set Eval justify them.

## Key files

- `app/cfpb.py`: real data acquisition and HTML/PDF chunking.
- `app/data_foundation.py`: deterministic normalization, validation, hash, deduplication, quality report and snapshot artifact.
- `app/storage.py`: PostgreSQL/MinIO/Redis health and source-of-truth persistence adapter.
- `app/rag.py`: embedding, Qdrant indexing/retrieval, prompting and citation checks.
- `app/reranker.py`: optional lazy Cross-Encoder V0.4 adapter; disabled by default and fail-closed when dependencies are missing.
- `app/reranker.py`: V0.4 supports the tested local llama.cpp `/reranking` backend, bounded batch calls and candidate text truncation; Python Cross-Encoder remains a fallback.
- `app/main.py`: public API and source manifest creation.
- `infra/postgres/001_data_foundation.sql`: source-of-truth schema contract for the production profile.
- `scripts/backfill_source_of_truth.py`, `scripts/migrate_sparse_index.py`, `scripts/dedupe_qdrant_index.py`: repeatable migration utilities.
- `evals/customer_support_benchmark_v0.3.json`: 50-case Golden Draft; not a production Gate until human review is recorded.
- `evals/customer_support_benchmark_v0.3_review_packet.json`: tracked structural audit packet; `reports/benchmark_review_v0_3.json` is the runtime copy.
- `static/`: visual RAG trace UI.
- `docs/`: learning materials.
- `docs/09-frontier-module-gate.md`, `docs/10-v04-reranker.md`: source-backed frontier rationale, Trace contract and V0.4 acceptance gate.
- `docs/11-v05-contextual-parent-child.md`: V0.5 failure hypothesis, build command and same-set evidence.
- `docs/17-v1-agent-eval.md`, `scripts/agent_eval.py`: V1 controlled Agent preflight; public API remains locked by `AGENT_ENABLED=false`.
- V1 preflight evidence: `routing_accuracy=1.0`, `dangerous_action_count=0`; the controller only calls `search_guidance`, `search_complaints`, and `build_ticket_draft`, persists a local `pending_approval` draft, and cannot send messages, write CRM, promise refunds or decide legal liability.
- `docs/19-golden-review-protocol.md`, `app/golden_review.py`: Review Center and two-person signoff API; current status is PENDING with 0/2 reviewers.
- `evals/customer_support_benchmark_v0.2.json`: versioned customer-support benchmark seed with answer/refuse-or-escalate actions, source URLs, risk slices and forbidden claims.
- `versions/`: stage-specific assembly manifests for V0.1 Dense, V0.2 Hybrid, V0.3 Intent + Metadata, optional V0.4 Reranker, production RAG and controlled Agent.
- Public repository checkpoint: https://github.com/daleselaji-dev/opensupport-rag ; latest CI run is green after adding a clean-runner pytest install.

## Required review output

Return exactly these sections:

1. **Architecture restatement** — describe data flow and authority boundary in your own words.
2. **Reproduction result** — list commands executed, pass/fail state and blocker.
3. **Blocking bugs** — only concrete bugs with file/function and reproduction evidence.
4. **RAG correctness** — retrieval, source separation, citations, cross-language embedding and prompt concerns.
5. **Security/data concerns** — PII, prompt injection, source freshness, misleading claims and unsafe outputs.
6. **Prioritized next actions** — at most five, ordered by impact.

## Next single task

Next: complete two-person Citation Support review on the generated 50-case packet, then run `scripts/release_check.py`; only after it passes start the isolated V1 environment with `scripts/start_agent_release.ps1` and rerun Agent Eval/approval smoke.
