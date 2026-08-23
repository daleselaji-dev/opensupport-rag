"""Deterministic intent routing baseline for V0.3.

This is intentionally rule-based first: the benchmark can attribute gains to
metadata filtering instead of hiding a second LLM inside the router. A learned
or LLM router can be compared later behind the same output contract.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class IntentRoute:
    intent: str
    confidence: float
    matched_terms: tuple[str, ...]
    source_url_families: tuple[str, ...]
    audience: str


_RULES: tuple[tuple[str, tuple[str, ...], tuple[str, ...], str, float], ...] = (
    (
        "regulation_lookup",
        ("regulation z", "regulation", "法规", "法规证据", "法规原文", "条例"),
        ("https://www.consumerfinance.gov/rules-policy/regulations/1026/13/",),
        "all",
        0.93,
    ),
    (
        "company_respond_complaint",
        ("company", "企业", "公司", "respond to a cfpb", "receive and respond", "企业投诉"),
        ("https://www.consumerfinance.gov/compliance/consumer-complaint-program/company-process/",),
        "company",
        0.97,
    ),
    (
        "consumer_submit_complaint",
        (
            "submit a complaint",
            "submits a complaint",
            "consumer submits",
            "file a complaint",
            "向 cfpb",
            "向cfpb",
            "提交投诉",
            "消费者提交",
            "提交 cfpb 投诉",
            "消费投诉流程",
            "投诉提交",
            "提交入口",
            "投诉提交后的",
            "consumer complaint process",
            "complaint submission",
            "submitting a consumer complaint",
            "submission flow",
            "how can a consumer",
            "official complaint process",
            "official process for submitting",
        ),
        ("https://www.consumerfinance.gov/complaint/process/",),
        "consumer",
        0.97,
    ),
    (
        "unauthorized_transaction",
        ("unauthorized", "do not recognize", "don't recognize", "unrecognized", "unfamiliar", "unfamiliar charge", "unfamiliar transaction", "陌生扣款", "陌生的信用卡", "不认识的消费", "不是我本人", "未经本人", "未授权", "fraudulent charge", "fraud"),
        (
            "https://www.consumerfinance.gov/ask-cfpb/how-do-i-dispute-a-charge-on-my-credit-card-bill-en-61/",
            "https://www.consumerfinance.gov/ask-cfpb/what-is-an-unauthorized-use-of-a-credit-card-en-26/",
            "https://www.consumerfinance.gov/rules-policy/regulations/1026/13/",
        ),
        "consumer",
        0.94,
    ),
    (
        "billing_error",
        ("billing error", "bill mistake", "duplicate charge", "credit card bill", "账单错误", "账单有误", "账单金额", "重复收费", "争议扣款", "dispute a charge"),
        (
            "https://www.consumerfinance.gov/consumer-tools/credit-cards/how-to-fix-mistakes-in-your-credit-card-bill/",
            "https://www.consumerfinance.gov/ask-cfpb/how-do-i-dispute-a-charge-on-my-credit-card-bill-en-61/",
            "https://www.consumerfinance.gov/rules-policy/regulations/1026/13/",
        ),
        "consumer",
        0.91,
    ),
)


def classify_intent(question: str) -> IntentRoute:
    normalized = re.sub(r"\s+", " ", question.lower()).strip()
    # Consumer submission markers take precedence over a generic word such as
    # "company" when the user explicitly contrasts the two process pages.
    ordered_rules = sorted(_RULES, key=lambda rule: 0 if rule[0] == "consumer_submit_complaint" else 1)
    for intent, terms, urls, audience, confidence in ordered_rules:
        matched = tuple(term for term in terms if term in normalized)
        if matched:
            return IntentRoute(intent, confidence, matched, urls, audience)
    return IntentRoute("general_support", 0.35, (), (), "unknown")
