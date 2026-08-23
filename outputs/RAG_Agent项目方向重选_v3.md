# 生产级 RAG / Agent 项目方向重选 v3

更新日期：2026-08-23

## 1. 结论修订

跨境商品合规审查是真实业务，但它更适合大型跨境平台、认证机构或高监管品类。对个人作品集而言，它存在三个问题：公开数据不能完整还原企业内部商品材料；单个卖家的使用频率可能不高；项目效果很难仅凭公开数据形成强闭环。因此，它保留为候选方向，不再作为首选。

当前首选调整为：

> **AirflowOps Copilot：面向企业数据平台的技术支持与生产故障分诊 Agent**

这是“智能客服”的企业软件版本：客户不是普通消费者，而是使用 Apache Airflow 的数据工程师、平台工程师、SRE 和技术支持人员；问题不是“订单在哪里”，而是“调度器为什么停止心跳、任务为什么卡住、升级后为什么失败、应该执行什么安全诊断”。

## 2. 候选方向对比

| 方向 | 企业价值 | 公开真实数据 | RAG 核心程度 | 可客观评测 | 首个作品集适合度 |
|---|---|---|---|---|---|
| 企业软件技术支持与故障分诊 | 很高 | 极好 | 很高 | 极好 | **首选** |
| 开源软件漏洞修复优先级 | 很高 | 极好 | 高 | 很好 | **第二选择** |
| 公开招投标机会情报 | 高 | 极好 | 高 | 中等 | 第三选择 |
| 上市公司公告与风险研究 | 高 | 极好 | 高 | 较好 | 可选 |
| 药物安全信号分流 | 很高 | 极好 | 中高 | 中等 | 不建议作为首个项目 |
| 跨境商品合规审查 | 中高但较窄 | 较好 | 高 | 中等 | 保留，不首选 |

判断标准不是“题材听起来重要”，而是：是否存在高频触发、明确使用者、可执行输出、可观察结果、可公开复现的数据链和可量化评测。

## 3. 首选项目：AirflowOps Copilot

### 3.1 真实企业工作流

使用者：

- 数据平台一线技术支持；
- 数据工程师；
- SRE / 平台工程师；
- 托管 Airflow 产品的客户成功与支持团队。

触发事件：

- 监控告警；
- 用户提交错误日志和环境信息；
- DAG 无法导入、任务卡住或调度器异常；
- Airflow 或 Provider 升级后出现回归；
- 用户需要判断是配置问题、已知缺陷、版本不兼容还是基础设施问题。

Agent 输出：

1. 对问题分诊：已知缺陷、配置错误、版本不兼容、资源/基础设施问题或证据不足；
2. 提取 Airflow、Python、Provider、Executor、数据库和部署方式等关键环境字段；
3. 检索与版本匹配的官方文档、历史 Issue、PR、Release Notes 和代码测试；
4. 给出带来源的诊断假设，并区分“已证实”和“待验证”；
5. 生成只读或低风险诊断命令；
6. 给出修复版本、临时 workaround 或升级建议；
7. 在可能产生停机、数据损坏或证据不足时升级人工处理。

### 3.2 全部核心数据都是真实公开数据

- Apache Airflow 官方版本化文档；
- 官方 Release Notes 和 Provider Changelog；
- `apache/airflow` GitHub 中真实 Issue、评论、标签、关联 PR、Commit 和关闭状态；
- Issue 中用户真实提交的错误日志、配置片段和复现代码；
- Stack Overflow / Stack Exchange 公共问答数据；
- Airflow 源代码、测试和公开安全公告。

我们不虚构工单。评测时直接使用历史已关闭 Issue：把 Issue 最初的问题描述当作输入，隐藏后续评论、关联 PR 和最终解决方案，让系统在当时可用的知识范围内进行诊断。

### 3.3 为什么它不是一个聊天玩具

它必须同时具备：

- 文档、Issue、PR、Release Notes、代码等异构数据摄取；
- Airflow 版本、Provider、Executor、组件、发布时间等元数据过滤；
- BM25 + 向量检索 + 重排；
- Issue—PR—Commit—Release 的关系检索；
- 引用到原始段落或具体 Issue / PR；
- 版本时态控制，避免用未来修复回答过去问题；
- 诊断工具沙箱，实际执行健康检查、配置检查或最小复现；
- 风险分级、拒答和人工升级；
- 离线评测、在线追踪、成本与延迟监控；
- API、队列、缓存、增量同步和可回滚索引。

### 3.4 可以客观验证的指标

- Issue 类型分类准确率；
- 正确组件和版本识别率；
- Recall@k、MRR、nDCG；
- 是否召回最终关联 PR / 修复版本；
- 引用正确率和引用覆盖率；
- 建议命令安全通过率；
- 证据不足时的正确升级率；
- 相比纯向量 Baseline 的提升；
- p95 延迟、单次成本、增量索引新鲜度。

测试集按时间切分，检索库不能包含测试 Issue 关闭之后才产生的内容，以防止答案泄漏。

## 4. 第二选择：开源漏洞修复优先级 Agent

