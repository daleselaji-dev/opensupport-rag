# 前沿模块 Gate：先理解，再引入主链路

OpenSupport 不把“用了多少前沿名词”当成技术先进性。每个模块都必须回答：

1. 它解决了当前哪个已观察到的问题？
2. 它的论文/官方实现原理是什么？
3. 它会增加哪些 Trace、索引、延迟和成本？
4. 哪个冻结 Benchmark 切片证明它有效？
5. 失败时能否回退到上一版？

## 当前主线

```text
Data Foundation
→ Dense + Sparse/BM25 + RRF
→ Intent + Metadata
→ Candidate expansion + source diversity
→ Contextual/Parent-child
→ Reranker
→ Corrective/Query Translation
→ Graph/Multimodal by route
→ Production RAG
→ Controlled Agentic Retrieval
```

Azure 的 RAG 指南把 Query Rewrite、Decomposition、HyDE、Hybrid、Reranking
和 Agentic Retrieval 分成不同检索阶段；这意味着它们不是可以任意叠加的同义词。
Contextual Retrieval 的核心是把 Chunk 放回文档上下文后再做 Embedding 和 BM25，
而不是简单地把更多文本塞进 Prompt。GraphRAG/DRIFT 主要针对全局和多跳问题，
不应默认替代普通客服检索。

最新公开评测也支持这种分层思路：NIST TREC 2025 RAG Track 将检索与带归因的生成分开评测；
EMNLP 2025 的知识选择研究专门分析 reranking/filtering 对下游 RAG 的影响；ACL 2025 的
SetR 工作进一步指出，多跳问题有时需要“集合选择”而不只是逐条排序。因此本项目先实现可
解释的 Cross-Encoder V0.4，再用失败切片决定是否需要集合级选择、Query Translation 或
Agentic Retrieval，而不是把所有方法串成一个不可归因的黑盒。

参考：

- [TREC 2025 RAG Track](https://trec-rag.github.io/trec25/)
- [How Does Knowledge Selection Help Retrieval Augmented Generation? (EMNLP 2025)](https://aclanthology.org/2025.findings-emnlp.218/)
- [Shifting from Ranking to Set Selection for Retrieval Augmented Generation (ACL 2025)](https://aclanthology.org/2025.acl-long.861/)

## 进入标准

模块只有在以下条件全部满足时才能成为默认主链路：

- 有真实失败切片，而不是为了展示论文名称；
- 有同一数据快照的 Before/After；
- 报告 Recall/MRR/nDCG、Citation Support、p50/p95 和成本；
- 新增 Trace 能解释启用、跳过、重试和回退原因；
- 高风险、安全和权限切片没有回归；
- 在旧版本失败时可以通过配置回滚。

当前工作台的 `FRONTIER MODULE GATE` 来自 `app/frontier.py`，展示模块、原理来源、
新增 Trace、进入条件和状态。`planned`/`locked` 不代表未学习，而是代表还没有足够
的项目证据让它成为默认组件。
