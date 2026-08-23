"""Project-stage state derived from observable runtime and evaluation facts."""

from __future__ import annotations

from typing import Any


def build_lifecycle(
    health: dict[str, Any],
    last_eval: dict[str, Any] | None,
    last_answer_eval: dict[str, Any] | None = None,
) -> dict[str, Any]:
    qdrant_ready = health.get("qdrant") == "ready"
    lm_ready = health.get("lm_studio") == "ready"
    indexed = int(health.get("indexed_documents") or 0)
    eval_ran = bool(last_eval and last_eval.get("version"))
    eval_passed = bool(last_eval and last_eval.get("overall_passed"))
    metrics = (last_eval or {}).get("metrics", {})
    answer_metrics = (last_answer_eval or {}).get("metrics", {})
    inventory = (last_eval or {}).get("index_inventory", {})
    quality = health.get("data_quality") or {}
    complaint_count = int(inventory.get("complaint_chunks") or 0)
    manifest_points = inventory.get("manifest_indexed_documents", "未生成")
    if manifest_points == "未生成" and quality:
        manifest_points = quality.get("indexed_documents", "未生成")
    qdrant_points = inventory.get("qdrant_points", indexed)
    accepted_documents = int(quality.get("accepted_documents") or 0)
    accepted_complaints = int((quality.get("source_types") or {}).get("complaint") or 0)
    duplicate_documents = int(quality.get("duplicate_documents") or 0)
    quarantined_documents = int(quality.get("quarantined_documents") or 0)
    data_ready = bool(quality)
    data_gate = data_ready and duplicate_documents == 0 and accepted_complaints >= 200
    reranker_state = (health.get("reranker") or {}).get("state", "disabled")
    contextual_ready = bool(health.get("contextual_ready"))
    graph_state = (health.get("graph") or {}).get("state", "locked")

    if qdrant_ready and lm_ready and indexed > 0:
        v01_status = "in_progress"
        v01_label = "已运行 · 验收未完成"
        v01_evidence = f"LM Studio/Qdrant 在线；Qdrant 有 {indexed} 个点"
    else:
        v01_status = "blocked"
        v01_label = "基础链路未就绪"
        v01_evidence = "需要先启动 LM Studio、Qdrant 并导入数据"

    if eval_passed:
        v02_status = "completed"
        v02_label = "Eval Gate 已通过"
    elif eval_ran:
        v02_status = "in_progress"
        v02_label = "当前施工 · Gate 未通过"
    else:
        v02_status = "next"
        v02_label = "下一阶段 · 尚未评测"

    if eval_ran:
        v03_status = "in_progress"
        v03_label = "当前施工 · Intent + Metadata"
    else:
        v03_status = "next"
        v03_label = "下一阶段 · 问题导向升级"

    if not data_ready or not data_gate or manifest_points != qdrant_points:
        current_stage = "v0.0"
        current_label = "V0.0 Data Foundation 数据地基"
    elif contextual_ready:
        current_stage = "v0.5"
        current_label = "V0.5 Contextual / Parent-Child"
    elif eval_ran:
        current_stage = "v0.3"
        current_label = "V0.3 Intent + Metadata 过滤"
    else:
        current_stage = "v0.1"
        current_label = "V0.1 可运行基础 RAG"

    return {
        "current_stage": current_stage,
        "current_label": current_label,
        "principle": "先完成数据地基，再用同一快照比较检索；只有质量门通过，才允许进入更复杂组件或 Agent。",
        "eval_standards": [
            {
                "id": "P0",
                "name": "数据与血缘",
                "status": "blocked" if not data_gate or manifest_points != qdrant_points else "passed",
                "status_label": "未通过" if not data_gate or manifest_points != qdrant_points else "通过",
                "actual": (f"{complaint_count} 条索引投诉；接受投诉 {accepted_complaints}；总接受 {accepted_documents}；重复 {duplicate_documents}；隔离 {quarantined_documents}；Manifest {manifest_points} vs Qdrant {qdrant_points}" if data_ready else f"尚未生成 Data Quality 报告；Manifest {manifest_points} vs Qdrant {qdrant_points}"),
                "target": "≥200 条唯一投诉；Manifest 与实际索引一致；重复数为 0；所有隔离项可解释",
                "enterprise_value": "企业首先要能复现数据版本，否则后面的分数不可信。",
            },
            {
                "id": "P1",
                "name": "检索质量",
                "status": "partial" if eval_ran else "not_started",
                "status_label": "Seed 已运行" if eval_ran else "尚未开始",
                "actual": (f"{metrics.get('case_count', '—')} 条：Hit@3 {metrics.get('hit_at_3')}；MRR {metrics.get('mrr')}；p95 {metrics.get('retrieval_p95_ms')}ms" if eval_ran else "没有固定评测结果"),
                "target": "≥50 条人工复核 Golden Set；按语言、主题、来源类型切片；记录 Recall/MRR/nDCG/延迟",
                "enterprise_value": "这是企业会认可的方向，但 8 条 seed 只能作为早期回归，不是上线证明。",
            },
            {
                "id": "P2",
                "name": "回答与引用",
                "status": "passed" if last_answer_eval and last_answer_eval.get("overall_passed") else ("partial" if last_answer_eval else "not_started"),
                "status_label": "自动 Gate 通过" if last_answer_eval and last_answer_eval.get("overall_passed") else ("已运行 · 仍需扩展" if last_answer_eval else "尚未完成"),
                "actual": (f"{last_answer_eval.get('case_count')} 条：引用有效 {answer_metrics.get('citation_validity')}；覆盖 {answer_metrics.get('citation_coverage')}；拒答 {answer_metrics.get('refusal_correctness')}" if last_answer_eval else "已有引用 ID 确定性校验；尚未完成回答完整性/引用精确率人工集"),
                "target": "引用存在性、引用支持度、答案完整性、无证据拒答；人工抽检与自动评测一致",
                "enterprise_value": "企业不能只看召回命中，还要证明答案没有超出证据。",
            },
            {
                "id": "P3",
                "name": "安全与边界",
                "status": "passed" if last_answer_eval and last_answer_eval.get("overall_passed") and answer_metrics.get("forbidden_claim_count") == 0 else ("partial" if last_answer_eval else "not_started"),
                "status_label": "自动安全回归通过" if last_answer_eval and last_answer_eval.get("overall_passed") and answer_metrics.get("forbidden_claim_count") == 0 else ("已运行 · 仍需扩展" if last_answer_eval else "尚未完成"),
                "actual": (f"危险声明 {answer_metrics.get('forbidden_claim_count')}；拒答正确率 {answer_metrics.get('refusal_correctness')}" if last_answer_eval else "Prompt guardrail 已存在；安全回归集尚未接入 Gate"),
                "target": "提示注入、PII、违法/退款诱导、冲突来源、无答案请求可重复拒答",
                "enterprise_value": "这是生产审批和合规评审的必需项，不是可选加分项。",
            },
            {
                "id": "P4",
                "name": "运营与业务结果",
                "status": "not_started",
                "status_label": "尚未开始",
                "actual": "已记录单次检索耗时；尚未记录错误率、成本、缓存、人工分流结果",
                "target": "p50/p95、超时率、成本/请求、数据新鲜度、人工升级准确率和线上反馈",
                "enterprise_value": "企业最终关心处理时间、升级准确率和风险，而不只是离线分数。",
            },
        ],
        "stages": [
            {
                "id": "v0.0",
                "name": "Data Foundation",
                "status": "completed" if data_gate and manifest_points == qdrant_points else ("in_progress" if data_ready else "next"),
                "status_label": "数据门已通过" if data_gate and manifest_points == qdrant_points else ("已运行 · 质量门未通过" if data_ready else "当前第一步"),
                "scope": "规范化 · Hash · 去重 · 隔离 · 数据血缘 · Manifest",
                "evidence": (f"接受 {accepted_documents}；重复 {duplicate_documents}；隔离 {quarantined_documents}；快照 {quality.get('snapshot_id')}" if data_ready else "尚未生成清洗和去重报告"),
                "gate": "≥200 条唯一投诉；重复 0；Manifest/Qdrant 一致；失败项可解释",
                "next_action": "先运行一次真实 CFPB 摄取，检查 Data Quality，再进入 Dense/Hybrid 对照",
            },
            {
                "id": "v0.1",
                "name": "可运行基础 RAG",
                "status": v01_status,
                "status_label": v01_label,
                "scope": "真实 CFPB 数据 · Qwen Embedding · Qdrant · 引用回答",
                "evidence": v01_evidence,
                "gate": f"投诉案例 {complaint_count}/200；Manifest {manifest_points} vs Qdrant {qdrant_points}",
                "next_action": "分批导入 200 条唯一投诉并重建 Manifest",
            },
            {
                "id": "v0.2",
                "name": "Eval 与检索升级",
                "status": v02_status,
                "status_label": v02_label,
                "scope": "Golden Set · Hit@3 · MRR · Dense/BM25/RRF 对照",
                "evidence": (f"{last_eval.get('retrieval_mode')}；Hit@3 {metrics.get('hit_at_3')}；MRR {metrics.get('mrr')}" if eval_ran else "尚未运行固定问题集"),
                "gate": "通过数据一致性、检索质量和延迟对照后，才接受新的检索组件",
                "next_action": "保留 Dense/Hybrid 对照，扩展到 50 条人工复核 Golden Set",
            },
            {
                "id": "v0.3",
                "name": "Intent + Metadata 过滤",
                "status": v03_status,
                "status_label": v03_label,
                "scope": "问题意图 · audience · source URL family · 过滤 Trace",
                "evidence": "8 条 seed：投诉流程 hard case 已按官方 URL family 分流" if eval_ran else "尚未运行 Intent/Metadata 对照",
                "gate": "不能牺牲召回率；必须改善意图切片和官方来源准确性",
                "next_action": "扩充意图/Metadata Golden Set，确认规则路由是否需要学习型 Router",
            },
            {
                "id": "v0.4",
                "name": "Reranked RAG",
                "status": "experimental" if reranker_state in {"ready", "not_loaded", "unavailable"} else "locked",
                "status_label": "可选实验开关" if reranker_state in {"ready", "not_loaded", "unavailable"} else "等待检索质量证据",
                "scope": "RRF 候选 · Cross-Encoder · 排名对照",
                "evidence": f"运行状态：{reranker_state}；必须先证明正确来源进了候选集但排名靠后",
                "gate": "MRR/nDCG 或 Citation Precision 改善；延迟增幅受控",
                "next_action": "继续 candidate-k/batch/truncation 消融；当前首轮 MRR 未改善且 p95 很高，暂不升为默认",
            },
            {
                "id": "v0.5",
                "name": "Contextual / Parent-Child",
                "status": "in_progress" if contextual_ready else "next",
                "status_label": "索引已构建 · 待同集评测" if contextual_ready else "下一项：先构建索引",
                "scope": "标题/来源继承 · 长 Chunk 拆分 · 父子血缘 · 上下文预算",
                "evidence": f"contextual_ready={contextual_ready}；contextual points={health.get('contextual_indexed_documents', 0)}",
                "gate": "长文档 Citation Support/上下文完整性改善；父子血缘可回溯；延迟受控",
                "next_action": "运行 POST /api/index/build-contextual，再对 text_too_long 和支持度切片做 V0.3/V0.5 对照",
            },
            {
                "id": "v0.6",
                "name": "Adaptive / Corrective RAG",
                "status": "locked",
                "status_label": "等待 V0.5 证据",
                "scope": "证据评分 · 有限重试 · Query Translation · 拒答",
                "evidence": "禁止无限循环；只在失败切片触发一次纠错检索",
                "gate": "Recall/Citation Support 提升，重试率和 p95 在预算内",
                "next_action": "V0.5 同集评测通过后，再实现一次受控纠错路由",
            },
            {
                "id": "v0.7",
                "name": "Graph-Augmented RAG",
                "status": "experimental" if graph_state == "ready" else "locked",
                "status_label": "图 profile 已运行 · 待 Golden Set" if graph_state == "ready" else "等待 Support Intelligence 切片",
                "scope": "实体关系 · 全局主题 · 多跳证据",
                "evidence": f"Neo4j 状态：{graph_state}；当前客服 Top-k 问题尚未证明需要图路由",
                "gate": "图关系必须能回溯原始来源；全局问题切片改善",
                "next_action": "先冻结全局主题 Golden Set，再决定 Neo4j/GraphRAG 路由",
            },
            {
                "id": "v0.8",
                "name": "Multimodal RAG",
                "status": "locked",
                "status_label": "等待 PDF/图表切片",
                "scope": "页面级检索 · 表格/图表 · OCR/视觉证据",
                "evidence": "当前数据主要为 HTML/JSON/文本投诉",
                "gate": "页面 Recall 和区域引用可复现",
                "next_action": "接入 CFPB PDF 报告并建立页面级问题集",
            },
            {
                "id": "v0.9",
                "name": "Production RAG Operations",
                "status": "locked",
                "status_label": "等待纯 RAG 质量门",
                "scope": "增量同步 · 缓存 · 队列 · Trace · 监控 · 蓝绿索引/回滚",
                "evidence": "Postgres/MinIO/Redis/OTel profile 已可运行，但还未完成故障演练",
                "gate": "更新不阻断查询；索引失败可回滚；稳定性/安全测试通过",
                "next_action": "V0.5–V0.8 证据齐全后施工生产运维门",
            },
            {
                "id": "v1.0",
                "name": "受控客服 Agent",
                "status": "locked",
                "status_label": "等待 Production RAG",
                "scope": "信息补全 · 检索规划 · 工单草稿 · 人工审批",
                "evidence": "Agent 不会因页面能回答就提前进入",
                "gate": "工具白名单；审批遵从 100%；危险动作 0",
                "next_action": "Production RAG 通过后再施工工具轨迹和 Agent Eval",
            },
        ],
    }
