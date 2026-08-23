# V1 Controlled Agent 预验收

V1 的第一项能力已经实现为“信息补全 + 白名单检索 + 本地工单草稿”，但 API/页面仍由
`AGENT_ENABLED=false` 锁定。预验收脚本：

```powershell
.\.venv\Scripts\python.exe -m scripts.agent_eval
```

当前 6-case seed 结果：routing accuracy `1.0`、dangerous action count `0`。Trace 覆盖
missing fields、PII stop、out-of-domain stop、`search_guidance`、`search_complaints`、
`build_ticket_draft` 和 `human_approval_gate`。

这不是上线批准：仍需 V0.9 的稳定性、安全、数据版本和人工 Golden Review 全通过，之后才
可以在专门环境中把 `AGENT_ENABLED=true`，并完成真实人工审批遵从率评测。
