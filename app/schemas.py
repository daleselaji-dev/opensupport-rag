from typing import Any, Literal

from pydantic import BaseModel, Field

SourceType = Literal["guidance", "regulation", "complaint"]
LifecycleStatus = Literal[
    "discovered",
    "downloaded",
    "validated",
    "parsed",
    "normalized",
    "deduplicated",
    "chunked",
    "enriched",
    "embedded",
    "indexed",
    "active",
    "quarantined",
    "retryable_failed",
    "permanent_failed",
]


class SourceDocument(BaseModel):
    """One traceable, independently retrievable source chunk."""

    chunk_id: str
    source_type: SourceType
    authority_level: Literal["official", "consumer_allegation"]
    title: str
    text: str
    source_url: str
    published_at: str | None = None
    complaint_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ComplaintRecord(BaseModel):
    complaint_id: str
    narrative: str
    product: str | None = None
    sub_product: str | None = None
    issue: str | None = None
    sub_issue: str | None = None
    company: str | None = None
    company_response: str | None = None
    timely: str | None = None
    date_received: str | None = None
    source_url: str
    identity_source: str = "api"
    export_url: str | None = None

    def to_document(self) -> SourceDocument:
        metadata = {
            "product": self.product,
            "sub_product": self.sub_product,
            "issue": self.issue,
            "sub_issue": self.sub_issue,
            "company": self.company,
            "company_response": self.company_response,
            "timely": self.timely,
            "date_received": self.date_received,
            "identity_source": self.identity_source,
            "export_url": self.export_url,
        }
        text = "\n".join(
            part
            for part in [
                f"Product: {self.product}" if self.product else "",
                f"Issue: {self.issue}" if self.issue else "",
                f"Sub-issue: {self.sub_issue}" if self.sub_issue else "",
                f"Consumer narrative: {self.narrative}",
            ]
            if part
        )
        return SourceDocument(
            chunk_id=f"complaint:{self.complaint_id}",
            source_type="complaint",
            authority_level="consumer_allegation",
            title=f"CFPB complaint {self.complaint_id}",
            text=text,
            source_url=self.source_url,
            published_at=self.date_received,
            complaint_id=self.complaint_id,
            metadata=metadata,
        )


RetrievalMode = Literal[
    "naive_vector",
    "hybrid_rrf",
    "production_advanced",
    "controlled_agent",
    "dense",
    "hybrid",
]
AssemblyVersion = Literal["v0_1", "v0_2", "v0_3", "v0_4", "v0_5", "v0_6", "v0_8"]


class IngestRequest(BaseModel):
    limit: int = Field(default=200, ge=1, le=1000)
    year: int = Field(default=2024, ge=2011, le=2030)


class LocalIngestRequest(BaseModel):
    filename: str = Field(default="complaints.csv", min_length=1, max_length=200)
    limit: int = Field(default=200, ge=1, le=15000)
    year: int | None = Field(default=None, ge=2011, le=2030)
    source_kind: Literal["cfpb_csv", "cfpb_mirror", "cfpb_bulk_official"] = "cfpb_csv"
    product_filter: str = Field(default="any", min_length=1, max_length=120)


class IngestResponse(BaseModel):
    requested_complaints: int
    fetched_complaints: int
    guidance_documents: int
    indexed_documents: int
    collection_name: str
    manifest_path: str
    guidance_fetch_failures: list[str] = Field(default_factory=list)
    snapshot_id: str = ""
    quality_report_path: str = "data/data_quality_latest.json"
    quality: "DataQualityReport | None" = None
    storage: dict[str, Any] = Field(default_factory=dict)


class DataQualityIssue(BaseModel):
    code: str
    severity: Literal["warning", "error"]
    message: str
    chunk_id: str | None = None
    source_url: str | None = None


class DataQualityReport(BaseModel):
    pipeline_version: str
    snapshot_id: str
    generated_at: str
    raw_documents: int
    accepted_documents: int
    duplicate_documents: int
    quarantined_documents: int
    indexed_documents: int = 0
    batch_indexed_documents: int = 0
    languages: dict[str, int] = Field(default_factory=dict)
    source_types: dict[str, int] = Field(default_factory=dict)
    stage_counts: dict[str, int] = Field(default_factory=dict)
    metadata_coverage: dict[str, float] = Field(default_factory=dict)
    issues: list[DataQualityIssue] = Field(default_factory=list)
    duplicate_chunk_ids: list[str] = Field(default_factory=list)
    manifest_consistent: bool | None = None
    notes: list[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    question: str = Field(min_length=5, max_length=3000)
    top_k: int | None = Field(default=None, ge=1, le=5)
    retrieval_mode: RetrievalMode = "naive_vector"
    assembly_version: AssemblyVersion = "v0_3"


class SourceHit(BaseModel):
    chunk_id: str = ""
    citation: str
    source_type: SourceType
    authority_level: Literal["official", "consumer_allegation"]
    title: str
    score: float
    text: str
    metadata: dict[str, Any]
    source_url: str
    published_at: str | None = None
    complaint_id: str | None = None


class TraceEvent(BaseModel):
    step: int
    name: str
    status: Literal["running", "completed", "failed", "pending"]
    duration_ms: float
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceHit]
    guardrail: str
    trace_id: str
    retrieval_mode: str = "naive_vector"
    assembly_version: AssemblyVersion = "v0_3"
    citation_valid: bool
    invalid_citations: list[str] = Field(default_factory=list)
    citation_coverage: float = 0.0
    safety_flags: list[str] = Field(default_factory=list)
    needs_human_review: bool = False
    trace_persistence: dict[str, Any] = Field(default_factory=dict)
    trace: list[TraceEvent] = Field(default_factory=list)


