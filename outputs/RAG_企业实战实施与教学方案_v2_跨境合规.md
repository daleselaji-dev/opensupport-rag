# 生产级 RAG/Agent 项目 v2：跨境商品合规审查 Copilot

更新日期：2026-08-23  
项目暂定名：**CrossBorder Compliance Copilot**

## 1. 最终落脚点

主场景不是“跨境法规问答”，而是：

> **中国商品进入欧盟市场前的商品上架合规审查与证据生成。**

第一版再收窄为：

- 商品：智能手机和平板电脑；
- 路径：中国 → 欧盟，首个落地国德国；
- 用户：跨境电商平台/品牌方的商品合规运营人员；
- 触发点：新商品上架或已有商品复审；
- 输出：适用规则、所需材料、缺口、真实召回/风险案例、关税与进口要求入口、证据引用、人工复核项；
- 决策边界：Agent 只能给出 `ready / blocked / needs_review` 建议，最终决定由合规人员确认。

这使项目从“问答系统”变成一个真正改变企业工作流的系统：它参与商品准入，而不是只回答知识问题。

## 2. 为什么不需要编造核心数据

### 真实产品数据：EPREL

European Product Registry for Energy Labelling 是欧盟委员会运营的产品注册数据库。公开系统可查询、筛选、比较和导出真实注册产品；截至 2026-07，官方称已有超过 200 万个注册产品。公开 API 面向程序化访问，在线商店也是官方列出的使用者。

用途：

- 真实品牌、型号、注册号和产品参数；
- 产品信息表、能源标签、上市时间、部分 GTIN 与供应商公开信息；
- 作为商品主数据和确定性 lookup 评测来源。

限制：

- API key 申请需要签署声明；没有 key 时可从公开网站检索/导出固定样本；
- 产品由供应商登记，注册本身不等于权威机构已经验证合规；这应成为系统的风险提示，而不能被 RAG 隐藏。

入口：

- https://energy-efficient-products.ec.europa.eu/eprel_en
- https://eprel.ec.europa.eu/screen/requestpublicapikey

### 真实风险与召回数据：Safety Gate

Safety Gate 是欧盟危险非食品产品快速预警系统。每条通报包含真实产品、风险描述和企业或主管机关采取的措施；页面支持按条件检索，并可导出 Excel/XML。

用途：

- 品牌/型号/品类相似风险检索；
- 召回和下架案例；
- `brand + model + risk + measure` 的确定性评测；
- 真实 hard negatives 和失败案例。

入口：https://ec.europa.eu/safety-gate/

### 真实法规、修订与生效时间：EUR-Lex / Cellar

EUR-Lex 提供欧盟法律及其元数据、合并版本、修订关系、多语言版本和稳定标识；Cellar 提供 REST、SPARQL、RSS/Atom 等机器访问方式。

第一批法规候选：

- General Product Safety Regulation：Regulation (EU) 2023/988；
- Batteries Regulation：Regulation (EU) 2023/1542；
- Radio Equipment Directive：Directive 2014/53/EU；
- RoHS：Directive 2011/65/EU；
- WEEE：Directive 2012/19/EU；
- 与智能手机/平板电脑能源标签和生态设计有关的具体法规及官方指南。

入口：

- https://eur-lex.europa.eu/
- https://op.europa.eu/en/web/cellar
- https://eur-lex.europa.eu/content/help/data-reuse/webservice.html

### 真实关税、原产地与进口要求：Access2Markets

欧盟委员会明确列出的信息包括关税、原产地规则、税费、进口手续、产品要求和贸易统计。

用途：

- 根据商品分类、原产地和目的地查询市场准入信息；
- 将“法规检索”与“真实跨境交易条件”连接；
- 作为工具调用，而不是把动态税率长期写进向量库。

入口：https://trade.ec.europa.eu/access-to-markets/

## 3. 真实企业流程

```text
新商品/型号进入待上架队列
        ↓
读取 EPREL 真实产品记录或产品信息表
        ↓
根据产品类别、无线能力、电池、目标市场、日期确定检索范围
        ↓
检索 EUR-Lex 法规、合并版本、官方指南
        ↓
查询 Safety Gate 是否有同型号或相似风险通报
        ↓
调用 Access2Markets 获取进口/关税/原产地入口信息
        ↓
规则引擎检查确定性字段，RAG 组装证据
        ↓
生成 ready / blocked / needs_review 审查报告
        ↓
合规人员审批、退回补材料或升级专家
```

一个可演示的真实任务：

> “检查 EPREL 注册号 X 对应的智能手机是否适合在德国上架。列出与产品安全、无线设备、电池、RoHS、WEEE 和标签相关的适用证据；检查 Safety Gate 中是否存在同型号或相似风险；指出缺失信息，并明确哪些判断必须由人工完成。”

## 4. 与客服的关系

客服不是第一落脚点，而是第二个受益工作流。

### 主要产品：上架合规审查 Agent

业务价值最清楚：减少人工找法规和案例的时间、避免遗漏、保留审计证据、阻止高风险商品未经复核上架。

### 第二模块：合规客服 Agent Assist

