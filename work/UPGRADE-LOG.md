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
- 参数消融：同一 8-case seed、batch=16、text=800 时，candidate-k=10 为 Hit@3=1.0、MRR=0.9375、p95=5346.49ms；candidate-k=20 为 Hit@3=1.0、MRR=1.0、p95=9908.5ms。结果写入 `reports/reranker_ablation_latest.json`。
- 决定：V0.4 可运行但暂不进入默认链路；candidate-k=20 的排名收益无法抵消相对 V0.3 Hybrid 约 81ms 的巨大延迟增幅。后续只有在更强失败切片和 Citation Support 证据改善时才重新评估。

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

## V0.6–V1 状态修正（2026-08-24）

- 真实问题：代码和报告已经推进到 V0.6、V0.7、V0.9 和 V1 预检，但工作台状态卡仍按旧占位逻辑显示“等待施工”，容易把“已实现但未发布”误解成“未实现”。
- 修复：`app/lifecycle.py` 现在读取 V0.5/V0.6 Eval、稳定性、安全、Agent preflight 和 release check 报告；`app/main.py:/api/lifecycle` 同时读取 Neo4j profile；`app/frontier.py` 明确把 Graph 和 PDF 页级基线标为实验状态。
- 当前显示：V0.5 同集 Eval 已通过但仍待人工 Citation Support；V0.6 受控一次纠错已完成；V0.7 Graph profile 已运行但等待全局问题集；V0.8 页级 PDF 基线已实现但官方 PDF CDN 403；V0.9 运维演练已通过但 release gate 仍被 Golden Review 阻塞；V1 Agent preflight routing accuracy=1.0、危险动作=0，但默认 API 仍锁定。
- 决定：状态只能反映证据，不能把自动分数或隔离预检当作正式发布批准。

## 生产数据快照与安全回归（2026-08-24）

- 数据升级：从 CFPB 官方 `complaints.csv.zip` 下载全量快照（官方 ZIP 约 1.35GB），抽取 12,000 条有公开叙述且保留真实 Complaint ID 的记录；47 个 Embedding/写入批次完成，新增 12,000 个文档，主 Dense/Sparse 索引达到 12,335 points，投诉 Chunk 达到 12,223，Manifest 一致。
- Contextual 重建：12,335 个源文档生成 19,087 个 Contextual Chunk，其中 11,100 个 parent-child 扩展；主索引未被覆盖，V0.5 仍是隔离派生索引。
- 新快照检索证据：V0.3 Hybrid 40-case Hit@3=0.975、MRR=0.8792、p95=142.82ms；V0.5 Hit@3=0.975、MRR=0.8958、p95=174.15ms；V0.6 Hit@3=0.975、MRR=0.8958、p95=164.8ms。指标以新快照为准，旧 335-point 报告仅保留作历史对照。
- 真实安全问题：12,335 points 扫描发现 2 条投诉叙述包含 `system prompt` 模式；它们是消费者公开文本，不是系统指令。修复了“全部候选被标记后仍把原文放回 Prompt”的漏洞：现在没有安全候选时直接停止生成、标记 `prompt_injection_evidence` 并转人工。安全报告区分 `isolated_prompt_injection_findings=2` 与 `unisolated=0`。
- 真实数据源限制：官方 CFPB HTML 页面在当前运行环境返回 403；已有 4 个官方指导 Chunk 保留在索引中，失败 URL/时间写入摄取进度，未伪造新指导内容。

## 完整回答/安全 Eval 与请求级风险门（2026-08-24）

