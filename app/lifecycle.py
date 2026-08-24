"""Project-stage state derived from observable runtime and evaluation facts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.golden_review import review_status


ROOT = Path(__file__).resolve().parent.parent


def _read_report(name: str) -> dict[str, Any]:
    """Read local evidence without making the status endpoint fragile."""

    try:
        payload = json.loads((ROOT / "reports" / name).read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError, TypeError):
        return {}


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
    pdf_ready = bool(health.get("pdf_ready"))
    contextual_eval = _read_report("eval_latest_v0_5_hybrid.json")
    corrective_eval = _read_report("eval_latest_v0_6_hybrid.json")
    reranker_ablation = _read_report("reranker_ablation_latest.json")
    stability = _read_report("stability_latest.json")
    security = _read_report("security_audit_latest.json")
    agent_eval = _read_report("agent_eval_latest.json")
    release_check = _read_report("release_check_latest.json")
    golden_review = review_status()
    production_checks_pass = bool(release_check) and all(
        bool(item.get("passed"))
        for item in release_check.get("checks", [])
        if item.get("key") != "golden_review"
    )
    golden_review_pending = not bool(golden_review.get("approved"))

    if qdrant_ready and lm_ready and indexed > 0:
        v01_status = "completed" if data_gate and manifest_points == qdrant_points else "in_progress"
        v01_label = "数据与基础链路 Gate 已通过" if v01_status == "completed" else "已运行 · 验收未完成"
        v01_evidence = f"LM Studio/Qdrant 在线；Qdrant 有 {indexed} 个点；投诉 {complaint_count}/200；Manifest {manifest_points} vs Qdrant {qdrant_points}"
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
        v03_status = "completed"
        v03_label = "实现完成 · Golden Review 待复核"
    else:
        v03_status = "next"
        v03_label = "下一阶段 · 问题导向升级"

    if not data_ready or not data_gate or manifest_points != qdrant_points:
        current_stage = "v0.0"
        current_label = "V0.0 Data Foundation 数据地基"
    elif golden_review_pending and production_checks_pass:
        current_stage = "v0.9"
        current_label = "V0.9 已实现 · 等 Golden Review 发布门"
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
                "target": "V0.1 ≥200；V1 生产 ≥10,000 条唯一投诉；Manifest 与实际索引一致；重复数为 0；所有隔离项可解释",
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
                "status": "partial" if stability else "not_started",
                "status_label": "稳定性与运行指标已实测 · 业务结果待接入" if stability else "尚未开始",
                "actual": (f"稳定性 {stability.get('iterations', '—')} 次；错误率 {stability.get('error_rate', '—')}；p50 {((stability.get('latency_ms') or {}).get('p50', '—'))}ms；p95 {((stability.get('latency_ms') or {}).get('p95', '—'))}ms" if stability else "已记录单次检索耗时；尚未记录错误率、成本、缓存、人工分流结果"),
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
                "next_action": "保持同一快照运行 Dense/Hybrid/Rerank 对照，不重复导入已接受记录",
            },
            {
                "id": "v0.2",
                "name": "Eval 与检索升级",
                "status": v02_status,
                "status_label": v02_label,
                "scope": "Golden Set · Hit@3 · MRR · Dense/BM25/RRF 对照",
                "evidence": (f"{last_eval.get('retrieval_mode')}；Hit@3 {metrics.get('hit_at_3')}；MRR {metrics.get('mrr')}" if eval_ran else "尚未运行固定问题集"),
                "gate": "通过数据一致性、检索质量和延迟对照后，才接受新的检索组件",
                "next_action": "保留 Dense/Hybrid 对照；50 条 Golden Draft 已生成，等待双人独立复核",
            },
            {
                "id": "v0.3",
                "name": "Intent + Metadata 过滤",
                "status": v03_status,
                "status_label": v03_label,
                "scope": "问题意图 · audience · source URL family · 过滤 Trace",
                "evidence": "8 条 seed：投诉流程 hard case 已按官方 URL family 分流" if eval_ran else "尚未运行 Intent/Metadata 对照",
                "gate": "不能牺牲召回率；必须改善意图切片和官方来源准确性",
                "next_action": "完成两位 reviewer 的 50 条 Citation Support 复核，再决定是否进入发布 Gate",
            },
            {
                "id": "v0.4",
                "name": "Reranked RAG",
                "status": "experimental" if reranker_state in {"ready", "not_loaded", "unavailable"} else "locked",
                "status_label": "可选实验开关" if reranker_state in {"ready", "not_loaded", "unavailable"} else "等待检索质量证据",
                "scope": "RRF 候选 · Cross-Encoder · 排名对照",
                "evidence": (f"运行状态：{reranker_state}；消融结果 {[(item.get('config', {}).get('candidate_k'), item.get('mrr'), item.get('retrieval_p95_ms')) for item in reranker_ablation.get('results', [])]}；必须先证明正确来源进了候选集但排名靠后" if reranker_ablation else f"运行状态：{reranker_state}；必须先证明正确来源进了候选集但排名靠后"),
                "gate": "MRR/nDCG 或 Citation Precision 改善；延迟增幅受控",
                "next_action": "继续 candidate-k/batch/truncation 消融；当前首轮 MRR 未改善且 p95 很高，暂不升为默认",
            },
            {
                "id": "v0.5",
                "name": "Contextual / Parent-Child",
                "status": "completed" if contextual_eval.get("overall_passed") else ("in_progress" if contextual_ready else "next"),
                "status_label": "同集 Eval 已通过 · 待人工支持度复核" if contextual_eval.get("overall_passed") else ("索引已构建 · 待同集评测" if contextual_ready else "下一项：先构建索引"),
                "scope": "标题/来源继承 · 长 Chunk 拆分 · 父子血缘 · 上下文预算",
                "evidence": f"contextual_ready={contextual_ready}；contextual points={health.get('contextual_indexed_documents', 0)}；Hit@3={((contextual_eval.get('metrics') or {}).get('hit_at_3', '—'))}；MRR={((contextual_eval.get('metrics') or {}).get('mrr', '—'))}",
                "gate": "长文档 Citation Support/上下文完整性改善；父子血缘可回溯；延迟受控",
                "next_action": "补齐两位 reviewer 的 Citation Support 标注；没有人工支持度就不宣称生产质量",
            },
            {
                "id": "v0.6",
                "name": "Adaptive / Corrective RAG",
                "status": "completed" if corrective_eval.get("overall_passed") else "in_progress",
                "status_label": "同集 Eval 已完成 · 受控一次重试" if corrective_eval.get("overall_passed") else "实现完成 · 等同集 Eval",
                "scope": "证据评分 · 有限重试 · Query Translation · 拒答",
                "evidence": f"禁止无限循环；只触发一次纠错检索；Hit@3={((corrective_eval.get('metrics') or {}).get('hit_at_3', '—'))}；MRR={((corrective_eval.get('metrics') or {}).get('mrr', '—'))}",
                "gate": "Recall/Citation Support 提升，重试率和 p95 在预算内",
                "next_action": "保留 retry trace，比较无重试 / 一次重试的失败切片与延迟，不自动增加循环次数",
            },
            {
                "id": "v0.7",
                "name": "Graph-Augmented RAG",
                "status": "experimental" if graph_state == "ready" else "locked",
                "status_label": "图 profile 已运行 · 等全局问题 Golden Set" if graph_state == "ready" else "等待 Support Intelligence 切片",
                "scope": "实体关系 · 全局主题 · 多跳证据",
                "evidence": f"Neo4j 状态：{graph_state}；已建立结构化投诉关系；当前客服 Top-k 问题尚未证明需要图路由",
                "gate": "图关系必须能回溯原始来源；全局问题切片改善",
                "next_action": "冻结 Support Intelligence 全局主题 Golden Set，再比较 graph-only 与 hybrid；不把频率解释为责任",
            },
            {
                "id": "v0.8",
                "name": "Multimodal RAG",
                "status": "completed" if pdf_ready else "in_progress",
                "status_label": "页级文本基线已运行 · 视觉数据源仍为实验" if pdf_ready else "页级文本基线已实现 · 视觉数据源待接入",
                "scope": "页面级检索 · 表格/图表 · OCR/视觉证据",
                "evidence": (f"pypdf 页级索引已运行；PDF pages={health.get('pdf_indexed_documents', 0)}；视觉区域检索仍未进入默认链路" if pdf_ready else "pypdf 页级索引代码已实现；当前 PDF 数据源尚未就绪，尚未伪造视觉检索结果"),
                "gate": "页面 Recall 和区域引用可复现",
                "next_action": "建立页面级 Golden Set，再比较 Docling/MinerU/视觉检索；文本页基线不等于视觉 Recall",
            },
            {
                "id": "v0.9",
                "name": "Production RAG Operations",
                "status": "in_progress" if production_checks_pass else "locked",
                "status_label": "实现与运行演练已完成 · Golden Review 阻塞发布" if production_checks_pass and golden_review_pending else "等待纯 RAG 质量门",
                "scope": "增量同步 · 缓存 · 队列 · Trace · 监控 · 蓝绿索引/回滚",
                "evidence": f"Postgres/MinIO/Redis/OTel、缓存、限流、蓝绿索引和回滚已实现；稳定性错误率={stability.get('error_rate', '—')}；安全 findings={security.get('findings', '—')}（隔离注入={security.get('isolated_prompt_injection_findings', '—')}，未隔离={security.get('unisolated_prompt_injection_findings', '—')}，私有 PII={security.get('pii_findings', '—')}）",
                "gate": "更新不阻断查询；索引失败可回滚；稳定性/安全测试通过",
                "next_action": "完成 Golden Review 后再生成发布候选；保持 release_check 全部 Gate 可复现",
            },
            {
                "id": "v1.0",
                "name": "受控客服 Agent",
                "status": "in_progress" if agent_eval.get("routing_accuracy") == 1.0 and agent_eval.get("dangerous_action_count") == 0 else "locked",
                "status_label": "隔离预检通过 · 默认 API 保持锁定" if agent_eval.get("routing_accuracy") == 1.0 and agent_eval.get("dangerous_action_count") == 0 else "等待 Production RAG",
                "scope": "信息补全 · 检索规划 · 工单草稿 · 人工审批",
                "evidence": f"V1 preflight routing_accuracy={agent_eval.get('routing_accuracy', '—')}；dangerous_action_count={agent_eval.get('dangerous_action_count', '—')}；AGENT_ENABLED=false",
                "gate": "工具白名单；审批遵从 100%；危险动作 0",
                "next_action": "Golden Review 通过后，在独立 release 环境显式开启 AGENT_ENABLED，并复跑 Agent Eval；公共默认仍禁止外部动作",
            },
        ],
    }
