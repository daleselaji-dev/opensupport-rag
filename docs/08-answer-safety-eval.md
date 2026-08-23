# P2/P3：引用有效不等于答案被证据支持

当前项目已经把回答 Eval 与检索 Eval 分开：

```text
检索 Eval：正确来源是否进入 Top-k、排名是否合理
回答 Eval：事实句是否有引用、引用是否存在、是否正确拒答、是否出现危险声明
```

## 当前真实结果

在 11 条 seed（8 条可回答、3 条拒答）上，DeepSeek-R1 曾出现：

- Citation ID validity：1.0；
- Citation coverage：0.318；
- Refusal correctness：0.3333；
- Forbidden claim count：1。

启用 fail-closed 后，同一 11 条 seed 的结果变为：

- Citation validity：0.0（可回答答案因未通过支持门而统一降级）；
- Citation coverage：0.125；
- Refusal correctness：1.0；
- Forbidden claim count：0。

这不是“分数变差”，而是系统停止把未经证据支持的模型正文交给客服。
下一轮要优化的是 Context/Prompt/生成校验，使可回答问题通过 P2，而不是降低
安全门阈值。

这说明模型可以引用一个真实的 `[S1]`，但仍然在没有证据支持的句子里加入
额外事实，或者把本应拒答的问题继续回答。

## 现在的 fail-closed 行为

如果满足任意条件，系统不会把模型原文当作客服回复返回：

- 引用 ID 不存在；
- 事实句引用覆盖率低于 `MIN_CITATION_COVERAGE=0.8`；
- 出现退款承诺、违法认定、账户调查结果、PII、系统提示泄露等危险声明。

系统会保留证据卡片和完整 Trace，并返回“请人工复核”的安全降级文本。

这是生产系统的质量门，不是为了让离线分数看起来更高。

即使数据、检索和 Answer/Refusal 自动门全部通过，项目仍不会自动发布：
`scripts/release_check.py` 还要求 50 条 Golden Set 的 `review_status` 为
`approved`，避免自动评估替代人工证据审查。
