import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

GuidanceTypeLiteral = Literal["EDUCATIONAL", "OPERATIONAL_INSTRUCTION", "CLINICAL_RULE"]
ApprovalStatusLiteral = Literal["draft", "under_review", "approved", "rejected", "retired"]

VALID_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["under_review"],
    "under_review": ["approved", "rejected", "draft"],
    "approved": ["retired", "under_review"],
    "rejected": ["draft"],
    "retired": ["under_review"],
}


class GuidanceSourceBase(BaseModel):
    """Source authority attributes according to NASA Spaceflight standards."""
    model_config = ConfigDict(from_attributes=True)

    source_identifier: str = Field(..., max_length=64, description="Authoritative code (e.g. NASA-STD-3001-VOL1)")
    title: str = Field(..., max_length=255, description="Full publication title")
    publisher: str = Field(..., max_length=255, description="Issuing agency or authority")
    document_url: str | None = Field(None, max_length=512, description="Canonical document URL")
    version: str = Field(..., max_length=32, description="Source revision / edition")
    publication_date: datetime | None = Field(None, description="Official publication date")
    access_date: datetime | None = Field(None, description="Date source material was accessed/verified")
    citation_reference: str | None = Field(None, max_length=255, description="Chapter, section, or page reference")
    summary: str | None = Field(None, description="Concise summary with attribution")
    health_indicator: str | None = Field(None, max_length=64, description="Relevant biomarker/indicator")
    spaceflight_hazard: str | None = Field(None, max_length=64, description="Associated spaceflight hazard")
    mission_context: str | None = Field(None, max_length=64, description="Operational mission context")
    target_population: str | None = Field(None, max_length=64, description="Target crew population")
    evidence_limitations: str | None = Field(None, description="Evidence caveats and limitations")
    intended_use: str | None = Field(None, description="Intended scope of guidance")
    next_review_date: datetime | None = Field(None, description="Scheduled next-review date")
    effective_from: datetime | None = Field(None, description="Start of validity")
    effective_to: datetime | None = Field(None, description="End of validity")


class GuidanceSourceCreate(GuidanceSourceBase):
    """Payload to register a new authoritative guidance source."""
    review_state: str = Field("approved", max_length=32)
    approval_status: str = Field("approved", max_length=32)
    reviewer_metadata: dict[str, Any] | None = None


class GuidanceSourceResponse(GuidanceSourceBase):
    """Authoritative guidance source response DTO."""
    id: uuid.UUID
    review_state: str
    approval_status: str
    reviewer_metadata: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GuidanceSourceListResponse(BaseModel):
    """Paginated collection of guidance sources."""
    items: list[GuidanceSourceResponse]
    total: int
    limit: int
    offset: int


class GuidanceDocumentBase(BaseModel):
    """Core guidance document attributes separating educational, operational, and clinical rules."""
    model_config = ConfigDict(from_attributes=True)

    document_identifier: str = Field(..., max_length=64, description="Unique guidance code")
    guidance_source_id: uuid.UUID | None = Field(None, description="Foreign key to parent source standard")
    title: str = Field(..., max_length=255, description="Descriptive title")
    guidance_type: GuidanceTypeLiteral = Field(
        ...,
        description="Category: EDUCATIONAL (learning/research), OPERATIONAL_INSTRUCTION (protocol), or CLINICAL_RULE (threshold)",
    )
    summary: str = Field(..., description="Concise summary with attribution")
    content: str | None = Field(None, description="Detailed guidance text or operational protocol")
    citation_reference: str | None = Field(None, max_length=255, description="Page or passage reference")
    topic: str | None = Field(None, max_length=128, description="Topical area (e.g. Cardiovascular, Fatigue)")
    health_indicator: str | None = Field(None, max_length=64, description="Associated health indicator")
    spaceflight_hazard: str | None = Field(None, max_length=64, description="Associated spaceflight hazard")
    mission_context: str | None = Field(None, max_length=64, description="Applicable flight phase / context")
    target_population: str | None = Field(None, max_length=64, description="Target crew population")
    evidence_limitations: str | None = Field(None, description="Contraindications and limitations")
    intended_use: str | None = Field(None, description="Intended operational / educational purpose")
    version: str = Field("1.0.0", max_length=32, description="Semantic version string")
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    next_review_date: datetime | None = None


class GuidanceDocumentCreate(GuidanceDocumentBase):
    """Payload to submit new guidance into the registry (starts in draft status)."""
    approval_status: Literal["draft", "under_review"] = "draft"


class GuidanceReviewRecordResponse(BaseModel):
    """Auditable review history entry."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    guidance_id: uuid.UUID
    reviewer_id: str | None = None
    reviewer_role: str
    previous_status: str
    new_status: str
    decision_rationale: str
    reviewed_at: datetime
    metadata_snapshot: dict[str, Any] | None = None


class GuidanceDocumentResponse(GuidanceDocumentBase):
    """Guidance document response with approval workflow history and optional redaction."""
    id: uuid.UUID
    approval_status: str
    superseded_by_id: uuid.UUID | None = None
    guidance_source: GuidanceSourceResponse | None = None
    review_metadata: dict[str, Any] | None = None
    review_records: list[GuidanceReviewRecordResponse] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GuidanceDocumentListResponse(BaseModel):
    """Paginated collection of guidance documents."""
    items: list[GuidanceDocumentResponse]
    total: int
    limit: int
    offset: int


class GuidanceReviewCreate(BaseModel):
    """Payload to transition guidance approval status with medical rationale."""
    new_status: ApprovalStatusLiteral
    decision_rationale: str = Field(..., min_length=5, description="Auditable justification for approval state transition")
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    next_review_date: datetime | None = None
    metadata_snapshot: dict[str, Any] | None = None


class GuidanceSupersedeRequest(BaseModel):
    """Payload to supersede an existing guidance document with a new version."""
    new_version: str = Field(..., min_length=1, max_length=32, description="Semantic version string (e.g. 2.0.0)")
    title: str | None = Field(None, max_length=255)
    summary: str | None = None
    content: str | None = None
    citation_reference: str | None = Field(None, max_length=255)
    evidence_limitations: str | None = None
    intended_use: str | None = None
    decision_rationale: str = Field(..., min_length=5, description="Rationale for superseding previous version")
