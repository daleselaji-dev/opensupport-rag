# OpenSupport RAG 实施计划

## 产品目标

构建本地优先的双语消费投诉 RAG：中文或英文提问，经 LM Studio 的 Qwen3-Embedding-0.6B 转成向量，Qdrant 分别召回 CFPB 官方指导和真实投诉案例，再由本地聊天模型生成带引用的中文回答。

投诉案例用于说明相似模式；官方指导和法规用于支持一般流程信息。系统不认定违法、不决定赔偿、不发送客服消息。

## 生产级能力主线（新增）

项目先从 V0.0 Data Foundation 开始：PostgreSQL/MinIO 作为真相源，Qdrant
作为派生索引。原始 CFPB 资料必须经过下载、校验、规范化、Hash、去重、
隔离、Chunk 和血缘记录后才允许进入 Embedding。工作台会显示每个生命周期
状态的数量、重复与隔离原因，避免用一个漂亮的检索分数掩盖数据问题。

生产 Profile 的默认技术栈为 FastAPI、PostgreSQL、MinIO、Qdrant、Redis、
Celery、OpenTelemetry、Prometheus/Grafana 和 Langfuse；本地学习路径可以只
启动 Qdrant、LM Studio 和 FastAPI。生产基础设施 Schema 位于
`infra/postgres/001_data_foundation.sql`，本轮本地质量快照位于
`data/data_quality_latest.json`。

## 版本路线

| 版本 | 施工内容 | 教学重点 | 质量门 |
|---|---|---|---|
| V0.0 | 数据清洗、Hash、去重、隔离、血缘、快照 | 为什么数据质量先于检索指标；真相源和派生索引 | ≥200 唯一投诉；重复 0；Manifest/Qdrant 一致；失败可解释 |
| V0.1 | 双证据 RAG MVP | Embedding、Qdrant、上下文、引用 | 真实数据导入、中文查询、可点击引用 |
| V0.2 | Eval Gate → Qdrant Native Sparse/Hybrid Search | 先测数据一致性/Hit@3/MRR/延迟，再决定 BM25、RRF、Reranker | Dense/Native Hybrid 同集对照；最终 50 条真实 Golden Set 与可复现报告 |
| V0.3 | Intent + Metadata 过滤 | 问题意图、audience、source URL family、问题导向 Trace | 投诉流程 hard case 修复，召回不下降 |
| V0.4 | Reranked RAG | Bi-Encoder/Cross-Encoder、候选集和延迟权衡 | MRR/nDCG 或 Citation Precision 有实测改善 |
| V0.5 | Contextual + Hierarchical | 结构化 Chunk、Parent-child、RAPTOR、上下文预算 | Citation support 和完整性改善，延迟受控 |
| V0.6 | Adaptive/Corrective | Query rewrite、证据评分、有限重试和拒答 | 无证据时稳定拒答，不允许无限循环 |
| V0.7 | Graph-Augmented | 投诉关系、多跳和全局问题 | Graph-only/Hybrid 同集对照，可回溯原始投诉 |
| V0.8 | Multimodal | PDF、表格、页面检索和视觉证据 | 页面级 Recall 与引用可验证 |
| V0.9 | 生产型纯 RAG | 数据血缘、增量、PII、缓存、监控、回滚 | 失败可观察、索引可回滚、陌生人可启动 |
| V1.0 | 受控 Agent | 状态机、工具边界、人工批准 | 仅补全信息与工单草稿，不写 CRM/不发送 |

## V0.1 运行步骤

1. 在 LM Studio 下载官方 Qwen3-Embedding-0.6B GGUF，启动 Developer Server。
2. 运行 `Invoke-RestMethod http://localhost:1234/v1/models`，把实际 DeepSeek 和 Qwen Embedding ID 写入 `.env`。
3. 启动 Docker Desktop，运行 `docker compose up -d qdrant`。
4. 运行 `scripts/check_local_setup.ps1`。
5. 启动 `./.venv/Scripts/python.exe -m uvicorn app.main:app --reload`。
6. 打开 `http://localhost:18000`，导入 2024 CFPB 信用卡投诉并提问。本机因为端口策略使用 LM Studio `23145`、Qdrant `16333`、API `18000`。

