# OpenSupport RAG 升级日志

这份日志把每次升级写成“真实问题 → 必要组件 → Trace/结构变化 → 同集证据 → 是否接受”。
它是项目叙事和面试复盘的事实来源，不记录没有运行过的提升百分比。

## V0.0：数据地基

- 真实问题：CFPB API/CSV 受到 WAF 403，来源并非始终可下载；重复导入会污染派生索引。
- 必要组件：规范化、SHA256、去重、隔离、PostgreSQL/MinIO 真相源、Manifest。
- 结构变化：`source → validated → normalized → deduplicated → indexed → active`，Qdrant 只作为可重建读模型。
- 证据：镜像批次接受 200 条投诉，重复 0，隔离 0；累计 Qdrant/Manifest 335/335。
- 决定：接受为基础门；数据源失败记录为可操作 503，不伪装成空数据。

## V0.1：Dense RAG

- 真实问题：中文问题需要召回英文 CFPB 指导和投诉案例，同时保留官方证据与消费者主张的权威边界。
- 必要组件：Qwen3 Embedding、Qdrant Dense、DeepSeek-R1、引用卡片。
- Trace：`embed_query → retrieve_guidance → retrieve_complaints → assemble_context → generate_answer → guardrail_review`。
- 决定：保留为可解释基线，不用生成模型自评检索质量。

## V0.2：Native Sparse + RRF

- 真实问题：精确术语、法规编号和机构名称可能被纯语义检索压低；进程内 BM25 不适合持续运行。
- 必要组件：Qdrant named Dense/Sparse、`qdrant/bm25`、RRF。
- Trace：增加 `sparse_backend`、两个 BM25 候选分支和 `fusion_rrf`。
- 证据：40 条可回答 draft 复跑中 Native Hybrid Hit@3=0.975、MRR=0.8667，但 p95=313.14ms；因此记录为候选方案，不把“分数更高”写成生产结论。

## V0.3：Intent + Metadata

- 真实问题：消费者提交投诉和企业响应流程语义相近，容易召回错误官方页面。
- 必要组件：规则 Intent Router、audience/source URL family 过滤。
- Trace：增加 `route_intent → metadata_filter`。
- 决定：保留在默认纯 RAG 路径；意图切片必须继续扩充人工 Golden Set。

## V0.4：Cross-Encoder Reranker

- 真实问题：RRF 候选已经命中正确来源，但需要验证“重排是否让正确证据更靠前”。
- 必要组件：Qwen3 Reranker 0.6B Q8_0 GGUF + llama.cpp `/reranking`；不是把专用模型误当 Chat 模型。
- Trace：增加 `rerank_candidates`，记录 candidate-k、batch size、文本截断、Before/After Chunk ID 和 `rerank_score`。
- 真实故障：50 个候选一次性请求时，长投诉 Chunk 使 llama.cpp `ubatch` 超限并返回 500；改为 14 个受控 batch 后稳定完成。
- 证据：8-case seed Hit@3=1.0、MRR=0.9375、p95=35168.92ms；V0.3 Hybrid MRR=1.0、p95=81.38ms。
- 决定：V0.4 可运行但暂不进入默认链路；后续只调 candidate-k/batch/truncation，并以同集 MRR/nDCG、Citation Support、p95 和成本决定接受或撤回。

## 生成安全故障：为什么会频繁人工复核

- 首次证据：11-case Answer Eval 中 10 条进入 `extractive_grounded_fallback`，主要原因是 `citation_coverage`；其中 8 条本来是 answer 案例。
- 根因一：R1 输出全角 `【S1】`，解析器只识别 ASCII `[S1]`。
- 根因二：系统只在“没有有效引用”时运行修复，未覆盖“有一个引用但其他事实句未引用”。
- 修复：引用变体规范化；低覆盖率也触发一次 Citation Repair；Trace 保存修复前/后覆盖率和 fallback 原因；Prompt 改为最多三条、每条事实句必须有引用。
- 复测证据：账单错误单条查询 `needs_human_review=false`、citation coverage=1.0；完整 Answer Eval 的最终报告仍保留人工盲评要求，自动 PASS 不等于企业上线证明。

## 当前下一步

## V0.5：Contextual / Parent-Child

- 真实问题：Data Quality 报告发现超长投诉 Chunk；孤立子 Chunk 缺少标题/来源身份。
- 必要组件：隔离 contextual Dense/Sparse 集合、确定性上下文前缀、父子 Chunk、稳定 child ID。
- 结构变化：V0.3 默认集合保持不变；V0.5 构建 335 个源文档 → 432 个 contextual Chunk，145 个长文档子 Chunk。
- Trace：增加 `contextual_backend` 和 `expand_parent`，记录集合、chunk size、overlap、父文档和子 Chunk 数。
- 证据：40 条 Golden Draft 上 Hit@3=0.975、MRR=0.8958、p95=108.28ms；V0.3 Hybrid 为 0.975/0.8667/313.14ms。
- 决定：保留为有希望的实验，等待双人 Golden Review 和人工 Citation Support 后再设为默认。

## 当前下一步

1. 完成 V0.4 candidate-k/batch/truncation 消融，决定是否撤回默认 Reranker。
2. 对 V0.5 的 `text_too_long`、跨语言和 Citation Support 切片做人工复核和回答 Eval。
3. 只有 V0.4–V0.9 质量门通过后，才解除页面和 API 中 V1 Controlled Agent 的锁定。

## V0.7：Graph-Augmented（可选）

- 真实问题：Support Intelligence 的全局聚合问题不是普通单次 Top-k 客服问题。
- 必要组件：Neo4j Community、结构化 CFPB 字段、白名单 Cypher 查询。
- 约束：只写入已有 Product/Issue/Company/Response/Source 字段，LLM 不生成关系。
- 证据：本机已写入 223 Complaint、112 Source、802 structured relationships；top issue/product 查询成功。
- 决定：保留为可选 Support Intelligence 模块，等待专门 Golden Set；不替换默认客服 RAG。

## 生产硬化增量

- 真实问题：重复查询浪费 Embedding 调用；模型并发或卡住会拖垮本地服务；Reranker 长批次曾返回 500。
- 必要组件：Redis Embedding Cache、独立模型 timeout、Semaphore、API 滑动窗口限流、Reranker batch/truncation。
- 证据：同一问题第一次 `cache_hit=false`，第二次 `cache_hit=true`；Reranker 50 候选从一次超限请求改为 14 个受控 batch 后稳定完成。
- 决定：保留为生产横切层；V1 Agent 默认锁定，直到这些边界和质量门通过。
- 蓝绿演练：V0.5 contextual 集合通过 `/api/index/activate` 切换为 active，健康检查确认活动集合改变，再通过 `/api/index/rollback` 原子恢复 V0.1；没有删除派生索引。
