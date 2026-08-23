# V0.5：Contextual / Parent-Child RAG

## 为什么现在需要它

当前 Data Quality 报告已经暴露一条真实失败：至少一个投诉 Chunk 超过 20,000 字符。
长文档直接作为一个向量会造成两个问题：检索粒度过粗，且回答只看到孤立片段时难以保留
标题、产品、问题类型和来源身份。V0.5 针对这个失败切片，不是为了增加一个前沿名词。

Anthropic 的 Contextual Retrieval 原理是给 Chunk 补充其在文档中的上下文后再检索；本项目
先实现可复现的 deterministic contextual prefix（标题、source_type、权威等级和元数据），
并把长记录切成带 `parent_chunk_id` 的子 Chunk。后续可把 LLM 生成的 contextual prefix
作为 A/B 实验，不覆盖当前索引。[Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval)

## 施工

```powershell
Invoke-RestMethod -Method Post http://localhost:18000/api/index/build-contextual
```

它从现有 Qdrant Dense 派生读模型构建隔离集合：

- `opensupport_qwen_v05_contextual`
- `opensupport_qwen_v05_contextual_sparse`

当前 V0.3 索引不会被覆盖；重复运行使用稳定的 child ID 幂等写入。查询选择 V0.5 后，
Trace 增加 `contextual_backend` 和 `expand_parent`，并记录 chunk size、overlap、父文档数量
和子 Chunk 数量。

## 验收

- `text_too_long` 文档被拆分，父子血缘不丢失；
- 同一问题集上比较 V0.3 与 V0.5 的 Recall/MRR/nDCG、Citation Support、上下文长度和 p95；
- 任何上下文改善不能牺牲官方证据覆盖率；
- 删除 V0.5 派生集合后，仍能从当前 Dense/真相源重建；
- 没有长文档/支持度失败切片的收益时，不把 V0.5 设为默认。

## 首轮真实结果（2026-08-24）

在当前 335 点快照、40 条可回答 Golden Draft 上：

| 装配 | Hit@3 | MRR | p95 |
|---|---:|---:|---:|
| V0.3 Hybrid | 0.975 | 0.8667 | 313.14 ms |
| V0.5 Contextual Hybrid | 0.975 | 0.8958 | 108.28 ms |

这是同集的正向信号，尤其是 MRR 和 p95；但 Golden Draft 仍待双人复核，且 Citation Support
还没有人工真值，因此 V0.5 先保持可选装配，下一步再在 `text_too_long`、跨语言和引用切片
上做更细的对照。

V0.5 的 11-case Answer/Safety Eval 也通过自动门：引用有效性 `1.0`、事实句覆盖率 `1.0`、
拒答正确率 `1.0`、危险声明 `0`，生成 p95 `33124.52ms`。这只说明确定性安全回归没有退化，
不替代人工 Citation Support 标注，也不代表 V0.5 已经达到线上 SLA。