V0.0 首次摄取后先打开工作台的 `DATA FOUNDATION` 卡片，检查接受、重复、隔离、快照 ID 和生命周期数量，再运行 Eval。不要在 Data Quality 未生成或 Manifest 不一致时解释 Hybrid 分数。

如果本地 Qwen Embedding 下载过慢，可只切换 Embedding Provider 到阿里云百炼的 `qwen3.7-text-embedding`，Chat 仍留在 LM Studio；API key 只放在 `.env`，不提交仓库。

详细教学请依序阅读：

- [第 1 课：RAG 基础](../docs/01-rag-basics.md)
- [第 2 课：LM Studio 设置](../docs/02-lm-studio-setup.md)
- [第 3 课：亲手启动 V0.1](../docs/03-v01-hands-on.md)
- [第 4 课：V0.2 Eval 与升级](../docs/04-v02-eval-and-upgrade.md)
- [第 5 课：客服 Benchmark 与企业验收](../docs/05-customer-support-benchmark.md)
- [第 6 课：Benchmark 之后的升级路线](../docs/06-next-upgrade-roadmap.md)
- [第 7 课：V0.0 Data Foundation](../docs/07-data-foundation.md)
- [第 8 课：回答与安全 Eval](../docs/08-answer-safety-eval.md)

## V0.1 验收

- 真实 CFPB 投诉与官方指导均被索引；
- 中文问题可召回英文证据；
- 回答含 `[S#]` 官方引用和 `[C#]` 投诉案例引用；
- 每个引用都有页面证据卡片和原始 URL；
- API 不暴露 Python 堆栈；
- `pytest` 通过；
- 不能输出退款承诺、违法认定或账户调查结论。

## Agent 进入规则

V0.1 后只学习 Agent 概念，V0.3 的评测、回滚、安全和运行门通过后，才施工 V0.4。第一个 Agent 只能追问信息、检索证据和生成待人工批准的工单草稿。

## 当前实际状态

工作台已经把“数据问题 → 必须升级的组件 → Trace 变化 → Eval 结果”连起来。V0.0 已完成规范化、Hash、去重、隔离、Postgres/MinIO 真相源和 Qdrant 派生索引；镜像批次已接受 200 条投诉，累积 335 points，Manifest 与索引一致。2026-08-24 在 50-case draft 的 40 条可回答题上复跑：Dense Hit@3/MRR=0.900/0.8417、p95=59.80ms，Native Hybrid=0.975/0.8667、p95=313.14ms；因此保留 Hybrid 对照但不宣称延迟或生产收益。V0.4 Cross-Encoder 适配器已实现为默认关闭的实验开关；下一项施工任务是完成 Golden Draft 双人复核，再用同集验证 Reranker 是否值得承担额外成本。

工作台状态分为三层：`LIVE STATUS` 表示服务是否在线，`DATA FOUNDATION` 表示数据是否可信，`RAG EVOLUTION` 表示项目阶段。当前阶段回到 V0.0 Data Foundation：服务在线但质量快照尚未生成，后续 Dense/Hybrid/Intent 只在数据门可解释后比较。阶段状态只由可观察证据驱动，不由页面是否能生成一句回答驱动。

工作台还提供组件检查器和 `只运行检索 Trace`：即使 Chat LLM 很慢，也可以先运行 Embedding、官方/投诉检索和 RRF，查看每一步输入、输出、依赖和耗时。

当前 Chat 已切换到 LM Studio 本地 `deepseek-r1-distill-qwen-7b`；Qwen3-Embedding 仍作为 Embedding 模型。完整查询先显示检索 Trace，再进入 R1 生成；一次本地烟雾测试约 9.6 秒返回正文，但因回答没有带 `[S#]/[C#]` 引用，引用 Gate 保持失败，下一步需要修复引用遵从，而不是放宽校验。
