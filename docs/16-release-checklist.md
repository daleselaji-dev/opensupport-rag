# V1 交付前验收清单

## 必须有证据

- Data: 真实来源、版本 Hash、去重/隔离报告、Manifest 与 Qdrant 一致；
- Retrieval: Dense、Sparse、Hybrid、Contextual、Corrective 的同集报告和失败切片；
- Answer: 引用有效性、引用覆盖、人工 Citation Support、拒答和危险声明；
- Safety: PII、间接提示注入、退款承诺、违法判断、权限越界；
- Operations: p50/p95、缓存命中、限流/超时、队列、稳定性、蓝绿切换/回滚；
- Agent: 只有白名单工具、审批门、轨迹和危险动作拦截。

## 当前客观状态

`scripts/release_check.py` 当前仍会因为 `draft_pending_two_person_human_review` 返回非零；这是刻意的质量门，不是脚本错误。不能在没有两位独立复核者的情况下把 Golden Draft 改成 approved。

当前自动 Gate 实测：12,223 个唯一投诉 Chunk；Manifest/Qdrant `12,335/12,335`；V0.3
Hybrid Hit@3 `0.975`、MRR `0.8792`；V0.5 Contextual Hit@3 `0.975`、MRR `0.8958`；完整
50-case Answer Eval citation validity/coverage/refusal correctness 均为 `1.0`，危险声明和
生成错误/超时均为 `0`；10 次稳定性 smoke 错误率 `0`；私有 PII `0`、未隔离 Prompt Injection `0`。
这些数字仍不能替代人工 Citation Support。

端到端本地 p95 目标也已纳入 `release_check.py`：默认 Citation Repair 关闭、grounded
fallback 开启时最新完整 50-case p95=`14,542.61ms`，目标 `20,000ms`，通过。打开二次 LLM
Citation Repair 会使 p95 上升到 `23,038.79ms`，因此只保留为显式实验配置。

面试叙事必须按：

```text
真实失败 → 必要组件 → Trace/数据结构变化 → 同集指标 → 延迟/成本权衡 → 接受或撤回
```

不要把 Graph、Reranker、Agent 的存在本身当成生产能力；只有当它们解决了可复现问题并通过质量门，才写入简历的实测数字。
