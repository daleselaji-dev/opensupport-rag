# Benchmark 之后的升级路线

## 当前判断

你已经掌握了 Dense + BM25 + RRF（Reciprocal Rank Fusion）。这意味着 V0.2 的第一阶段已经完成：能够解释两种召回各自解决什么问题，并用 RRF 合并排名。

下一步不应该直接堆 Reranker 或 Agent，而应该先冻结当前版本、运行客服 Benchmark、分析失败切片，再决定哪个组件值得加入。每次升级都必须有同一测试集上的 before/after、延迟、成本和失败案例。

## Phase 0：冻结并运行 Benchmark

先记录：

- 数据版本、索引集合名、Embedding 模型、Chat 模型；
- Dense、BM25、Hybrid 三种模式；
- 10 条客服 seed 和后续 50 条人工复核 Golden Set；
- Hit@3、MRR、nDCG、Recall、检索 p50/p95；
- 引用存在性、引用支持度、拒答正确率；
- 错误案例和按语言/意图/风险切片的结果。

当前数据 Gate 已通过本地镜像批次的 200 条唯一投诉门；累积索引有 223 个投诉 Chunk，Manifest 与 Qdrant 为 335/335，一条重复官方 Chunk 已从 Dense 和 Sparse 派生索引中删除。后续仍要把数据版本和人工 Golden Review 分开报告，不能用检索分数掩盖评测集未冻结。

V0.2 现在使用 Qdrant 1.17 的原生多语言 Sparse/BM25 命名向量。2026-08-24 在 335 点快照和 50-case draft 的 40 条可回答题上复跑：Dense Hit@3/MRR=0.900/0.8417、p95=59.80ms；Native Hybrid Hit@3/MRR=0.975/0.8667、p95=313.14ms。结论是“原生 Sparse 已正确运行，Hybrid 有召回信号但延迟代价明显”，必须先完成双人复核再冻结 Gate。

50 条 Golden Draft（40 条可回答检索题，仍待两人复核）已作为可复现实验包；结果支持保留 Hybrid 作为实验/候选默认，但还不能称为正式生产 Gate，因为 Golden Draft 尚未完成双人标注。

V0.3 的首轮结果已经显示方向有效：加入 Intent + Metadata 后，8 条 seed 的 Dense 和 Hybrid 都达到 Hit@3=1.0、MRR=1.0；但这只是小规模回归信号，不能替代数据 Gate 和人工复核 Golden Set。

## Phase 1：意图与 Metadata 过滤

当前最明确的失败是：

- “消费者如何提交 CFPB 投诉？”
- “企业如何处理 CFPB 投诉？”

两者都被召回到相似的企业投诉流程页面。

优先升级：

- 为每个官方 Chunk 增加 `topic`、`audience`、`process_stage`、`source_url_family`；
- 查询前做轻量意图分类：`consumer_submit`、`company_respond`、`billing_error`、`unauthorized_transaction`；
- 先做 metadata pre-filter，再做 Dense/BM25；
- 把意图切片加入 Benchmark。

验收：两个投诉流程 hard case 的正确官方 URL 命中；不能只看整体平均分。

## Phase 2：Reranker

只有当 Benchmark 证明“正确来源已进入候选集，但排名不够靠前”时，才加入 Cross-Encoder Reranker。

Trace 会变成：

```text
Dense candidates + BM25 candidates
→ RRF candidates
→ Reranker score
→ final evidence
```

验收必须同时满足：nDCG/MRR 或 Citation Precision 提升，且 p95 延迟和成本没有超过预算。如果没有质量收益，保留 RRF，不保留 Reranker。

当前代码已加入可选的 `BAAI/bge-reranker-v2-m3` Cross-Encoder 适配器，但默认关闭。它只读取 RRF 的候选集，不扫描全库；若依赖未安装，V0.4 接口返回 424，而不是静默降级。安装和启用后，必须在同一 Golden Set 记录 `rerank_score`、Before/After 排名、p95 和模型下载/内存成本。

## Phase 3：Chunk 与 Context Engineering

如果 Benchmark 显示正确页面命中了，但答案缺少关键条件，问题可能不是检索器，而是 Chunk：

- 标题与正文没有绑定；
- 法规条款被截断；
- 关键条件分散在多个 Chunk；
- 上下文只保留了相似句，没有保留例外条件。

这时做 Chunk A/B、标题增强、parent-child retrieval 和上下文去重，并同时测引用支持度和上下文长度。

## Phase 4：回答、引用与安全 Eval

检索稳定后，再评估：

- 每个事实是否有支持它的引用；
- 是否把消费者主张说成事实；
- 无答案时是否拒答/升级；
- 是否承诺退款或认定违法；
- R1 是否遵守引用格式。

RAGAS 类自动指标可以作为筛查工具，但人工盲评子集必须保留，不能让 LLM judge 成为唯一真值。

## Phase 5：生产型纯 RAG

最后才做：

- 增量同步与索引版本；
- PII 检测；
- 超时、重试、熔断、缓存；
- 结构化日志、Trace 和成本；
- 回滚与 CI 回归门禁；
- 客服人工采纳率、升级准确率和处理时长。

Agent 仍然等待 V0.3 质量门，不因为 RAG 能生成回答就提前进入。

## 面试表达

> 我先冻结 Dense、BM25 和 Hybrid 基线，用同一版本化客服 Benchmark 做检索、引用、安全和延迟对照。当前最优先的不是继续堆模型，而是通过失败切片判断问题属于意图路由、数据 Metadata、排序、Chunk 还是生成。只有当一个新组件在质量、延迟和成本上同时满足门槛，才会合并进主链路。

这体现的是可归因的实验设计，而不是组件堆叠。
