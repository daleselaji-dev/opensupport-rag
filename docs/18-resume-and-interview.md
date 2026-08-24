# 简历与面试叙事（只写已实测内容）

> 推荐定位：**生产导向的本地客服 RAG 工作台**，而不是“已经在线商用的客服系统”。
> 当前代码、数据、评测和运维链路已具备生产设计证据；正式发布仍需双人 Golden Review。

## 项目一句话

基于 CFPB 官方投诉 bulk 快照、官方指导和 Regulation Z 构建双语客服 RAG 工作台；以
PostgreSQL/MinIO 管理真相源、Qdrant 实现 Dense + native Sparse/BM25 + RRF，并按版本
比较 Intent/Metadata、Contextual/Parent-Child、Corrective Retrieval、Graph 和本地
Cross-Encoder，通过 Trace、确定性 Eval、安全门、缓存、Alias 回滚和 CI 验证生产约束。

## 可展示的实测证据

- 真实数据：官方 CFPB bulk ZIP 中 12,000 条新增公开叙述、12,223 个投诉 Chunk、12,335 个主 Dense/Sparse points；Manifest/Qdrant `12,335/12,335`，重复 0。
- 检索：V0.3 Hybrid 在 40 条可回答案例上 Hit@3=`0.975`、MRR=`0.8792`、p95=`142.82ms`；V0.5 Contextual Hit@3=`0.975`、MRR=`0.8958`、p95=`174.15ms`。
- 精排权衡：本地 Qwen3-Reranker 0.6B 在冻结 seed 上 k=20 MRR=`1.0`，但 p95=`9.91s`，相对 Hybrid 基线约 `81ms`，因此保留为实验组件而不进入默认链路。
- 回答与安全：完整 50-case Eval 的 citation validity、citation coverage、refusal correctness 均 `1.0`；forbidden claims=`0`、生成错误/超时=`0`、最新 p95约=`15.61s`（低于 20s 门）。
- 重要限制：40 条可回答问题中当前约 38 条使用 grounded fallback；这不是高风险拒答，而是本地 R1 引用覆盖不足后的安全降级。简历不应隐藏该指标，面试时应说明“安全正确，但生成体验仍有优化空间”。
- 生产硬化：Redis Embedding Cache、模型 timeout/Semaphore、429 限流、Celery 批次摄取、OpenTelemetry/Prometheus、蓝绿 Alias 回滚和 10 次 stability smoke（错误率 `0`）。
- 安全：12,335 points 扫描私有 PII=`0`、未隔离 Prompt Injection=`0`；2 条投诉注入文本被标记为不可信并 fail-closed。
- Graph/V1：Neo4j 12,223 Complaint、41,802 结构化关系；V1 Agent 6/6 preflight、routing accuracy=`1.0`、危险动作=`0`，默认 API 仍锁定。
- CI/发布：GitHub Actions clean runner 通过 pytest、compileall、benchmark audit 和 Compose config；唯一未通过的公开发布门是双人 Golden Review。

## 面试回答结构

1. 先说真实失败：Reranker 长候选触发 llama.cpp `ubatch` 500；R1 全角引用和低覆盖率导致人工复核飙升；高风险问题被模型当普通问答；完整 Eval p95 超过 20s。
2. 再说必要升级：batch/truncation、引用规范化与 grounded fallback、请求级风险门、关闭默认二次 Citation Repair。
3. 展示 Trace 前后变化：`rerank_candidates`、`repair_citations`、`request_safety_gate`、`guardrail_review`，以及同一冻结集的指标。
4. 说明为什么没有把每个前沿模块设为默认：Reranker 排名收益无法抵消延迟；Graph 只适合 Support Intelligence 全局问题；PDF 视觉数据仍未可复现。
5. 明确限制：Golden Draft 仍需双人 Citation Support；CFPB 网页部分 403；尚无真实线上客服业务 KPI，因此不能声称线上 ROI 或商用部署。

## 可直接放入中文简历的版本

**OpenSupport｜基于真实 CFPB 数据的生产导向双语客服 RAG（个人项目）**

- 针对客服场景中的脏数据、来源混淆、跨语言检索、引用幻觉和高风险承诺问题，构建从数据摄取到回答安全门的可观测 RAG 工作台；使用 FastAPI、PostgreSQL/MinIO、Qdrant、Redis/Celery、Neo4j、LM Studio 和 DeepSeek-R1。
- 从 CFPB 官方 bulk CSV ZIP 提取并保留 12,000 条真实公开投诉叙述，实施 Hash、去重、隔离、Manifest 和批次 checkpoint；最终形成 12,223 个投诉 Chunk、12,335 个 Dense/Sparse 索引点，并验证 Manifest/Qdrant `12,335/12,335` 一致。
- 在同一 40-case Golden Retrieval Set 上比较 Dense、Sparse/BM25+RRF、Intent/Metadata、Contextual/Parent-Child 和 Corrective Retrieval；V0.5 将 MRR 测得为 `0.8958`，检索 p95 `174.15ms`，所有版本保留可解释 Trace 和失败切片。
- 建立覆盖引用有效性、事实句覆盖率、拒答、安全声明、生成 timeout 和 p95 的 50-case Answer Eval：citation validity/coverage/refusal correctness 均 `1.0`，forbidden claims 与生成错误均 `0`，最新 p95约 `15.61s`。
- 通过本地 Qwen3 Reranker 消融、请求级风险门、间接 Prompt Injection 隔离、Redis 缓存、限流、蓝绿索引回滚、OpenTelemetry/Prometheus 和 CI Gate 展示生产权衡；V1 受控 Agent 仅允许检索和本地工单草稿，必须人工审批。

## 英文简历版本

**OpenSupport — Production-oriented bilingual customer-support RAG (Personal Project)**

- Built an inspectable, local-first RAG workbench for CFPB complaint support, addressing dirty data, source authority separation, cross-lingual retrieval, citation failures, prompt injection and unsafe outcome promises.
- Ingested 12,000 public-narrative complaints from the official CFPB bulk export with hashing, deduplication, quarantine, checkpointed batching and source lineage; produced 12,223 complaint chunks and 12,335 Dense/Sparse Qdrant points with a 12,335/12,335 manifest check.
- Evaluated Dense, native Sparse/BM25 + RRF, intent/metadata routing, contextual parent-child retrieval and bounded corrective retrieval on the same frozen set; V0.5 reached Hit@3 0.975, MRR 0.8958 and retrieval p95 174.15 ms.
- Built a 50-case answer/safety evaluation covering citation validity, citation coverage, refusal correctness, forbidden claims, model errors/timeouts and latency; measured 1.0/1.0/1.0, zero forbidden claims/errors, and approximately 15.61 s p95.
- Added local reranker ablations, request-level safety gates, indirect prompt-injection isolation, Redis/Celery, OpenTelemetry/Prometheus, blue-green alias rollback and a whitelisted human-approved V1 ticket-draft controller.

不要把 `release_check` 当前的 false 隐藏：它准确指出唯一未通过的公开发布门是独立人工 Golden Review。
