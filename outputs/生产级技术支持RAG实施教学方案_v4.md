# 生产级技术支持 RAG 实施与教学方案 v4

更新日期：2026-08-23

## 1. 项目最终定义

> **Enterprise TechSupport RAG：基于 Apache Airflow 真实文档、故障 Issue、修复 PR 和版本记录的企业技术支持检索系统。**

第一阶段只做 RAG，不做 Agent：系统不自主执行命令、不修改用户环境、不自动关闭工单。它只负责检索、证据组织、回答、引用、置信边界和人工升级。

选择 Airflow 是因为它是实际生产中的数据工作流平台，公开数据又足以还原真实技术支持过程。系统架构以后可以复用到 Kubernetes、Docker、PostgreSQL 或企业自己的 SaaS 产品知识库。

## 2. 它解决什么实际问题

用户提交版本、部署方式、错误日志和问题描述，例如：

> Airflow 2.7.3 的 Scheduler 仍在运行，但 DAG 不再被调度，日志提示 DAG record locked，应当如何判断？

系统返回：

- 问题分类：已知缺陷、配置问题、版本不兼容、资源问题或证据不足；
- 最相关的官方文档和历史 Issue；
- 受影响版本与修复版本；
- 已验证 workaround 与适用条件；
- 引用到文档段落、Issue、PR 或 Release Note；
- 尚缺少哪些环境信息；
- 何时必须交给人工支持人员。

这对应企业的 L1/L2 技术支持、客户成功、数据平台运维和 SRE 知识检索工作。

## 3. 数据不需要编造

第一版只使用 Apache 官方公开数据：

1. Airflow 版本化官方文档；
2. Airflow Release Notes 和 Provider Changelog；
3. `apache/airflow` 真实 GitHub Issues；
4. Issue 评论、标签、时间线和关联 PR；
5. PR、Commit、测试和最终发布版本；
6. 必要时加入 Stack Exchange 公开问答，并遵守 CC BY-SA 署名要求。

真实 Issue 中已经包含用户提交的版本、部署方式、日志、配置和复现代码。我们不会编“客服工单”。

评测方式也使用真实记录：把已关闭 Issue 的初始描述作为测试问题，隐藏后续解决评论和关联 PR，检查 RAG 能否召回当时可用的正确文档、相似案例、修复版本和证据。

## 4. RAG 边界

属于当前项目：

- 数据采集和增量同步；
- 文档解析、清洗、去重和版本化；
- Chunking；
- BM25、Embedding、混合检索和 Reranking；
- Query Rewrite 与错误签名提取；
- 元数据过滤；
- 上下文组装；
- 带引用生成；
- 证据不足拒答；
- 离线评测、回归测试、监控和部署。

暂时不属于当前项目：

- 自主决定下一步工具；
- 自动运行诊断命令；
- 自动修改配置或升级依赖；
- 多 Agent 协作；
- 自动回复或关闭真实工单。

## 5. 生产级检索链路

```text
Airflow Docs / Issues / PRs / Releases
        ↓
采集、许可登记、清洗、去重、版本和时间元数据
        ↓
结构化 Chunk + Source Registry
        ↓
BM25 索引 + Dense Vector 索引
        ↓
查询解析：错误签名、组件、Airflow 版本、Provider、Executor
        ↓
多路召回 + 元数据过滤 + RRF 融合 + Cross-Encoder 重排
        ↓
证据充分性检查 + 上下文组装
        ↓
带逐条引用的回答 / 证据不足拒答 / 建议人工升级
```

关键点是错误日志中的精确字符串更适合 BM25，而“调度器活着但不工作”一类语义描述更适合 Dense Retrieval；生产系统必须同时支持两者。

## 6. 分阶段边做边学

### Sprint 0：数据可用性和真实闭环

实现：

- 通过 GitHub API 获取一批已关闭 Airflow Issue、评论、标签和关联 PR；
- 获取对应版本文档和 Release Notes；
- 建立 Source Registry，记录 URL、许可、来源类型、版本、发布时间、抓取时间和哈希；
- 筛选 100 个信息完整的真实案例，人工审计其中 20 个。

学习：数据血缘、许可、时间泄漏、业务标签和评测设计。

退出条件：展示至少 20 条“故障描述 → 证据 → 解决 PR → 发布版本”的可追溯链路。

### Sprint 1：最小可测 Baseline

实现：

- 解析官方文档和 Issue；
- 固定长度分块；
- Dense Retrieval；
- 最简单的带引用回答；
- 冻结首版开发集和测试集。

学习：Embedding、向量相似度、Top-k、Chunk、上下文和基础召回指标。

退出条件：系统可运行，Recall@k 和引用正确率可重复计算。

### Sprint 2：混合检索

实现：

- BM25；
- Dense + Sparse 多路召回；
- RRF 融合；
- 错误码和日志签名精确匹配；
- 文档类型、组件和版本过滤。

学习：关键词检索与语义检索的互补关系，以及为什么单向量检索在技术支持中会失败。