当消费者询问召回、产品安全、退货或保修时：

1. 读取真实商品型号；
2. 查询 Safety Gate；
3. 检索欧盟消费者权利与公司的已批准政策；
4. 生成带引用的客服回复草稿；
5. 涉及安全、召回或法律争议时必须升级人工。

第一版不让模型直接面向消费者自动回复。这样既能展示客服应用，又不会把项目降级成普通 FAQ bot。

## 5. RAG 和 Agent 各自负责什么

| 能力 | 正确实现 |
|---|---|
| 法规/指南检索 | 结构化、版本感知 RAG |
| 相似危险产品 | hybrid retrieval + metadata filtering + reranker |
| 精确产品参数 | EPREL API/结构化数据库 lookup，不让 LLM 猜 |
| 税率和进口条件 | Access2Markets 工具实时查询，不将旧数值当静态知识 |
| “是否缺材料” | 确定性规则/decision table |
| 多源任务编排 | 有限状态机 Agent |
| 最终结论 | 证据聚合 + verifier + 人工审批 |

关键原则：**RAG 负责找证据，规则负责确定性检查，Agent 负责编排，人工负责高风险判断。**

## 6. 不编数据的评测集

评测问题可以人工编写，但答案和证据必须绑定真实记录：

- `law_retrieval`：问题 → EUR-Lex CELEX/ELI + article/annex；
- `temporal_law`：指定日期 → 当时有效的合并版本；
- `product_lookup`：EPREL registration number → 真实字段；
- `recall_match`：品牌/型号/品类 → Safety Gate 通报编号、风险和措施；
- `cross_source_case`：真实 EPREL 产品 + 真实法规 + 真实 Safety Gate 通报；
- `abstention`：公开数据缺少的信息必须输出 unknown/needs_review；
- `citation`：每个重要 claim 必须引用可打开的真实页面或稳定 ID。

人工标注不是“编数据”。它是对真实记录建立 gold relevance 和适用性判断。项目必须保存标注人、依据、时间和复核状态。

## 7. 第一阶段数据切片

不先抓全欧盟：

1. 从 EPREL 选取 100–500 个真实智能手机/平板型号；
2. 导出 Safety Gate 中相关电子产品通报；
3. 从 EUR-Lex 获取 5–10 部核心法规及合并版本、article/annex 结构；
4. 保存 Access2Markets 查询参数和响应快照/证据入口；
5. 建立 50 个 law retrieval、50 个 product lookup、50 个 recall match、20 个跨源任务；
6. 先跑 lexical baseline，再做 dense、hybrid、reranker 和 Agent。

## 8. 作品集最终展示

五分钟 Demo：

1. 输入一个真实 EPREL 产品注册号和目标市场；
2. Agent 展开有限步骤和工具调用；
3. 返回法规版本、条款、产品参数和 Safety Gate 风险证据；
4. 明确 missing evidence 和 needs_review；
5. 合规人员批准或退回；
6. 展示 trace、评测结果、延迟、成本和一次失败案例。

简历项目的准确定位：

> 构建基于 EUR-Lex、EPREL、Safety Gate 与 Access2Markets 公开真实数据的跨境商品合规审查 Agent，将版本感知法规 RAG、产品主数据查询、危险品通报检索、确定性规则和人工审批整合为可审计工作流。

## 9. 仍然不能声称的内容

- 不能声称系统给出法律意见；
- 不能把 EPREL 注册等同于已验证合规；
- 不能声称覆盖全部欧盟国家和商品品类；
- 不能把 Access2Markets 当前结果永久缓存后继续当实时事实；
- 不能在没有合规专家复核时把“适用法规映射”包装成法律 ground truth；
- 不能因所有核心数据公开，就省略鉴权、审计、回滚和数据版本。

## 10. 下一步实施

Sprint 0 只做一件事：验证四个真实数据源能否组成一条可重复的数据链。

交付物：

- `source_registry`；
- 100 个 EPREL 产品 manifest；
- Safety Gate 导出样本；
- EUR-Lex/Cellar 法规抓取与版本 manifest；
- 20 个真实跨源问题；
- 数据获取、许可、限制和更新策略报告。

通过条件：每个问题都能追溯到真实产品 ID、法规 ID 或通报 ID；没有核心业务事实依赖生成数据。

## 11. 主要官方依据

- EPREL：https://energy-efficient-products.ec.europa.eu/eprel_en
- EPREL Public API：https://eprel.ec.europa.eu/screen/requestpublicapikey
- Safety Gate：https://ec.europa.eu/safety-gate/
- EUR-Lex Webservice：https://eur-lex.europa.eu/content/help/data-reuse/webservice.html
- Cellar data：https://op.europa.eu/en/web/cellar/cellar-data
- Access2Markets：https://policy.trade.ec.europa.eu/help-exporters-and-importers/importing-eu_en
- CE marking：https://europa.eu/youreurope/business/product-rules-compliance/general-product-compliance/ce-marking/index_en.htm
- EU consumer guarantees/returns：https://europa.eu/youreurope/business/selling-in-eu/consumer-contracts-guarantees/consumer-guarantees/index_en.htm
