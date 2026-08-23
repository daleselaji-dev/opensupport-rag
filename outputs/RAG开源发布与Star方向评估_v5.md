# RAG 开源发布与 Star 方向评估 v5

更新日期：2026-08-23

## 结论

如果同时追求真实业务、学习价值、可公开使用和 GitHub 传播，最合适的形态不是单独的金融投诉网站，而是：

> **OpenSupport RAG：可复用的开源客服 RAG Starter Kit，内置 CFPB 真实消费投诉参考应用和可视化检索评测。**

第一阶段仍然只做 RAG。消费投诉是证明系统真实有效的默认数据包；可替换的数据连接器、检索评测和可视化界面，使其他开发者能把它用于自己的产品文档、FAQ、历史工单或政策资料。

Star 无法通过设计保证。这里优化的是“陌生开发者五分钟内获得价值、理解差异并愿意保存仓库”的概率。

## 方向对比

| 方案 | 真实业务 | 普通用户价值 | 开发者复用 | 传播潜力 | 主要问题 |
|---|---|---|---|---|---|
| 仅做金融投诉客服网站 | 高 | 中 | 低 | 低至中 | 领域窄，外部开发者难代入 |
| 本地求职情报 RAG | 中高 | 很高 | 中 | 中 | 当前开源项目已较拥挤 |
| 通用 RAG Playground | 高 | 低 | 很高 | 中高 | Google 等已有类似项目，差异化困难 |
| **客服 RAG Starter Kit + 真实投诉包** | **高** | **高** | **高** | **相对最好** | 需要同时把 Demo 和框架控制在小范围 |

## 用户为什么会 Star

仓库首页必须让用户立即看到：

1. `docker compose up` 即可运行；
2. 无需自己准备数据即可使用 CFPB 真实投诉 Demo；
3. 粘贴一段投诉后，可看到相似案例、官方依据和逐条引用；
4. 可并排比较 Vector、BM25、Hybrid 和 Rerank 的结果；
5. 可查看每个答案到底由哪个 Chunk 支持；
6. 可运行内置 Golden Set，看到 Recall、MRR、nDCG、引用正确率、延迟和成本；
7. 可用一个简单配置替换成自己的客服数据。

别人 Star 的理由不是“作者做了一个作品集”，而是“这个仓库能帮我搭客服 RAG、调试检索或学习 RAG”。

## v0.1 产品范围

### 默认参考应用：消费投诉客服 RAG

- CFPB 真实信用卡投诉；
- CFPB 官方投诉流程和消费者指导；
- 投诉分类建议；
- 相似案例检索；
- 带引用的客服回复草稿；
- 回复覆盖与风险检查；
- 不认定违法、不决定赔偿、不自动发送。

### 开发者工作台

- 查询输入；
- 检索结果及分数；
- 关键词命中和语义命中解释；
- 不同检索方案并排比较；
- 最终送入模型的上下文；
- 答案与引用对应关系；
- 单条问题调试；
- 一键运行小型评测集。

### 可替换接口

- 文档加载器；
- Chunker；
- Embedding Provider；
- Sparse / Dense Retriever；
- Fusion；
- Reranker；
- Generator；
- Evaluator。

v0.1 只提供少量清晰接口，不追求支持所有框架、模型和数据库。

## 如何避免变成另一个普通 Playground

差异化来自四点组合：

- **真实垂直数据**：不是随便上传几个 PDF，而是带真实标签和业务流程的投诉数据；
- **检索透明**：能看见每一步为什么召回、为什么重排、为什么引用；
- **可验证**：内置真实 ID 绑定的 Golden Set 与基线结果；
- **可迁移**：用户可换成自己的 FAQ、客服记录和产品文档。

项目定位不是“零代码搭任意聊天机器人”，而是：

> 用一个真实客服场景，帮助开发者构建、理解、评测并发布可靠的 RAG。

## 分阶段发布

### v0.1：真实可运行

- 1,000–5,000 条 CFPB 投诉样本下载器；
- 官方指导文档摄取；
- Dense Baseline；
- 带引用回答；
- 20 条人工审计评测；
- 简单 Web UI；
- Docker Compose；
- 英文 README、截图和短演示视频。

### v0.2：证明技术深度

- BM25 + Dense + RRF；
- Metadata filter；
- Cross-Encoder reranker；
- 100 条 Golden Set；
- 检索对比和评测 Dashboard；
- 可复现实验报告。

### v0.3：让别人能复用

- CSV / JSON / Markdown 连接器；
- 数据包配置规范；
- 第二个公开数据包；
- API 文档；
- `good first issue`；
- 贡献指南和插件示例。

### v1.0：生产形态

- FastAPI；
- 增量和幂等索引；
- 缓存、限流、超时和降级；
- Trace、成本、延迟和索引新鲜度；
- 安全测试、Prompt Injection 与 PII 检查；
- 稳定配置格式和迁移说明。

### 后续 Agent 升级

RAG 质量稳定后，另行增加可选模块：追问缺失信息、创建工单、路由团队、SLA 提醒和人工批准后发送。Agent 不进入首版核心，也不能破坏纯 RAG 用户的简单部署。

## 开源增长不是最后一步

从 v0.1 就要包含：

- 清晰的英文项目名和一句话价值；
- 30–60 秒 GIF；
- 无 API Key 或本地模型的最小体验路径；
- 在线只读 Demo；
- 可复制的 Benchmark 表；
- Roadmap、Discussions、Issue templates；
- 3–5 个明确的 `good first issue`；
- 双周小版本，而不是等“大而全”后一次发布；
- 向 RAG、LLM、customer-support、local-first 等相关社区提交真实技术内容，而不是只发广告。

## 当前最大风险

- 通用 RAG 工具竞争激烈，必须坚持真实样例和可视化证据链；
- CFPB 数据不代表全部消费者经历，投诉叙述也未经官方核实；
- 不能把公司回复类别误当成完整解决方案；
- 框架范围容易膨胀，首版必须限制组件和数据量；
- Star 受发布渠道、文档、时机和持续维护影响，不能作为唯一成功指标。

更可靠的首版指标是：陌生用户完成首次运行的时间、成功完成的安装数、Demo 查询数、Issue/PR、重复访问、文档成功率和 Star 转化。

## 已核验的竞争与数据来源

- Google RAG Playground：https://github.com/GoogleCloudPlatform/rag-playground
- CFPB Consumer Complaint Database：https://www.consumerfinance.gov/data-research/consumer-complaints/
- CFPB Complaint API：https://cfpb.github.io/api/ccdb/api.html
- CFPB 企业投诉处理流程：https://www.consumerfinance.gov/compliance/consumer-complaint-program/company-process/
- Greenhouse Job Board API：https://developer.greenhouse.io/job-board.html
- Ashby Public Job Posting API：https://developers.ashbyhq.com/docs/public-job-posting-api
- Lever Postings API：https://github.com/lever/postings-api
