# V0.2：从“能回答”升级到“能证明”

## 这轮先解决什么问题

V0.1 的端到端链路已经能回答，但它不能证明三件事：

1. 真实索引是否真的有 200 个唯一投诉；
2. Manifest 是否与 Qdrant 的真实点数一致；
3. Dense 检索失败时，BM25 + RRF 是否真的改善了正确来源的排名。

工作台的 `OBJECTIVE EVAL` 用 8 个中英文问题绑定 CFPB 官方 URL，直接测检索，不让 Chat LLM 自评。投诉文本仍然只作为未经核实的案例，不用于判断违法。

## 组件变化

### V0.1 Dense baseline

```text
问题
  → Qwen3-Embedding-0.6B
  → Qdrant cosine search（官方分支 + 投诉分支）
  → 上下文
  → Chat LLM
  → 引用校验
```

Trace 中会看到 `embed_query`、`retrieve_guidance`、`retrieve_complaints`、`assemble_context`、`generate_answer` 和 `validate_citations`。

### V0.2 Hybrid 实验

```text
问题
  ├→ Qwen 向量 → Dense official/case candidates ─┐
  └→ BM25      → Sparse official/case candidates ─┤→ RRF → 上下文 → LLM
```

Trace 增加：

- `retrieve_dense_guidance` / `retrieve_dense_complaints`：向量召回候选；
- `bm25_guidance` / `bm25_complaints`：精确词项召回候选；
- `fusion_rrf`：记录两个分支的候选数量和融合结果；
- 融合后的 source metadata 保存 `dense_rank`、`bm25_rank`、`dense_score`、`bm25_score`、`rrf_score`。

本版本已经使用 Qdrant 1.17 的原生命名 Sparse 向量和 `qdrant/bm25`，不再在每次查询时滚动扫描全库；Trace 保留 Dense、Sparse、RRF 三条证据链。

## 当前真实结果（2026-08-24，335 点快照复跑）

| 模式 | 40 条可回答问题 Hit@3 | MRR | 检索 p95 |
|---|---:|---:|---:|
| Dense（V0.3，同一 50-case draft） | 0.900 | 0.8417 | 59.80 ms |
| Native Hybrid + RRF | 0.975 | 0.8667 | 313.14 ms |

结论：Native Hybrid 在当前 40 条可回答 draft 上带来更高 Hit@3/MRR，但 p95 约为 Dense 的 5 倍；这不是“BM25 单独提升”的因果证明。Golden Draft 尚未人工冻结，因此保留为可对照候选，不宣称上线收益。

## 当前失败不是“系统坏了”

- `唯一投诉案例数`：真实镜像批次已接受 200 条，累积索引共有 223 个投诉 Chunk；
- `Manifest 与真实点数一致`：当前为 335/335，并在 PostgreSQL/MinIO 保存快照；
- `complaint-process-zh` 和 `complaint-process-en`：召回了企业投诉处理页，而非消费者提交投诉页。这是“语义相近但业务意图不同”的真实 hard case，下一轮需要 BM25、标题/URL 过滤或 query intent 标签共同解决。

## 运行与验收

工作台：`http://localhost:18000`

工作台现在把两种状态分开：

- `LIVE STATUS`：LM Studio、Qdrant、模型和索引是否在线；
- `RAG EVOLUTION`：V0.1 基础 RAG、V0.2 Hybrid、V0.3 Intent/Metadata、V0.4 Cross-Encoder 实验和后续生产型纯 RAG/Agent 的阶段状态和前置条件。

点击组件会打开组件检查器，显示输入、输出、依赖和是否已经出现在 Trace 中。`只运行检索 Trace` 只执行 Embedding 和检索，不调用慢速 Chat LLM，因此可以先观察 RAG 的前半段。

Hybrid 运行使用 `POST /api/retrieve-stream`：每个步骤都会先发 `running`，完成后发真实耗时、候选数、分数和结果。右侧 V0.1/V0.2 结构图节点与这些事件同步，不需要等整个检索函数结束。

完整查询会先把检索 Trace 渲染到页面，并将 `generate_answer` 标为 pending，再等待本地 DeepSeek-R1 Chat LLM。Prompt 只发送官方证据与投诉案例的紧凑子集，但页面仍保留全部召回证据卡片。若 R1 漏掉引用，会进入受控的 `repair_citations` 步骤，只能补充已有 `[S#]/[C#]`，然后再次经过确定性校验；若 Chat 仍慢或离线，检索 Trace 和证据不会消失。

```powershell
# Dense baseline
Invoke-RestMethod -Method Post 'http://localhost:18000/api/eval/run?retrieval_mode=dense'

# Hybrid + RRF
Invoke-RestMethod -Method Post 'http://localhost:18000/api/eval/run?retrieval_mode=hybrid'
```

报告会写入：

- `reports/eval_latest_dense.json` / `.md`；
- `reports/eval_latest_hybrid.json` / `.md`；
- `reports/eval_latest.json` / `.md`（最近一次运行）。

只有同时满足数据一致性、唯一投诉数量、检索质量和安全/引用回归，才可以把版本标为通过。没有通过的报告也要保留，作为失败案例和面试中的消融证据。

## V0.4 本地 Reranker 首轮实测

同一 8 条 seed、同一 Hybrid 候选集上：

| 装配 | Hit@3 | MRR | Retrieval p95 |
|---|---:|---:|---:|
| V0.3 Hybrid/RRF | 1.000 | 1.000 | 81.38 ms |
| V0.4 Hybrid + Qwen3 Reranker 0.6B Q8_0 | 1.000 | 0.9375 | 35,168.92 ms |

结论：本地 Reranker 已经可以运行，Trace 记录了 50 个候选到 3+3 证据的重排；但首轮没有提升 Hit@3，MRR 反而下降，延迟增加约两个数量级。因此 V0.4 不进入默认主链路，保留为可调实验。下一步若继续调参，必须记录 candidate-k、batch size、截断长度和同集结果；没有质量收益就撤回。

## 企业是否会认可当前 Eval

当前标准是企业评测的正确骨架，但还不是企业上线证明。企业通常会要求五层证据：

1. **P0 数据与血缘**：唯一文档、重复检测、来源 URL、版本和可复现 Manifest；
2. **P1 检索质量**：人工复核 Golden Set，按语言、问题类型、来源类型切片，测 Recall@k、MRR、nDCG 和延迟；
3. **P2 回答与引用**：引用是否真实支持结论、答案完整性、无证据拒答，不能只看 LLM 自评分；
4. **P3 安全边界**：提示注入、PII、冲突来源、退款/违法诱导和无答案请求的回归测试；
5. **P4 运营与业务结果**：p50/p95、超时率、成本、数据新鲜度、人工升级准确率和实际处理时长。

本项目当前 P0 数据/Manifest 已通过本地 200 条投诉门，P1 的 50-case Golden Draft 仍待双人复核；P2/P3 的 11-case 自动回归已通过，但仍需扩大人工盲评和运行指标，因此工作台不会把当前结果包装成生产就绪。
