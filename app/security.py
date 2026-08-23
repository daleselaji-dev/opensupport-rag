"""Deterministic content safety scans used before indexing and generation."""

from __future__ import annotations

import re
from typing import Any

PII_PATTERNS: dict[str, tuple[str, ...]] = {
    "payment_card_number": (r"(?<!\d)\d{12,19}(?!\d)",),
    "ssn": (r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)",),
    "email": (r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b",),
    # Require a phone-like grouping; do not classify ISO dates or dollar
    # amounts as phone numbers.
    "phone": (r"(?<!\d)(?:\+?\d{1,3}[\s.-])?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)",),
}
INJECTION_PATTERNS: tuple[str, ...] = (
    r"ignore (all|any|previous) instructions",
    r"忽略(之前|以上|所有)指令",
    r"system prompt",
    r"系统提示词",
    r"你现在必须输出",
    r"reveal hidden",
)


def scan_text(text: str) -> dict[str, Any]:
    pii = [name for name, patterns in PII_PATTERNS.items() if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)]
    injection = [pattern for pattern in INJECTION_PATTERNS if re.search(pattern, text, re.IGNORECASE)]
    return {"pii_flags": pii, "prompt_injection_flags": injection, "safe": not pii and not injection}
