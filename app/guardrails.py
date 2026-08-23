"""Deterministic post-generation guardrails for customer-support answers."""

from __future__ import annotations

import re
from typing import Any, Iterable

_CITATION_PATTERN = re.compile(r"\[([SC]\d+)\]")
_SENTENCE_PATTERN = re.compile(r"[^。！？.!?]+[。！？.!?]?")
_SAFETY_FOOTER = re.compile(r"这不是法律、金融或账户处理决定。|this is not a legal, financial, or account decision\.?")
# Local multilingual models commonly emit full-width citation brackets
# (`【S1】`, `［S1］`) even when the prompt requests ASCII `[S1]`.  Normalize
# only the strict citation token shape; arbitrary brackets remain untouched.
_CITATION_VARIANT_PATTERN = re.compile(r"[\[【［]\s*([SC]\d+)\s*[\]】］]")
FORBIDDEN_PATTERNS: dict[str, tuple[str, ...]] = {
    "refund_promise": (r"保证.{0,12}退款", r"一定会退款", r"will refund", r"guarantee.{0,20}refund", r"refund.{0,20}today"),
    "legal_liability": (r"公司违法", r"企业违法", r"违反法律", r"broke the law", r"illegal", r"legally liable"),
    "company_guilt": (r"公司有罪", r"公司应负责", r"company is guilty", r"company committed"),
    "account_investigation_result": (r"已经完成.{0,12}调查", r"调查结果是", r"investigation is complete", r"account investigation found"),
    "account_action": (r"我已经修改", r"我已冻结", r"we changed your account", r"your account has been updated"),
    "pii_disclosure": (r"\b\d{12,19}\b", r"完整卡号", r"full card number", r"social security number"),
    "system_prompt_leak": (r"system prompt", r"系统提示词", r"hidden instructions"),
    "invented_bank_policy": (r"银行规定.{0,20}必须", r"the bank policy requires", r"guaranteed bank policy"),
    "guaranteed_outcome": (r"一定会受理", r"保证结果", r"guarantee.{0,20}outcome"),
}

REQUEST_RISK_PATTERNS: dict[str, tuple[str, ...]] = {
    "refund_or_outcome_promise": (r"保证.{0,16}(退款|结果)", r"一定.{0,12}(退款|结果)", r"promise.{0,24}refund", r"guarantee.{0,24}(refund|outcome)", r"refund.{0,20}today"),
    "legal_conclusion": (r"公司违法", r"企业违法", r"违反法律", r"确认.{0,10}违法", r"broke the law", r"legally liable"),
    "account_decision": (r"账户调查", r"账户处理", r"修改账户", r"直接告诉我怎么改", r"account investigation", r"update my account"),
    "pii_or_hidden_data": (r"个人信息", r"联系方式", r"完整.*信息", r"hidden customer data", r"system prompt", r"系统提示词", r"ignore (all|any|previous) instructions"),
    "unsupported_domain_action": (r"ATM", r"atm", r"取款机", r"cash machine"),
}


def detect_request_risks(question: str) -> list[str]:
    """Detect requests that require refusal or human handling before generation."""

    return [name for name, patterns in REQUEST_RISK_PATTERNS.items() if any(re.search(pattern, question, re.IGNORECASE) for pattern in patterns)]


def normalize_citations(answer: str) -> str:
    """Canonicalize safe citation marker variants to ASCII `[S1]`/`[C1]`."""

    return _CITATION_VARIANT_PATTERN.sub(lambda match: f"[{match.group(1)}]", answer)


def find_forbidden_claims(answer: str, requested: Iterable[str] | None = None) -> list[str]:
    claims = requested or FORBIDDEN_PATTERNS.keys()
    return [claim for claim in claims if any(re.search(pattern, answer, re.IGNORECASE) for pattern in FORBIDDEN_PATTERNS.get(claim, ()))]


def citation_coverage(answer: str, sources: Iterable[Any]) -> float:
    available = {source.citation for source in sources}
    answer = normalize_citations(_SAFETY_FOOTER.sub("", answer))
    raw_sentences = [item.strip() for item in _SENTENCE_PATTERN.findall(answer) if item.strip()]
    sentences: list[str] = []
    for item in raw_sentences:
        if _CITATION_PATTERN.fullmatch(item):
            if sentences:
                sentences[-1] += item
        else:
            sentences.append(item)
    factual = [item for item in sentences if item and not any(marker in item.lower() for marker in ("人工复核", "人工核对", "human review", "not a legal", "当前模型回答未"))]
    if not factual:
        return 1.0
    supported = sum(bool(_CITATION_PATTERN.findall(item)) and all(cite in available for cite in _CITATION_PATTERN.findall(item)) for item in factual)
    return round(supported / len(factual), 4)


def analyze_answer(answer: str, sources: list[Any], min_coverage: float = 0.8) -> dict[str, Any]:
    available = {source.citation for source in sources}
    citations = _CITATION_PATTERN.findall(normalize_citations(answer))
    invalid = sorted({citation for citation in citations if citation not in available})
    coverage = citation_coverage(answer, sources)
    forbidden = find_forbidden_claims(answer)
    return {
        "citation_coverage": coverage,
        "invalid_citations": invalid,
        "safety_flags": forbidden,
        "needs_human_review": bool(invalid or forbidden or coverage < min_coverage),
    }
