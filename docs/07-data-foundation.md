# V0.0 Data Foundation：先解决脏数据，再谈检索分数

RAG 的第一个生产问题通常不是模型，而是数据。OpenSupport 现在把一条
来源记录经过以下状态后才允许进入 Qdrant：

```text
discovered → downloaded → validated → parsed → normalized
→ deduplicated → chunked → enriched → embedded → indexed → active
```

任意一步失败都要进入 `quarantined`、`retryable_failed` 或
`permanent_failed`，不能静默丢弃。

## 本轮已经施工的内容

- 规范化空白、控制字符、标题和来源 URL；
- 计算内容 Hash 和规范化文本 Hash；
- 为每个 Chunk 写入语言、规范 URL、Pipeline 版本和生命周期状态；
- 检查缺失 URL、过短文本、缺失 complaint ID；
- 对官方页面按 URL+文本去重；
- 对投诉按 complaint ID 保留来源身份，即使叙述文本相同；
- 生成 `data/data_quality_latest.json`；
- 工作台展示每个生命周期阶段的数量、重复、隔离和快照 ID。
- CFPB JSON API 返回 403 时，下载器会尝试官方过滤 CSV 导出；CSV 当前不提供 complaint ID，系统使用稳定行 Hash 并在 `identity_source` 标明降级身份。
- JSON 和 CSV 都被 WAF 拒绝时，系统返回不暴露堆栈的可操作错误，并保存 `data/ingest_failure_latest.json`。
- 如果浏览器可以下载官方 CSV，可将文件保存为 `data/raw/complaints.csv`，调用 `POST /api/ingest-local`；它会按产品和年份过滤，并复用同一套质量、索引和 Manifest 契约。
- 为了在 CFPB WAF 403 期间保持可复现，项目也支持 `source_kind=cfpb_mirror`，读取带真实 complaint_id 的公开 CFPB 派生镜像；报告会保存镜像 URL/文件 Hash 和 `identity_source=cfpb_mirror_huggingface`，不会把它标记为 CFPB 实时 API。

## 你要观察的真实问题

1. 两个不同来源页面拥有同样正文：内容去重应该生效，但来源身份仍要保留。
2. 投诉文本为空：不能进入 Embedding，否则会产生无意义向量。
3. 同一个投诉重复出现在两次 API 分页：complaint ID 去重必须生效。
4. 官方页面 URL 有 fragment：fragment 不应导致同一页面生成两套身份。
5. 解析失败的 PDF：进入隔离区，并在工作台显示失败原因。

## 当前真实阻塞

本机最近一次真实 20 条导入同时遇到 CFPB JSON 与 CSV endpoint 的 `403
Forbidden`。这不是 RAG 或 Embedding 质量失败，而是外部数据源接入失败。工作台
会显示最近一次数据源错误；下一步可以稍后重试，或从 CFPB 官方 Consumer
Complaint Database 下载 CSV 后调用 `/api/ingest-local`。

## 生产真相源与派生索引

PostgreSQL/MinIO 保存原始数据和生命周期；Qdrant 只是派生读模型。删除
Qdrant 后，系统应能根据文档版本、Chunk 配置和 Embedding 模型重新生成
索引。当前代码已经加入 PostgreSQL 初始化 Schema 和 Docker Profile，JSON
质量报告用于本地第一阶段观察，下一步将接入真实存储适配器。
