# V0.7：Graph-Augmented RAG（可选 Support Intelligence）

V0.7 不替代客服的普通 Top-k RAG。它只服务于“哪些问题最常见”“某产品关联哪些 Issue”
等全局/聚合问题。图中的关系全部来自 CFPB 已有结构化字段：Complaint、Product、Issue、
Company、Response 和 Source；LLM 不得创造关系。

启动可选 profile：

```powershell
docker compose --profile graph up -d neo4j
$env:GRAPH_ENABLED = "true"
Invoke-RestMethod -Method Post http://localhost:18000/api/index/build-graph
Invoke-RestMethod 'http://localhost:18000/api/graph/query?kind=top_issues&limit=10'
.\.venv\Scripts\python.exe scripts\graph_eval.py
```

当前默认环境保持 `GRAPH_ENABLED=false`。没有 Neo4j 或没有 Support Intelligence Golden Set 时，
GraphRAG 不进入客服主链路；投诉数量也不等于违法或责任结论。

本机 V0.7 演练已完成：12,335 条源记录写入 12,223 个 Complaint 节点、112 个官方 Source 节点和
41,802 条结构化关系；`top_issues`/`top_products` 查询成功返回聚合结果。由于当前还没有冻结的
Support Intelligence Golden Set，图模块仍不替换客服默认检索。

`scripts/graph_eval.py` 会把 profile readiness、top issues/products 非空性、计数合法性和
延迟写入 `reports/graph_eval_latest.json`。这是结构化 smoke evidence，不是图谱质量的最终
Golden Set，也不把投诉频率解释为违法或责任。
