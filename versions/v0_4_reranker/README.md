# V0.4 Reranker (experimental, opt-in)

Principle: a bi-encoder/Dense or Sparse retriever searches the full index cheaply;
a Cross-Encoder reads `(question, candidate text)` pairs jointly and produces a
more precise relevance score. It must only run on a bounded high-recall
candidate set, never on the full corpus.

The adapter is implemented in `app/reranker.py` and the V0.4 assembly in
`app/rag.py`, but it is disabled by default. To run the experiment locally:

```powershell
.\.venv\Scripts\pip.exe install -r requirements-reranker.txt
$env:RERANKER_ENABLED = "true"
# restart the host API, then select V0.4 + Hybrid in the workbench
```

The tested local model is `Qwen3 Reranker 0.6B Q8_0 GGUF` (multilingual, about
639 MB). LM Studio's current API exposes chat and embedding endpoints but not a
dedicated rerank endpoint, so the project runs the same llama.cpp backend as a
small sidecar:

```powershell
.\scripts\start_reranker.ps1
# If CUDA is unavailable:
.\scripts\start_reranker.ps1 -Cpu
```

The API is `POST http://localhost:23146/reranking`. The original
`BAAI/bge-reranker-v2-m3` remains a supported Python fallback when the optional
dependency is installed. If either backend is unavailable, the API returns a
424 with the install/start action; it never silently labels RRF as reranking.

New Trace: `rerank_candidates` records model, candidate-k, final-k per source,
before/after chunk IDs and `rerank_score`. Source cards preserve the original
retriever score in `metadata.retriever_score`.

Acceptance: compare V0.3/V0.4 on the same frozen Golden Set and failure slices;
require an improvement in MRR/nDCG or citation support without violating the
p95/CPU/memory budget. Otherwise keep the adapter as an educational experiment
and retain V0.3 as the default.
