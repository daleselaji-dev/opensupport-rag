import asyncio

from app.agent import ComplaintAgent
from app.schemas import AgentRequest
from app.schemas import SourceHit


class FakeRag:
    async def retrieve(self, *args, **kwargs):
        raise AssertionError("missing-field and PII paths must stop before retrieval")


class DraftRag:
    async def retrieve(self, *args, **kwargs):
        return [SourceHit(citation="S1", source_type="guidance", authority_level="official", title="Guidance", score=.8, text="Official process evidence.", metadata={}, source_url="https://example.test")]


def test_agent_requests_missing_fields_before_tools():
    response = asyncio.run(ComplaintAgent(FakeRag()).run(
        AgentRequest(message="I see an unfamiliar credit card charge and need support to review it."),
        "trace-test",
    ))
    assert response.status == "needs_information"
    assert "previous_actions" in response.missing_fields
    assert response.trace[-1].name == "agent_stop"


def test_agent_blocks_pii_before_retrieval():
    response = asyncio.run(ComplaintAgent(FakeRag()).run(
        AgentRequest(message="我的卡号是 4111111111111111，请帮我查这笔交易。"),
        "trace-pii",
    ))
    assert response.status == "blocked_safety"
    assert "payment_card_number" in response.safety_flags


def test_agent_builds_pending_draft_with_allowlisted_tools():
    response = asyncio.run(ComplaintAgent(DraftRag()).run(
        AgentRequest(
            message="I do not recognize a credit card transaction and contacted the issuer already.",
            amount="20-30 USD",
            transaction_date="2026-08-20",
            merchant="Example merchant",
            previous_actions="contacted issuer",
        ),
        "trace-draft",
    ))
    assert response.status == "draft_ready"
    assert response.draft is not None
    assert response.draft.status == "pending_approval"
    assert "send_customer_message" in response.draft.prohibited_actions
    assert response.trace[-2].name == "human_approval_gate"