真实输入可以由某个真实开源仓库的 Lockfile 或现场生成的 SBOM 提供，不需要虚构企业资产。系统将依赖项与 OSV、NVD、GitHub Advisory、CISA KEV 和 EPSS 关联，然后输出：

- 该仓库真正受哪些漏洞版本影响；
- 哪些漏洞已有在野利用证据；
- 应优先修复哪一个；
- 安全升级到哪个版本；
- 哪些是直接依赖或传递依赖；
- 是否存在升级冲突、替代缓解措施和待人工确认项。

这个方向业务价值非常强，但第一期会同时涉及包解析、版本区间、SBOM、漏洞可达性和安全知识，学习曲线比 Airflow 技术支持更陡。因此更适合作为第二个垂直项目，或者在 AirflowOps 后期作为安全模块加入。

## 5. 其他真实方向为何暂不首选

### 公开招投标情报 Agent

EU TED 提供真实招标、变更、截止日期和中标公告，数据开放且 Search API 无需认证。系统可以进行机会发现、条款抽取、变更监控和投标材料差距分析。问题是“是否值得投标”依赖企业内部能力、历史交付和成本数据；仅凭公开数据可以完成情报层，却无法完整验证最终商业决策。

### SEC 上市公司研究 Agent

SEC EDGAR 提供实时公开申报和 XBRL 数据，适合做财务研究、竞争情报和供应商风险助手。它很真实，但容易做成“研报摘要器”。要成为生产项目，必须加入跨期变化检测、数值核验、会计概念映射和证据审计。

### 药物安全信号 Agent

FDA 的公开不良事件数据确实服务于上市后安全监测，但公开报告不能证明因果关系，也不能直接计算发生率。它需要药物警戒和统计专业审核；如果没有相关职业目标，首个作品集容易在医学结论上失控。

## 6. 边做边学的实施路线

### Sprint 0：证明数据和任务真实

- 拉取一批 Airflow 已关闭 Issue、评论、标签、关联 PR 和 Release Notes；
- 建立来源许可、字段、版本、更新时间和可追溯 ID 登记；
- 筛出 100 个信息较完整的真实故障案例；
- 手工审计 20 个案例，确认可以从公开证据恢复处理路径。

退出条件：能展示一条“原始故障 → 证据 → 诊断 → 修复 PR / 版本”的完整真实链路。

### Sprint 1：可测的基础 RAG

- 文档和 Issue 解析；
- 基础分块、Embedding、向量检索；
- 带引用回答；
- 首版锁定评测集。

### Sprint 2：生产检索

- BM25 + 向量混合检索；
- Reranker；
- 版本、组件、Executor、Provider 过滤；
- 查询改写、检索失败分析和消融实验。

### Sprint 3：Case Graph 和时态

- 建立 Issue—PR—Commit—Release 关系；
- 支持“哪个版本修复”“是否为重复问题”；
- 严格处理知识截止时间，防止未来信息泄漏。

### Sprint 4：受控诊断 Agent

- 环境信息缺失时主动追问；
- 调用只读健康检查和配置检查工具；
- 在 Docker 沙箱运行最小复现；
- 对危险操作实施禁止、审批和审计。

### Sprint 5：评测与安全门禁

- 检索、答案、引用、工具、安全分别评测；
- 加入对抗提示、错误日志注入、过时文档和冲突来源测试；
- 建立失败分类和回归测试。

### Sprint 6：部署与作品集证据

- FastAPI、PostgreSQL/pgvector、后台同步任务、缓存和可观测性；
- Docker Compose 本地生产形态；
- Dashboard 展示质量、延迟、成本和升级人工比例；
- README、架构决策记录、真实案例演示和可重复评测报告。

## 7. 最终建议

如果目标是应聘通用 AI 应用、RAG、Agent 或企业软件工程岗位，选择 **AirflowOps Copilot**。

如果目标明确偏向安全工程、DevSecOps 或云安全，选择 **开源漏洞修复优先级 Agent**。

首个项目不要把两个方向混在一起。先把一个工作流做到有真实数据、真实工具执行、真实评测和生产运维，再复用平台能力扩展第二个垂直场景。

## 8. 官方数据与依据

- Airflow 安装与问题求助路径：https://airflow.apache.org/docs/apache-airflow/stable/installation/index.html
- Airflow Release Notes：https://airflow.apache.org/docs/apache-airflow/stable/release_notes.html
- Airflow GitHub Issues：https://github.com/apache/airflow/issues
- GitHub Issues REST API：https://docs.github.com/en/rest/issues
- Stack Exchange Data Explorer：https://data.stackexchange.com/help
- CISA KEV：https://www.cisa.gov/known-exploited-vulnerabilities-catalog
- NVD API：https://nvd.nist.gov/developers/vulnerabilities
- OSV API：https://google.github.io/osv.dev/api/
- FIRST EPSS API：https://api.first.org/epss/
- TED Search API：https://docs.ted.europa.eu/api/latest/search.html
- SEC EDGAR APIs：https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- FDA 上市后安全与公开数据说明：https://www.fda.gov/drugs/cder-conversations/understanding-cders-postmarket-safety-surveillance-programs-and-public-data
