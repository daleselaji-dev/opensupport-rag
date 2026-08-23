"""Bounded V1 complaint-intake Agent.

This is intentionally a small, inspectable controller rather than an
autonomous chat loop.  It can ask for missing intake fields, call the existing
read-only retrieval path, and prepare a local ticket draft.  It cannot send a
message, write an external CRM, decide a refund, or make a legal finding.
"""

from __future__ import annotations

import re
import time
from hashlib import sha256
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.routing import classify_intent
from app.schemas import AgentDraft, AgentRequest, AgentResponse, TraceEvent

ALLOWED_TOOLS = ["search_complaints", "search_guidance", "build_ticket_draft"]
_PII_PATTERNS = {
    "payment_card_number": re.compile(r"(?<!\d)\d{12,19}(?!\d)"),
    "email": re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b"),
    "ssn": re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
}


def detect_sensitive_input(text: str) -> list[str]:
    return [name for name, pattern in _PII_PATTERNS.items() if pattern.search(text)]


def _event(trace: list[TraceEvent], name: str, summary: str, details: dict[str, Any], status: str = "completed") -> None:
    trace.append(
        TraceEvent(
            step=len(trace) + 1,
            name=name,
            status=status,  # type: ignore[arg-type]
            duration_ms=0.0,
            summary=summary,
            details=details,
        )
    )


def _infer_fields(request: AgentRequest, route: Any) -> dict[str, Any]:
    message = request.message.lower()
    product = request.product
    if not product and ("信用卡" in message or "credit card" in message or "card" in message):
        product = "credit_card"
    issue = request.issue
    issue_map = {
        "unauthorized_transaction": "unauthorized_transaction",
        "billing_error": "billing_error",
        "consumer_submit_complaint": "complaint_submission",
        "company_response": "complaint_response",
    }
    issue = issue or issue_map.get(route.intent)
    transaction_context = bool(
        request.transaction_date
        or request.amount
        or request.merchant
        or any(term in message for term in ("交易", "扣款", "账单", "transaction", "charge", "statement"))
    )
    prior_actions = request.previous_actions or (
        request.message if any(term in message for term in ("联系", "致电", "客服", "dispute", "contact", "called", "issuer")) else None
    )
    return {
        "product": product,
        "issue": issue,
        "transaction_date": request.transaction_date,
        "amount": request.amount,
        "merchant": request.merchant,
        "transaction_context_present": transaction_context,
        "previous_actions": prior_actions,
        "requested_outcome": request.requested_outcome,
        "intent_confidence": route.confidence,
    }


def _missing_fields(fields: dict[str, Any], route: Any) -> list[str]:
    if route.audience == "out_of_domain":
        return []
    missing: list[str] = []
    if not fields.get("product"):
        missing.append("product")
    if not fields.get("issue"):
        missing.append("issue")
    if route.intent in {"unauthorized_transaction", "billing_error"} and not fields.get("transaction_context_present"):
        missing.append("transaction_context")
    if route.intent in {"unauthorized_transaction", "billing_error"} and not fields.get("previous_actions"):
        missing.append("previous_actions")
    return missing


def _questions(missing: list[str]) -> list[str]:
    questions = {
        "product": "涉及哪一种产品或账户类型？请不要提供卡号、身份证号或完整账户号码。",
        "issue": "你希望客服处理的主要问题是什么，例如陌生交易、账单错误或投诉进度？",
        "transaction_context": "请提供不含敏感号码的交易背景，例如大致日期、金额区间或商户名称。",
        "previous_actions": "你此前是否联系过发卡机构或商户？对方给了什么处理状态？",
    }
    return [questions[item] for item in missing if item in questions]


