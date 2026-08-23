# V0.4：Cross-Encoder 精排实验

## 为什么不是把它直接接到默认链路

Dense Embedding 是 Bi-Encoder：文档可以离线编码，查询时只需一次向量比较，适合全库高召回。
Cross-Encoder 把同一个问题和每个候选文本放在一起计算相关性，通常更精确但逐候选计算，
所以它不能替代全库检索，只能接在 Dense/Sparse/RRF 候选集之后。

这一区分与 Azure 的 RAG 检索分层、TREC 2025 RAG Track 的检索/归因拆分和 EMNLP 2025
对知识选择（reranking/filtering）的独立分析一致：先让候选集 Recall 足够，再判断精排是否
改善最终证据选择。相关来源：

- [Azure RAG information retrieval guide](https://learn.microsoft.com/azure/architecture/ai-ml/guide/rag/rag-information-retrieval)
- [TREC 2025 RAG Track](https://trec-rag.github.io/trec25/)
- [How Does Knowledge Selection Help Retrieval Augmented Generation? (EMNLP 2025)](https://aclanthology.org/2025.findings-emnlp.218/)
- [`BAAI/bge-reranker-v2-m3` model card](https://huggingface.co/BAAI/bge-reranker-v2-m3)

## 本项目的最小装配

```text
Intent/Metadata
→ Dense Top-50 + Qdrant Sparse/BM25 Top-50
→ RRF candidate set
→ Cross-Encoder(question, candidate text)
→ 官方 Top-3 + 投诉 Top-3
→ Context → DeepSeek-R1 → citation/safety gate
```

新增 `rerank_candidates` Trace，记录：模型 ID、候选数量、每类最终 k、Before/After chunk ID、
原检索分数和 `rerank_score`。候选集为空、依赖缺失或模型下载失败都不会静默回退并冒充成功。

## 运行方式

```powershell
.\.venv\Scripts\pip.exe install -r requirements-reranker.txt
$env:RERANKER_ENABLED = "true"
# 重启 API，然后在工作台选择 V0.4 + Hybrid
```

当前已实际下载并启动多语言 `Qwen3 Reranker 0.6B Q8_0 GGUF`（约 639MB），由 LM Studio
自带的 llama.cpp 后端以独立端口提供 `/reranking`；这避免把一个专用排序模型误当成 Chat
模型调用。一次本地冒烟请求中，账单相关段落得分约 `0.9998`，无关段落约 `0.00001`。在
335 点快照的真实 V0.4 查询中，50 个候选被拆成 14 个 batch，Rerank 耗时约 `34.8s`；这是
当前本地模型/硬件的真实延迟，不会被隐藏。`RERANKER_BATCH_SIZE` 和 `RERANKER_TEXT_CHARS`
可在安全范围内调参，任何改变都要重新跑同一 Benchmark。
`BAAI/bge-reranker-v2-m3` 仍保留为可选 Python 后端。若本地 Reranker 服务不可用，工作台
显示 424 和启动动作，V0.1–V0.3 不受影响。

## 进入默认链路的 Gate

在同一个已复核的 Golden Set 上比较 V0.3 与 V0.4：

- MRR、nDCG@10、Citation Precision/Support 至少一个稳定改善；
- Recall 不下降；
- p50/p95、CPU/内存和模型冷启动成本在预算内；
- 高风险拒答、消费者主张/官方指导边界无回归；
- 失败时可回退到 V0.3，不删除原始 RRF Trace。

如果只有平均分上涨但失败切片、延迟或安全回归，V0.4 仍保持实验状态。
