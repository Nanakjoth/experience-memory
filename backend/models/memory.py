"""Application-level memory schema.

Hindsight is the memory engine. It does not know about governance, scope,
confidence or lifecycle, so MemoryOS keeps its own metadata store in SQLite and
links every application memory to the Hindsight fact that backs it.

The two systems are joined by ``hindsight_fact_id``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MemoryType(StrEnum):
    FACT = "FACT"
    EXPERIENCE = "EXPERIENCE"
    LESSON = "LESSON"
    OBSERVATION = "OBSERVATION"
    DECISION = "DECISION"
    EXCEPTION = "EXCEPTION"
    RELATIONSHIP = "RELATIONSHIP"
    COMMITMENT = "COMMITMENT"
    HYPOTHESIS = "HYPOTHESIS"
    CORRECTION = "CORRECTION"
    EVENT = "EVENT"


class Visibility(StrEnum):
    """Memory visibility. Promotion between levels is never automatic."""

    PERSONAL = "PERSONAL"
    TEAM = "TEAM"
    ORGANIZATION = "ORGANIZATION"


class AccessLevel(StrEnum):
    PUBLIC_ORG = "PUBLIC_ORG"
    TEAM_ONLY = "TEAM_ONLY"
    OWNER_ONLY = "OWNER_ONLY"
    RESTRICTED = "RESTRICTED"


class Sensitivity(StrEnum):
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    PUBLIC = "PUBLIC"


class MemoryStatus(StrEnum):
    """The knowledge-evolution state machine."""

    CREATED = "CREATED"
    CONFIRMED = "CONFIRMED"
    USED = "USED"
    OBSERVED = "OBSERVED"
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UPDATED = "UPDATED"
    REVALIDATED = "REVALIDATED"
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    ARCHIVED = "ARCHIVED"
    REJECTED = "REJECTED"


#: Legal forward transitions of the knowledge-evolution lifecycle.
LIFECYCLE_TRANSITIONS: dict[MemoryStatus, set[MemoryStatus]] = {
    MemoryStatus.CREATED: {
        MemoryStatus.CONFIRMED,
        MemoryStatus.REJECTED,
        MemoryStatus.ACTIVE,
        MemoryStatus.ARCHIVED,
    },
    MemoryStatus.CONFIRMED: {
        MemoryStatus.ACTIVE,
        MemoryStatus.USED,
        MemoryStatus.OBSERVED,
        MemoryStatus.CONTRADICTED,
        MemoryStatus.STALE,
        MemoryStatus.ARCHIVED,
    },
    MemoryStatus.ACTIVE: {
        MemoryStatus.USED,
        MemoryStatus.OBSERVED,
        MemoryStatus.SUPPORTED,
        MemoryStatus.CONTRADICTED,
        MemoryStatus.UPDATED,
        MemoryStatus.REVALIDATED,
        MemoryStatus.STALE,
        MemoryStatus.ARCHIVED,
    },
    MemoryStatus.USED: {
        MemoryStatus.OBSERVED,
        MemoryStatus.SUPPORTED,
        MemoryStatus.CONTRADICTED,
        MemoryStatus.UPDATED,
        MemoryStatus.REVALIDATED,
        MemoryStatus.STALE,
        MemoryStatus.ARCHIVED,
    },
    MemoryStatus.OBSERVED: {
        MemoryStatus.SUPPORTED,
        MemoryStatus.CONTRADICTED,
        MemoryStatus.UPDATED,
        MemoryStatus.REVALIDATED,
        MemoryStatus.STALE,
        MemoryStatus.ARCHIVED,
    },
    MemoryStatus.SUPPORTED: {
        MemoryStatus.OBSERVED,
        MemoryStatus.CONTRADICTED,
        MemoryStatus.UPDATED,
        MemoryStatus.REVALIDATED,
        MemoryStatus.STALE,
        MemoryStatus.ARCHIVED,
    },
    MemoryStatus.CONTRADICTED: {
        MemoryStatus.UPDATED,
        MemoryStatus.REVALIDATED,
        MemoryStatus.STALE,
        MemoryStatus.ARCHIVED,
        MemoryStatus.ACTIVE,
    },
    MemoryStatus.UPDATED: {
        MemoryStatus.ACTIVE,
        MemoryStatus.REVALIDATED,
        MemoryStatus.OBSERVED,
        MemoryStatus.CONTRADICTED,
        MemoryStatus.STALE,
        MemoryStatus.ARCHIVED,
    },
    MemoryStatus.REVALIDATED: {
        MemoryStatus.ACTIVE,
        MemoryStatus.USED,
        MemoryStatus.OBSERVED,
        MemoryStatus.CONTRADICTED,
        MemoryStatus.STALE,
    },
    MemoryStatus.STALE: {
        MemoryStatus.REVALIDATED,
        MemoryStatus.UPDATED,
        MemoryStatus.ARCHIVED,
        MemoryStatus.ACTIVE,
        MemoryStatus.CONTRADICTED,
    },
    MemoryStatus.ARCHIVED: {MemoryStatus.ACTIVE, MemoryStatus.REVALIDATED},
    MemoryStatus.REJECTED: {MemoryStatus.CREATED, MemoryStatus.ARCHIVED},
}


class ConfidenceBand(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class SourceProvenance(BaseModel):
    """Where a memory came from. Required for provenance guarantees."""

    model_config = ConfigDict(use_enum_values=True)

    source_type: str
    source_id: str
    source_name: str
    captured_at: datetime = Field(default_factory=utcnow)
    observed_at: datetime | None = None

    @field_validator("source_type")
    @classmethod
    def _known_source(cls, v: str) -> str:
        allowed = {
            "expert_interview",
            "incident",
            "handover_document",
            "outcome",
            "architecture_change",
            "agent_synthesis",
        }
        if v not in allowed:
            raise ValueError(f"source_type must be one of {sorted(allowed)}")
        return v


class MemoryGateDecision(BaseModel):
    """Output of the Memory Gate, evaluated before anything is stored."""

    model_config = ConfigDict(use_enum_values=True)

    purpose: str
    scope: str
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    retention_days: int = 365
    authorization_required: bool = True
    future_useful: bool = True
    needs_persistent_memory: bool = True
    contains_secret: bool = False
    contains_personal_data: bool = False
    decision: str = "STORE"
    reasons: list[str] = Field(default_factory=list)


class MemoryRecord(BaseModel):
    """A single application memory.

    All fields from the MemoryOS schema are present. Hindsight supplies the raw
    recalled text; MemoryOS supplies the governance around it.
    """

    model_config = ConfigDict(use_enum_values=True)

    id: str
    type: MemoryType
    title: str
    content: str
    summary: str = ""

    source_type: str
    source_id: str
    source_name: str
    captured_at: datetime = Field(default_factory=utcnow)
    observed_at: datetime | None = None

    scope: str
    owner: str
    domain: str
    purpose: str

    created_at: datetime = Field(default_factory=utcnow)
    last_validated_at: datetime | None = None
    expiry_at: datetime | None = None

    confidence: float = 0.5
    evidence_count: int = 0
    status: MemoryStatus = MemoryStatus.CREATED
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    access_level: AccessLevel = AccessLevel.TEAM_ONLY
    visibility: Visibility = Visibility.PERSONAL

    related_entities: list[str] = Field(default_factory=list)
    related_memories: list[str] = Field(default_factory=list)

    # Link into the Hindsight memory bank.
    hindsight_fact_id: str | None = None
    hindsight_document_id: str | None = None

    # Governance / provenance extras.
    gate: MemoryGateDecision | None = None
    human_confirmed: bool = False
    promoted_by: str | None = None
    version: int = 1
    tags: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)

    def is_expired(self, now: datetime | None = None) -> bool:
        if self.expiry_at is None:
            return False
        return (now or utcnow()) >= self.expiry_at

    def is_usable(self, now: datetime | None = None) -> bool:
        """Whether this memory may be presented as current operational guidance."""
        return self.status not in {
            MemoryStatus.ARCHIVED,
            MemoryStatus.REJECTED,
        } and not self.is_expired(now)


class MemoryEvent(BaseModel):
    """An entry in a memory's history."""

    model_config = ConfigDict(use_enum_values=True)

    id: str
    memory_id: str
    at: datetime = Field(default_factory=utcnow)
    from_status: MemoryStatus | None = None
    to_status: MemoryStatus
    action: str
    actor: str
    note: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