class ComplaintAgent:
    def __init__(self, rag: Any):
        self.rag = rag

    async def run(self, request: AgentRequest, trace_id: str) -> AgentResponse:
        trace: list[TraceEvent] = []
        started = time.perf_counter()
        _event(trace, "agent_received", "收到投诉补全请求", {"message_chars": len(request.message), "trace_id": trace_id})
        sensitive = detect_sensitive_input(request.message)
        if sensitive:
            _event(
                trace,
                "agent_safety_check",
                "检测到可能的敏感信息，停止存储和工具调用",
                {"flags": sensitive, "stored_raw_message": False},
                "failed",
            )
            _event(trace, "agent_stop", "安全门阻止继续处理", {"reason": "pii_detected"}, "failed")
            return AgentResponse(
                trace_id=trace_id,
                status="blocked_safety",
                safety_flags=sensitive,
                allowed_tools=ALLOWED_TOOLS,
                follow_up_questions=["请删除卡号、邮箱、身份证号等敏感信息后重新提交。"],
                trace=trace,
            )

        route = classify_intent(request.message)
        _event(
            trace,
            "agent_route_intent",
            f"路由到 {route.intent}，置信度 {route.confidence:.2f}",
            {"intent": route.intent, "confidence": route.confidence, "audience": route.audience},
        )
        support_context = any(term in request.message.lower() for term in ("support", "customer", "credit card", "charge", "transaction", "complaint", "客服", "投诉", "信用卡", "扣款"))
        if route.audience == "out_of_domain" or (route.audience == "unknown" and not support_context):
            _event(trace, "agent_stop", "问题不在客服投诉范围内，转人工判断", {"reason": "out_of_domain"}, "failed")
            return AgentResponse(
                trace_id=trace_id,
                status="out_of_domain",
                allowed_tools=ALLOWED_TOOLS,
                follow_up_questions=["请改为描述消费投诉、账单争议或投诉处理流程。"],
                trace=trace,
            )

        fields = _infer_fields(request, route)
        missing = _missing_fields(fields, route)
        _event(trace, "agent_missing_fields", "检查投诉工单必填字段", {"missing_fields": missing, "inferred_fields": fields})
        if missing:
            _event(trace, "agent_stop", "信息不足，先追问而不调用外部动作", {"reason": "missing_required_fields"}, "pending")
            return AgentResponse(
                trace_id=trace_id,
                status="needs_information",
                missing_fields=missing,
                follow_up_questions=_questions(missing),
                allowed_tools=ALLOWED_TOOLS,
                trace=trace,
            )

        retrieval_trace: list[TraceEvent] = []
        hits = await self.rag.retrieve(
            request.message,
            top_k=3,
            trace=retrieval_trace,
            retrieval_mode="hybrid",
            assembly_version="v0_3",
        )
        guidance = [hit for hit in hits if hit.source_type in {"guidance", "regulation"}]
        complaints = [hit for hit in hits if hit.source_type == "complaint"]
        _event(
            trace,
            "tool_search_guidance",
            f"search_guidance 返回 {len(guidance)} 条官方证据",
            {"tool": "search_guidance", "citations": [hit.citation for hit in guidance], "nested_trace": [item.name for item in retrieval_trace]},
        )
        _event(
            trace,
            "tool_search_complaints",
            f"search_complaints 返回 {len(complaints)} 条案例证据",
            {"tool": "search_complaints", "citations": [hit.citation for hit in complaints], "nested_trace": [item.name for item in retrieval_trace]},
        )
        draft = AgentDraft(
            draft_id=str(uuid4()),
            status="pending_approval",
            fields={**fields, "input_fingerprint": sha256(request.message.encode("utf-8")).hexdigest()[:16]},
            evidence=[
                {
                    "citation": hit.citation,
                    "source_type": hit.source_type,
                    "title": hit.title,
                    "source_url": hit.source_url,
                    "score": hit.score,
                }
                for hit in hits
            ],
            suggested_next_step="人工复核字段和证据后，再决定是否创建客服工单；系统不会自动发送回复。",
            prohibited_actions=["send_customer_message", "write_external_crm", "promise_refund", "decide_legal_liability"],
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        _event(
            trace,
            "build_ticket_draft",
            "生成待人工批准的结构化工单草稿",
            {"tool": "build_ticket_draft", "draft_id": draft.draft_id, "evidence_count": len(draft.evidence)},
        )
        _event(
            trace,
            "human_approval_gate",
            "草稿已暂停，等待人工批准",
            {"draft_id": draft.draft_id, "status": draft.status, "external_actions": False},
            "pending",
        )
        _event(trace, "agent_completed", "受控 Agent 运行完成", {"status": "draft_ready", "duration_ms": round((time.perf_counter() - started) * 1000, 2)})
        return AgentResponse(trace_id=trace_id, status="draft_ready", draft=draft, allowed_tools=ALLOWED_TOOLS, trace=trace)
