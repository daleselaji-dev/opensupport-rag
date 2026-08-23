# OpenSupport RAG

[![CI](https://github.com/daleselaji-dev/opensupport-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/daleselaji-dev/opensupport-rag/actions/workflows/ci.yml)

An inspectable, local-first customer-support RAG project. It starts with a real
CFPB data foundation and grows from Dense RAG to Hybrid, Reranked, hierarchical,
graph, multimodal and production RAG. The first query path remains small enough
to run locally: **LM Studio embeds → Qdrant retrieves two evidence types →
DeepSeek-R1 generates a cited answer**.

> This project is decision support only. It does not determine legal liability, refunds, account outcomes, or send customer messages.

## What V0.0 proves

- A RAG index is a derived read model, not the source of truth.
- Every downloaded source is normalized, validated, hashed and deduplicated before embedding.
- Invalid or short records are quarantined with an explicit reason.
- A Data Quality snapshot records the source languages, source types, lifecycle counts, accepted records and snapshot ID.
- The workbench displays the data lifecycle next to the RAG assembly so retrieval metrics cannot hide a data problem.

## What V0.1 proves

- Downloads real public complaint narratives from the CFPB API.
- Downloads and chunks official CFPB process, billing-dispute and Regulation Z guidance.
- Embeds each complaint with an OpenAI-compatible embedding API.
- Stores and searches vectors in Qdrant.
- Retrieves official guidance as `[S#]` and unverified consumer allegations as `[C#]`.
- Gives retrieved evidence to an LLM and requires cited, bounded answers.
- Shows a component assembly workbench and per-query runtime trace with durations, models, filters, scores, context size and citation checks.
- Includes a V0.2 objective eval workbench: real CFPB URL-linked seed cases, data consistency gates, Dense-vs-Hybrid/BM25+RRF comparison, and reproducible JSON/Markdown reports.
- The first screen includes live LM Studio/Qdrant/index/Eval status, wrapped component cards, and real question shortcuts so the workbench is informative before the first query.
- The RAG evolution board separates V0.0 data foundation, V0.1 Dense, V0.2 Native Hybrid, V0.3 Intent/Metadata, later production RAG and the controlled Agent; later stages remain locked until their prerequisites pass.
- Shows the original records, similarity scores, metadata and source links.
- V0.0 stores normalized source snapshots in MinIO and ingestion/chunk/index/trace records in PostgreSQL; Qdrant remains the derived read model.
- V0.2 now uses Qdrant 1.17 named Dense + native `qdrant/bm25` Sparse vectors with a transparent fallback to the historical in-process BM25 path.
- The workbench can run both retrieval Eval and local-R1 answer/safety Eval. Citation ID validity is not enough: low citation coverage or dangerous claims fail closed to human review.
- The `FRONTIER MODULE GATE` records the primary paper/official source, problem hypothesis, new Trace, entry criteria and current status for Query Translation, Contextual Retrieval, Reranking, GraphRAG/DRIFT, Multimodal Retrieval and Agentic Retrieval.
- V0.4 can run fully locally with a Qwen3 Reranker 0.6B Q8_0 GGUF served by llama.cpp at `http://localhost:23146/reranking`; it remains experimental because the first same-set seed result improved Hit@3 but reduced MRR and added roughly 35 seconds of retrieval latency.
- V0.5 contextual indexes can be activated and rolled back through `/api/index/activate` and `/api/index/rollback`; switching only changes an atomic alias pointer and never deletes the previous Qdrant collection.

## Quick start (local deployment)

1. Open **LM Studio → Developer → Start server**. Its default API address is `http://localhost:1234`.
2. In LM Studio, load `DeepSeek-R1-Distill-Qwen-7B-Q4_K_M` as the local R1 chat model and download the official Qwen3-Embedding-0.6B GGUF embedding model. They must be different models. The reproducible CLI source is:

   ```powershell
   lms get https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF --gguf --yes
   ```
3. List the exact identifiers we need:

   ```powershell
   Invoke-RestMethod http://localhost:1234/v1/models | ConvertTo-Json -Depth 5
   ```

4. Copy the environment template:

   ```powershell
   Copy-Item .env.example .env
   ```

5. Put the two model identifiers into `.env` as `CHAT_MODEL` and `EMBEDDING_MODEL`; leave `EMBEDDING_FAMILY=qwen`.
6. Install and start Docker Desktop, then start **Qdrant only**. This project maps Qdrant's HTTP port to local `16333` because some Windows environments reserve `6333`/`6334`:

   ```powershell
   docker compose up -d qdrant
   ```

   The production profile is available when you are ready for source-of-truth and queue services:

   ```powershell
   docker compose --profile core up -d
   ```

   It adds PostgreSQL (`15432`), MinIO (`19000`), Redis (`16379`) and a Celery worker. Observability and Neo4j are separate profiles.

   For the optional V0.7 graph experiment:

   ```powershell
   docker compose --profile graph up -d neo4j
   ```

   Start the observability profile when you want system metrics and OTLP traces:

   ```powershell
   docker compose --profile observability up -d
   ```

   Prometheus is at `http://localhost:19090`, Grafana at `http://localhost:13001`, and the API metrics endpoint is `http://localhost:18000/metrics`.

7. Create a Python virtual environment and start the app on Windows. This lets the app reach LM Studio safely on `localhost`:

   ```powershell
   & 'C:\Users\ACE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

8. Open [http://localhost:18000](http://localhost:18000), import CFPB records, then ask a Chinese or English question. The workbench shows the component assembly and each query's trace. Use `OBJECTIVE EVAL` to compare Dense baseline with Hybrid + RRF before claiming an upgrade.

The project supports the official CFPB API and official bulk CSV ZIP; no complaint corpus is committed to this repository. The current verified local snapshot was built from the official bulk ZIP. After import, `data/data_quality_latest.json` and `data/ingest_manifest.json` record the reproducible local snapshot.

If CFPB's public JSON/CSV endpoint is temporarily WAF-blocked, download the
official CSV from the [Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/), save it as
`data/raw/complaints.csv`, and call:

```powershell
$body = @{filename="complaints.csv"; limit=200; year=2024} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:18000/api/ingest-local -ContentType application/json -Body $body
```

The current CSV export omits complaint IDs; the local path uses a stable row
SHA256 and marks `identity_source=csv_row_sha256` instead of pretending it is an
official ID.

For the reproducible public mirror snapshot used in development, download
`sample_1000.csv` from [the CFPB-derived dataset](https://huggingface.co/datasets/claritystorm/cfpb-consumer-complaints/blob/main/README.md), save it as
`data/raw/cfpb_mirror_sample_1000.csv`, then run:

```powershell
$body = @{filename="cfpb_mirror_sample_1000.csv"; source_kind="cfpb_mirror"; product_filter="any"; limit=200} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:18000/api/ingest-local -ContentType application/json -Body $body
```

This mirror preserves real CFPB complaint IDs and points each complaint back
to its CFPB detail URL while recording the mirror URL in metadata. The report
does not claim that the mirror is a live CFPB snapshot.

For the production-scale local snapshot used in the latest evidence, download
the official CFPB bulk ZIP and extract a bounded narrative set without committing the ZIP:

```powershell
curl.exe -L --fail -o data/raw/cfpb_complaints_full.csv.zip https://files.consumerfinance.gov/ccdb/complaints.csv.zip
$env:PYTHONPATH = "."
.\.venv\Scripts\python.exe scripts/prepare_official_bulk_snapshot.py --limit 12000
.\.venv\Scripts\python.exe scripts/ingest_bulk_snapshot.py --limit 12000 --batch-size 256
```

The checkpointed worker preserves official Complaint IDs and URL provenance, skips already
indexed chunk IDs, and writes `data/bulk_ingest_progress.json`. The verified snapshot contains
12,000 new complaint records and 12,335 main Qdrant points.

### Online embedding fallback

If the local Qwen download is too slow, keep Chat Model local and switch only Embeddings to Alibaba Cloud Model Studio:

```text
EMBEDDING_PROVIDER=qwen-api
EMBEDDING_BASE_URL=https://<WorkspaceId>.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
EMBEDDING_API_KEY=sk-your-dashscope-key
EMBEDDING_MODEL=qwen3.7-text-embedding
EMBEDDING_FAMILY=qwen-api
```

Alibaba's official Model Studio documentation recommends `qwen3.7-text-embedding` for pure text/code, lists about CNY 0.0005 per 1K input tokens, and documents 200+ languages, 128K context and 1024 dimensions by default. `text-embedding-v4` is the stable fallback with 100+ languages. Region availability must be checked in your account. Do not commit the API key.

The app automatically batches Qwen API requests in groups of 10, within the official endpoint limits.

### Later: all-Docker mode

The `app` service in `docker-compose.yml` is optional. It reads `DOCKER_LM_STUDIO_BASE_URL` and `DOCKER_EMBEDDING_BASE_URL` from `.env`. Expose LM Studio carefully to Docker. On Windows this may require starting the server with `--bind 0.0.0.0`; doing that exposes the model API beyond localhost, so only use it on a trusted local network and enable authentication if appropriate.

## The V0.1 RAG trace

```text
Question
  → Qwen3-Embedding-0.6B in LM Studio
  → Qdrant vector similarity search
  → top official CFPB guidance `[S#]` + top public CFPB complaints `[C#]`
  → prompt with evidence + guardrails
  → LM Studio chat model answer with [C1], [C2] citations
```

## V0.2 evaluation and upgrade trace

The query form can switch between `Dense baseline` and `Hybrid: Dense + Qdrant Sparse/BM25 + RRF`. Hybrid traces add `sparse_backend`, `bm25_guidance`, `bm25_complaints`, and `fusion_rrf`, with component ranks and scores preserved in source metadata. The eval button runs the same versioned, URL-linked benchmark and stores reports under `reports/`. The current local snapshot is derived from CFPB's official bulk CSV ZIP: 12,000 new public-narrative complaints were embedded in 47 batches, producing 12,223 cumulative complaint chunks and 12,335 matching Dense/Sparse Qdrant points. The 50-case Golden Draft is still explicitly blocked on two-person human review.

Use `只运行检索 Trace` to inspect Embedding and retrieval without waiting for Chat LLM generation. The component inspector explains each node even before a query has run. `RAG EVOLUTION` separates project-stage status from service health. V0.4 Cross-Encoder is visible as an experimental opt-in path; it remains outside the default chain until the frozen benchmark proves a ranking problem.

Full-query execution first renders the retrieval Trace and marks `generate_answer` as pending, then calls the local DeepSeek-R1 Chat LLM. The prompt is bounded to a compact authority-balanced subset so LM Studio's context limit is not exceeded; all six retrieved source cards remain visible. `POST /api/retrieve-stream` streams `running` and `completed` events for each Dense/Sparse/RRF stage; `POST /api/retrieve-preview` remains the non-stream diagnostic path.

Read [docs/04-v02-eval-and-upgrade.md](docs/04-v02-eval-and-upgrade.md) for the exact problem → required upgrade → trace/structure/function/benefit mapping and the measured ablation result.
Read [docs/05-customer-support-benchmark.md](docs/05-customer-support-benchmark.md) for the interview/enterprise explanation and the versioned customer-support benchmark design.
Read [docs/06-next-upgrade-roadmap.md](docs/06-next-upgrade-roadmap.md) for the order of work after the Dense + BM25 + RRF baseline.

Read [docs/01-rag-basics.md](docs/01-rag-basics.md), [docs/02-lm-studio-setup.md](docs/02-lm-studio-setup.md), then [docs/03-v01-hands-on.md](docs/03-v01-hands-on.md).

## Verification

Once Qdrant and LM Studio are running:

```powershell
.\.venv\Scripts\python.exe -m pytest
Invoke-RestMethod http://localhost:18000/api/health
```

The health endpoint reports LM Studio availability, loaded/visible model IDs, Qdrant availability, index size, and whether placeholder model IDs are still configured.

## Source and limitations

- CFPB Complaint Database: <https://www.consumerfinance.gov/data-research/consumer-complaints/>
- CFPB API: <https://cfpb.github.io/api/ccdb/api.html>
- Complaint narratives are public only after consumer consent and CFPB processing, but they are not independently verified facts.
- Complaint volume is not a measure of company wrongdoing or consumer harm.
- The system must not claim a company violated the law, must refund money, or completed an account investigation.

## Roadmap

- V0.0: data cleaning, lineage, deduplication, quarantine and source-of-truth contracts.
- V0.1: Dense RAG baseline.
- V0.2: native Qdrant Sparse/BM25 + Dense/RRF, with Chinese-tokenization regression tests.
- V0.3: intent routing + Metadata filters.
- V0.4: optional multilingual Cross-Encoder reranking only if Benchmark evidence shows a ranking problem; install `requirements-reranker.txt` and enable `RERANKER_ENABLED=true` explicitly.
- V0.5: deterministic contextual/parent-child index; V0.6: bounded corrective retrieval; V0.7–V0.8: optional structured Graph and multimodal page experiments.
- V0.9: production RAG operations and rollback.
- V1.0: controlled Agent after production RAG quality and safety gates pass.
- V1 Agent preflight exists at `scripts/agent_eval.py`, but `AGENT_ENABLED=false` keeps the public endpoint locked until V0.9 and human review gates pass.

Read [docs/07-data-foundation.md](docs/07-data-foundation.md) before changing the ingestion pipeline.
Read [docs/16-release-checklist.md](docs/16-release-checklist.md) before calling the repository production-ready or writing resume metrics.
The live workbench Review Center documents the two-person Golden Set signoff required before V1 unlock.

## Release readiness audit

Run the local objective audit before publishing a release:

```powershell
python -m scripts.release_check
```

Exit code `0` means the data, retrieval and answer-safety gates pass. Exit code
`2` is intentional while a gate is incomplete; the JSON output identifies the
exact blocker instead of allowing a strong retrieval score to hide it.