- 真实失败：新快照的完整 50-case Answer Eval 首轮 citation validity=1.0、coverage=0.995，但拒答正确率只有 0.6；4 条“保证退款 / 账户动作 / 敏感信息”问题被 R1 当成普通问答。
- 根因：仅检查生成后的危险声明，不在生成前识别用户请求风险；模型可以给出不含禁止词但仍然越界的普通说明。
- 升级：加入 `detect_request_risks` 和 `request_safety_gate`，对退款/结果承诺、法律结论、账户动作、PII/隐藏数据、ATM 操作和提示注入在 LLM 前直接拒答/转人工。
- 复测：完整 50-case V0.6 Answer Eval citation validity=1.0、citation coverage=1.0、refusal correctness=1.0、forbidden claims=0、answer errors/timeouts=0、p95=26,758.29ms。
- 另一个真实故障：单条 R1 卡住会拖住整轮 Eval；增加每案例 timeout，超时计为失败并继续，不能用平均分隐藏。
- SLA 对照：600/300 token 预算仍使完整 50-case p95=23,038.79ms；关闭默认二次 Citation Repair、保留 grounded fallback 后，完整集质量不变且 p95 降至 13,118.83ms，达到 ≤20s 门。Citation Repair 仍可通过实验配置显式打开，不进入默认生产链路。

## V0.7 Graph 重建（2026-08-24）

- 在 12,335-point 官方快照上重建 Neo4j：12,223 Complaint、112 Source、41,802 条结构化关系；改用 `UNWIND` 批量写入，避免逐条 Cypher 循环成为新的摄取瓶颈。
- Graph smoke 通过：top issues/products 非空、计数非负、profile ready；它仍只适用于 Support Intelligence 聚合问题，不替代客服默认 RAG，也不代表责任或违法。

## V0.7：Graph-Augmented（可选）

- 真实问题：Support Intelligence 的全局聚合问题不是普通单次 Top-k 客服问题。
- 必要组件：Neo4j Community、结构化 CFPB 字段、白名单 Cypher 查询。
- 约束：只写入已有 Product/Issue/Company/Response/Source 字段，LLM 不生成关系。
- 证据：本机已写入 223 Complaint、112 Source、802 structured relationships；top issue/product 查询成功。
- 决定：保留为可选 Support Intelligence 模块，等待专门 Golden Set；不替换默认客服 RAG。

## V1 受控 Agent 预验收（仍锁定）

- 隔离端口临时开启 `AGENT_ENABLED=true`，真实 API 生成 PostgreSQL `pending_approval` 草稿并完成一次人工批准；Trace 包含 `tool_search_guidance`、`tool_search_complaints`、`build_ticket_draft` 和 `human_approval_gate`。
- 临时实例已关闭，公开端口仍返回 423；没有发送客服消息、写外部 CRM、承诺退款或作法律判断。

## V0.8：PDF Page Baseline（未晋级）

- 真实问题：PDF 表格/图表和页码在纯文本 RAG 中可能丢失。
- 当前施工：`app/multimodal.py` 支持本地 PDF 页级文本、页码和 SHA256 元数据，写入隔离 V0.8 集合。
- 外部事实：CFPB PDF CDN 当前返回 403，无法把下载失败伪装成已完成视觉数据集；视觉区域检索仍待真实 PDF 和页面级 Golden Set。
- 决定：保留代码和明确的 400/424 错误边界，暂不把 V0.8 设为默认。

## 生产硬化增量

- 真实问题：重复查询浪费 Embedding 调用；模型并发或卡住会拖垮本地服务；Reranker 长批次曾返回 500。
- 必要组件：Redis Embedding Cache、独立模型 timeout、Semaphore、API 滑动窗口限流、Reranker batch/truncation。
- 证据：同一问题第一次 `cache_hit=false`，第二次 `cache_hit=true`；Reranker 50 候选从一次超限请求改为 14 个受控 batch 后稳定完成。
- 决定：保留为生产横切层；V1 Agent 默认锁定，直到这些边界和质量门通过。
- 蓝绿演练：V0.5 contextual 集合通过 `/api/index/activate` 切换为 active，健康检查确认活动集合改变，再通过 `/api/index/rollback` 原子恢复 V0.1；没有删除派生索引。