退出条件：在锁定测试集上显著优于 Sprint 1，并提供失败案例分析。

### Sprint 3：结构化分块与重排

实现：

- 按标题、代码块、Issue 字段和评论角色分块；
- Parent-child retrieval；
- Cross-Encoder reranker；
- 去重和相邻上下文扩展。

学习：召回率与精确率、Bi-encoder 与 Cross-encoder、上下文预算和延迟权衡。

退出条件：对比不同 Chunk 与 Rerank 策略的消融实验，而不是只展示一个最好结果。

### Sprint 4：版本感知与多源证据

实现：

- Issue—PR—Commit—Release 关系；
- Airflow、Provider、Python、Executor 等兼容性过滤；
- 知识截止时间；
- 来源冲突处理和旧版本降权。

学习：Temporal RAG、Metadata filtering、关系型检索和多源证据融合。

退出条件：回答能明确说明“在哪些版本受影响、哪个版本修复、依据是什么”。

### Sprint 5：可靠回答与评测

实现：

- Claim-level citation；
- 引用覆盖率和引用蕴含检查；
- 无答案问题、冲突问题、过时文档和提示注入测试；
- Groundedness、Answer Relevance 和人工错误分类；
- 回归门禁。

学习：为什么 RAG 质量必须拆成检索、证据和生成三层评估。

退出条件：坏答案能追溯到具体查询、Chunk、排序和提示步骤。

### Sprint 6：生产服务

实现：

- FastAPI；
- 后台增量摄取和幂等重建索引；
- PostgreSQL 保存来源、任务和评测数据；
- 向量/搜索引擎封装；
- 缓存、限流、超时、重试和降级；
- OpenTelemetry 日志与 Trace；
- Docker Compose；
- 延迟、成本、失败率和索引新鲜度 Dashboard。

学习：RAG 不是 Notebook，而是有数据生命周期和质量门禁的后端服务。

退出条件：一条命令启动，测试和评测自动运行，数据可增量更新，失败可观察和回滚。

## 7. 评测集设计

至少包含：

- 40 条已知缺陷；
- 20 条配置或部署问题；
- 15 条版本兼容问题；
- 10 条重复 Issue；
- 10 条证据不足、应拒答的问题；
- 5 条文档与旧 Issue 冲突的问题。

主要指标：

- Recall@5 / Recall@10；
- MRR、nDCG@10；
- 修复 PR 命中率；
- 正确修复版本命中率；
- Citation precision / coverage；
- 无答案识别率；
- p50 / p95 延迟；
- 单次查询成本；
- 索引新鲜度。

数据按时间切分。测试某个历史 Issue 时，索引中不得出现该 Issue 解决之后才发布的 PR 或 Release Note，防止未来信息泄漏。

## 8. 对求职真正有价值的证明

项目完成后，简历不写“用 LangChain 搭建聊天机器人”，而写可验证结果：

- 构建真实 Airflow 文档、Issue、PR 和版本记录的增量摄取与可追溯索引；
- 实现 BM25 + Dense + RRF + Cross-Encoder 的混合检索；
- 建立时间切分 Golden Set 和检索/引用回归门禁；
- 用消融实验说明 Chunk、过滤和 Rerank 对 Recall、nDCG、延迟和成本的影响；
- 实现版本感知、证据不足拒答、逐条引用和失败追踪；
- 部署为带监控、缓存、限流和可回滚索引的 FastAPI 服务。

当前 RAG 招聘信息反复要求的也是这些能力：端到端数据摄取、混合检索、重排、元数据过滤、来源引用、评测、Python/FastAPI、向量数据库和生产可观测性。

## 9. 个人长期用途

第一阶段帮你排查和学习 Airflow。完成后不改核心架构，只增加数据连接器即可扩展到：

- Docker / Kubernetes 故障知识；
- PostgreSQL 运维；
- 你未来公司的产品文档和支持工单；
- 你自己的技术笔记、项目错误记录和解决方案。

因此第一版不是只服务某一道面试题，而是一套可以长期维护的个人技术支持检索底座。

## 10. 当前推荐技术路线

- Python 3.11+
- FastAPI
- PostgreSQL
- Qdrant 或 OpenSearch（Sprint 0 后用小规模基准决定）
- Sentence Transformers / 可替换的 Embedding Provider
- Cross-Encoder Reranker
- Pytest
- Docker Compose
- OpenTelemetry
- Grafana / Prometheus

尽量先用清晰的 Python 接口实现检索流程，再引入 LangChain 或 LlamaIndex 适配层，避免框架遮住检索原理。

## 11. 主要公开来源

- Airflow 官方文档：https://airflow.apache.org/docs/apache-airflow/stable/
- Airflow Release Notes：https://airflow.apache.org/docs/apache-airflow/stable/release_notes.html
- Airflow Issues：https://github.com/apache/airflow/issues
- GitHub Issues REST API：https://docs.github.com/en/rest/issues
- Stack Exchange Data Explorer：https://data.stackexchange.com/help
