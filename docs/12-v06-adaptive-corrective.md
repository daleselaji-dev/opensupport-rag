# V0.6：Adaptive / Corrective RAG

## 问题导向

普通 Hybrid RAG 可能在低相关问题上仍然返回一堆“看起来相关”的官方页面；如果直接把
这些证据交给 LLM，系统要么编造答案，要么频繁人工复核。V0.6 将“证据不足”显式化：

```text
首次检索 → evidence grade → 一次领域术语变体 → 再检索 → 足够则回答，否则停止/拒答
```

它不是 Agent 循环：retry budget 固定为 1，不访问开放网页，不执行外部动作。

## Trace

- `adaptive_route`：记录基础装配和最大重试次数；
- `evidence_grade`：记录官方证据数量、底层 Dense/Sparse 分数、候选数和 reason codes；
- `query_translation`：记录原问题、术语变体策略和长度，不保存敏感原文；
- `corrective_retry`：记录重试候选数、首轮/最终 grade 和是否停止。

## 当前实现边界

V0.6 依赖已构建的 V0.5 contextual 索引，使用确定性领域术语映射（例如“陌生扣款”补充
`unauthorized credit card transaction dispute`）。它不是通用 LLM rewrite，也不声称能解决
所有复杂问题；只有在失败切片上测出 Recall/Citation Support 改善，才可继续升级。

首轮 40-case Golden Draft 检索结果：Hit@3 `0.975`、MRR `0.8958`、p95 `110.09ms`，与
V0.5 基线接近；这说明当前 Seed/Draft 大多数问题证据已经足够，纠错路由没有被无谓触发。
这是正确的结果：没有失败切片时，Adaptive 模块不应增加成本。后续要在低相关、复合问题
专门切片上验证它是否真的减少人工复核。
