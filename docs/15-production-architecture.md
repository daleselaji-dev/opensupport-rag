# OpenSupport 生产架构与版本边界

```text
                     ┌──────────────────────────────┐
                     │ Visitor / Support Operator   │
                     │ Swiss Workbench + Query UI   │
                     └───────────────┬──────────────┘
                                     │ HTTP / SSE / Trace
                     ┌───────────────▼──────────────┐
                     │ FastAPI policy + rate limit  │
                     │ Pydantic + guardrail gate    │
                     └──────┬──────────┬────────────┘
                            │          │
                 ┌──────────▼───┐  ┌──▼─────────────────┐
                 │ RAG Assembly │  │ Optional V1 Agent  │
                 │ V0.1 → V0.6  │  │ locked + approval   │
                 └──┬────┬───────┘  └────────────────────┘
                    │    │
        ┌───────────▼┐  ┌▼────────────────┐
        │ Qdrant     │  │ LM Studio       │
        │ Dense/Sparse│  │ Qwen Embed/R1  │
        │ aliases    │  │ local APIs      │
        └──────┬─────┘  └─────────────────┘
               │ derived read model
      ┌────────▼──────────────────────────────┐
      │ PostgreSQL + MinIO truth/source line  │
      │ versions, chunks, jobs, traces, drafts│
      └──────────────┬────────────────────────┘
                     │ async / cache / observability
          ┌──────────▼───────────┐  ┌─────────▼────────┐
          │ Redis + Celery       │  │ OTel + Prometheus │
          │ cache / queue / lock │  │ metrics / spans  │
          └──────────────────────┘  └──────────────────┘
```

版本不是工具清单，而是问题边界：

- V0.4：候选集排名问题；本地 Qwen3 Reranker 已运行，但因 MRR/延迟结果未晋级默认。
- V0.5：长 Chunk、上下文和父子血缘；隔离集合已构建并在同集有正向信号。
- V0.6：证据不足；最多一次查询变体和纠错检索，不能无限循环。
- V0.7：只给全局/多跳 Support Intelligence 使用的结构化 Graph；不改变普通客服主链路。
- V0.8：PDF 页面、表格和图表的多模态实验；需要单独页面级 Golden Set。
- V0.9：蓝绿索引、缓存、队列、限流、超时、监控、稳定性与 CI Gate。
- V1.0：受控客服 Agent，只有审批后才能保存本地工单草稿，禁止外部副作用。