class EvidenceLink(BaseModel):
    """Links a memory to the incidents / outcomes / sources supporting it."""

    model_config = ConfigDict(use_enum_values=True)

    memory_id: str
    evidence_type: str  # incident | outcome | expert_interview | architecture_change
    evidence_id: str
    evidence_label: str
    polarity: str = "supports"  # supports | contradicts
    detail: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class Contradiction(BaseModel):
    """A detected conflict between old knowledge and new evidence.

    History is never destroyed. Resolution actions narrow scope or mark the old
    memory stale while keeping the original text intact.
    """

    model_config = ConfigDict(use_enum_values=True)

    id: str
    memory_id: str
    memory_title: str
    memory_scope: str
    conflicting_source_id: str
    conflicting_source_type: str
    conflicting_content: str
    current_environment: str
    detected_at: datetime = Field(default_factory=utcnow)
    reason: str
    status: str = "REVIEW_REQUIRED"  # REVIEW_REQUIRED | RESOLVED
    resolution: str | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None


class LearningEvent(BaseModel):
    """A 'recent intelligence' item on the dashboard."""

    model_config = ConfigDict(use_enum_values=True)

    id: str
    at: datetime = Field(default_factory=utcnow)
    kind: str
    message: str
    memory_id: str | None = None
    detail: str = ""
    synthetic: bool = False


__all__ = [
    "AccessLevel",
    "ConfidenceBand",
    "Contradiction",
    "EvidenceLink",
    "LIFECYCLE_TRANSITIONS",
    "LearningEvent",
    "MemoryEvent",
    "MemoryGateDecision",
    "MemoryRecord",
    "MemoryStatus",
    "MemoryType",
    "Sensitivity",
    "SourceProvenance",
    "Visibility",
    "utcnow",
]
