# Field State

## Purpose

- Purpose and target use: 边学边实现一套可进入简历、核心业务事实使用公开真实数据、可解释、可评测、具有企业生产约束的 RAG/Agent 系统。
- Current constraints: 当前附件仅有交接文本，无源码；用户明确不要虚构核心数据；跨境合规高风险结论必须人审。
- Observable outcome: 可运行仓库、真实数据、锁定评测集、可观测与安全门禁、完整证据包。

## Problem And Source State

- Initial-to-current problem-awareness delta: 用户确认实施 OpenSupport RAG V0.1，锁定中英跨语种检索、V0.3 后再实施 Agent、持续维护 Gemini 独立交接文件；现已从单投诉库升级为官方指导/法规与真实投诉分离的双证据 RAG。
- Active problem threads: 真实消费投诉与官方指导；V0.0 数据清洗/Hash/去重/隔离/血缘；Postgres/MinIO 真相源与 Qdrant 派生索引；Qwen3-Embedding/本地 DeepSeek-R1 Chat；Qdrant 双类型召回；Dense vs BM25+RRF；流式 Trace；引用校验/修复；客服 Benchmark；Benchmark 后的意图/Metadata、Reranker、Chunk 与 Context 升级顺序；回复安全边界；队列/缓存/OTel/Prometheus/Langfuse 生产 Profile；可替换数据包；本地部署与 Gemini 评审。
- Active source/evidence pointers and status: `outputs/消费者投诉开源RAG实施计划.md`、`outputs/gemini/GEMINI_HANDOFF.md`、`docs/07-data-foundation.md`、`infra/postgres/001_data_foundation.sql`；CFPB 六个官方来源解析为 109 个 Chunk；Qwen3-Embedding-0.6B 已本地下载；27 项单元/API/数据地基测试通过；Qwen Embedding + DeepSeek-R1 Chat + Qdrant 中文端到端查询已验证。
- Conflicts, gaps, and stale triggers: CFPB 网页可能触发反自动化限制，代码已加入来源失败报告、离线 CSV 摄取接口和公开镜像路径；最新镜像批次接受 200 条投诉、0 重复、0 隔离，累积 Qwen 主/Sparse 集合各 335 点（223 投诉 Chunk）；50-case Golden Draft 仍待双人复核；阿里云 Qwen Embedding fallback 已接入但需要用户 DashScope API key。

## Map And Active Use

- Map version and canonical map location: v6，`outputs/消费者投诉开源RAG实施计划.md`。
- Current node, task, or route: V0.0 Data Foundation、V0.2 原生 Sparse 和 V0.3 Intent/Metadata 已部署；V0.4 Cross-Encoder 适配器已接入但默认关闭；LM Studio `23145`、Qdrant `16333`、OpenSupport API `18000`、Docker core API `8000`、Postgres `15432`、MinIO `19000`、Redis `16379` 均可用；当前必须完成 50-case 双人复核，再决定是否启用 Reranker。
- Stable core: 模块化单体、真实数据、baseline-first、eval-first、权威来源与案例分离、provider abstraction、有限 Agent、人审。
- Active anchor, activation cues, use directions, and limits: CFPB 真实信用卡投诉 + 六个 CFPB 官方来源；官方来源支持一般流程、案例只支持相似经验；用于分流、案例检索、回复辅助与质检，不认定违法、不决定赔偿、不自动发送。
- Last stable artifact or performance: V0.0 数据地基、Postgres/MinIO 真相源、Qdrant 1.17 native Sparse、Data Quality 工作台、Compose Profiles、V0.3 Intent + Metadata、候选集扩大/来源 URL 多样性、50-case Golden Draft、P2/P3 answer Eval、fail-closed guardrail、Prometheus/OTel、V0.4 local Qwen3 Reranker adapter、V0.5 contextual parent-child index、V0.6 bounded corrective route 和 V0.7 optional Neo4j graph；50 项测试通过；Qwen3-Embedding 1024 维；2026-08-24 同一 335 点快照上 40 条可回答题 Dense Hit@3/MRR=0.900/0.8417、p95=59.80ms，native Hybrid=0.975/0.8667、p95=313.14ms；V0.4 8-case seed Hit@3=1.0、MRR=0.9375、p95=35168.92ms，未进入默认链路；V0.5 40-case draft Hit@3=0.975、MRR=0.8958、p95=108.28ms；V0.6 40-case draft Hit@3=0.975、MRR=0.8958、p95=110.09ms；V0.5 11-case Answer Eval 引用有效/覆盖/拒答正确率均为 1.0、危险声明 0、p95=33124.52ms；V0.7 Graph 已写入 223 Complaint、112 Source、802 structured relationships；Postgres 230 sources/335 versions/335 memberships，V0.5 Qdrant 432 contextual points，MinIO snapshot 已存在。
- Demonstrated mastery or observed failure: 尚未评估用户掌握；当前无可运行代码可验证。
- Feedback received: 用户要求非玩具、真实数据、分步实施并边做边学。

## Revision

- Latest revision delta: 完成 V0.0 真相源、V0.2 原生 Sparse、50-case Golden Draft、候选集/来源多样性、P2/P3 answer Eval、fail-closed guardrail、Prometheus metrics 和 OTel Collector。实际检索提升已被同集报告记录；生成层被客观 Eval 判定未通过，系统现在安全降级。
- Downstream items to recheck: 200 个唯一投诉扩展导入的网络/耗时；切换到 DeepSeek Chat 的延迟与正文稳定性；Qwen 本地与百炼 `qwen3.7-text-embedding` 的 Golden Set A/B 结果。
- Rollback point when relevant: 旧单投诉库实现可由历史版本恢复；v4 技术支持方案及更早版本保留为历史，不再作为当前首选。

## Continuation

- Blocker or open decision: V0.1 运行链路已不再阻塞；200 唯一投诉扩展仍受 CFPB 网络与本地 Embedding 耗时影响；公网 Qwen API 仍需要用户自行申请 Key。
- Next safe action: V0.7 结构化图演练已完成但没有 Support Intelligence Golden Set；下一步构造低相关/复合/全局问题切片，验证 V0.6 corrective 和 V0.7 graph 是否减少人工复核；V0.8/V0.9/V1 Agent 继续保持锁定。
- Resume prompt: “继续 OpenSupport RAG：真实镜像批次已接受 200 条投诉，Qdrant 主/Sparse 各 335 点，Manifest 335/335；V0.4 Qwen3 Reranker 已跑通但 MRR=0.9375、p95=35168.92ms，未进入默认；V0.5 contextual index 432 点，40-case draft Hit@3/MRR=0.975/0.8958、p95=108.28ms；V0.6 bounded corrective 40-case draft Hit@3/MRR=0.975/0.8958、p95=110.09ms。请先做低相关/复合问题切片，继续保持 Agent 锁定。”
