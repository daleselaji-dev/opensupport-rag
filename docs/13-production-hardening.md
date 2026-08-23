# 生产硬化增量

在 V0.4–V0.6 之后，先补会直接影响线上稳定性的横切能力：

- Redis Embedding Cache：缓存键包含模型 ID 和预处理后的输入 Hash；Trace 显示 `cache_hit`。
- 模型超时：Embedding/Chat 使用独立 timeout，避免一个本地模型卡住整个 API。
- 模型并发门：Embedding 和 Chat 共享有限 Semaphore，防止 RTX 3060 被并发请求压垮。
- API 限流：本地滑动窗口在 API 层返回 429；多副本部署时应替换为共享 Redis/Gateway 限流。
- Reranker batch：专用模型候选文本有 batch size 和字符上限，避免长 Chunk 触发 llama.cpp 500。
- Agent 锁定：`AGENT_ENABLED=false` 时 V1 API 返回 423，页面展示锁定原因，不提前执行外部动作。
- 蓝绿 Alias：`/api/index/activate` 只接受已登记的 Dense/Sparse 集合对，原集合不删除；`/api/index/rollback` 原子切回上一指针。
- 内容安全扫描：摄取阶段检测 PII/提示注入，生成前再次扫描证据；疑似注入文本不会直接进入 Prompt。
- 间接 Prompt Injection fail-closed：如果所有候选 Prompt 片段都被标记，系统停止生成并转人工，绝不把不可信原文重新塞回 Prompt。
- 完整回答 Eval：每条案例使用独立 timeout；单条 R1 卡住会记录失败并继续完整 Golden Set，不会让整轮评测无限等待。
- Citation Repair：保留为可选实验；生产默认使用确定性 grounded fallback，避免第二次本地 LLM 调用把 p95 推过 SLA。只有固定实验打开 `CITATION_REPAIR_ENABLED=true` 并通过同集对照时才启用。
- Celery 异步任务：`/api/index/build-contextual-async` 把 V0.5 重建移出 API 请求线程，`/api/tasks/{task_id}` 可查询状态。

这些能力不是“优化项”，而是把本地 Demo 变成可以观察、限流、超时和降级的服务边界。

已完成一次本地演练：V0.5 contextual Alias 激活后健康状态显示活动集合切换，再调用 rollback
恢复到 `opensupport_qwen_v01`；切换过程中没有删除任何 Qdrant 集合。