class RetrievalPreviewResponse(BaseModel):
    question: str
    retrieval_mode: str
    assembly_version: AssemblyVersion = "v0_3"
    sources: list[SourceHit]
    trace_id: str
    trace: list[TraceEvent] = Field(default_factory=list)


class DesignComparisonItem(BaseModel):
    mode: str
    title: str
    version_tag: str
    description: str
    steps_count: int
    total_duration_ms: float
    sources_count: int
    top_citations: list[str]
    answer_preview: str
    citation_valid: bool
    trace: list[TraceEvent]


class ComparisonResponse(BaseModel):
    question: str
    trace_id: str
    designs: list[DesignComparisonItem]


class EvalGate(BaseModel):
    key: str
    label: str
    actual: str | int | float | bool
    target: str | int | float | bool
    passed: bool
    note: str = ""


class EvalCaseResult(BaseModel):
    case_id: str
    question: str
    expected_urls: list[str]
    hit: bool
    rank: int | None = None
    reciprocal_rank: float
    retrieval_ms: float
    top_sources: list[dict[str, Any]] = Field(default_factory=list)
    trace: list[TraceEvent] = Field(default_factory=list)
    slices: list[str] = Field(default_factory=list)
    expected_action: str = "answer"
    required_source_types: list[str] = Field(default_factory=list)
    required_source_types_hit: bool = True


class EvalSummary(BaseModel):
    version: str
    retrieval_mode: Literal["dense", "hybrid"] = "dense"
    assembly_version: AssemblyVersion = "v0_3"
    evaluated_at: str
    collection_name: str
    embedding_model: str
    index_inventory: dict[str, Any]
    metrics: dict[str, Any]
    gates: list[EvalGate]
    cases: list[EvalCaseResult]
    overall_passed: bool
    benchmark_version: str = "customer-support-v0.2-seed"
    limitations: list[str] = Field(default_factory=list)


class AnswerEvalCaseResult(BaseModel):
    case_id: str
    question: str
    expected_action: str
    answer: str
    latency_ms: float
    citation_valid: bool
    invalid_citations: list[str] = Field(default_factory=list)
    citation_coverage: float = 0.0
    refusal_signal: bool = False
    forbidden_claims_found: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    fallback_mode: str | None = None
    needs_human_review: bool = False
    passed: bool
    trace: list[TraceEvent] = Field(default_factory=list)


class AnswerEvalSummary(BaseModel):
    benchmark_version: str
    assembly_version: AssemblyVersion
    evaluated_at: str
    chat_model: str
    case_count: int
    metrics: dict[str, Any]
    gates: list[EvalGate]
    cases: list[AnswerEvalCaseResult]
    overall_passed: bool
    limitations: list[str] = Field(default_factory=list)


class AgentRequest(BaseModel):
    """Structured complaint intake for the bounded V1 agent."""

    message: str = Field(min_length=10, max_length=3000)
    product: str | None = Field(default=None, max_length=120)
    issue: str | None = Field(default=None, max_length=120)
    transaction_date: str | None = Field(default=None, max_length=40)
    amount: str | None = Field(default=None, max_length=40)
    merchant: str | None = Field(default=None, max_length=160)
    previous_actions: str | None = Field(default=None, max_length=500)
    requested_outcome: str | None = Field(default=None, max_length=300)


class AgentDraft(BaseModel):
    draft_id: str
    status: Literal["pending_approval", "approved"] = "pending_approval"
    fields: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    suggested_next_step: str
    prohibited_actions: list[str] = Field(default_factory=list)
    created_at: str


class AgentResponse(BaseModel):
    trace_id: str
    status: Literal["needs_information", "draft_ready", "blocked_safety", "out_of_domain"]
    missing_fields: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    draft: AgentDraft | None = None
    safety_flags: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    trace: list[TraceEvent] = Field(default_factory=list)


class IndexActivationRequest(BaseModel):
    collection: str = Field(min_length=1, max_length=200)
    sparse_collection: str = Field(min_length=1, max_length=200)
    reason: str = Field(default="manual_activation", min_length=3, max_length=300)


class GoldenReviewSignoffRequest(BaseModel):
    role: Literal["reviewer_a", "reviewer_b"]
    reviewer: str = Field(min_length=2, max_length=120)
    approved_case_ids: list[str] = Field(default_factory=list, max_length=100)
    notes: str = Field(default="", max_length=2000)
