"""API request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from backend.models.memory import AccessLevel, Visibility


# --- health ---------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    memory_engine: str
    bank_id: str
    engine_mode: str
    engine_label: str
    engine_simulated: bool
    degraded_reason: str | None = None
    hindsight_base_url: str
    memory_count: int
    incident_count: int
    config: dict[str, Any]
    synthetic_data: bool = True
    at: datetime


# --- capture --------------------------------------------------------------
class CaptureTurn(BaseModel):
    prompt: str
    answer: str


class CaptureRequest(BaseModel):
    expert: str = "Arun"
    role: str = "Senior DevOps Engineer"
    team: str = "Payments Operations"
    scope: str = "Payment Queue v1"
    system: str = "Payment Platform"
    turns: list[CaptureTurn] = Field(default_factory=list)
    free_text: str | None = None
    visibility: Visibility = Visibility.PERSONAL
    auto_promote: bool = False
    source_id: str | None = None

    @field_validator("turns")
    @classmethod
    def _non_empty_answers(cls, v: list[CaptureTurn]) -> list[CaptureTurn]:
        """Drop unanswered prompts. The endpoint rejects a capture with nothing to
        store, rather than rejecting the request shape."""
        return [t for t in v if t.answer.strip()]


class CaptureResponse(BaseModel):
    source_id: str
    retained: bool
    engine_mode: str
    engine_simulated: bool
    memories: list[dict[str, Any]]
    rejected: list[dict[str, str]]
    hindsight_fact_ids: list[str]
    duration_ms: int


# --- ask ------------------------------------------------------------------
class AskRequest(BaseModel):
    question: str | None = None
    actor: str = "maya"
    current_scope: str | None = None


class AskResponse(BaseModel):
    question: str
    asked_by: dict[str, str]
    at: str
    answer: dict[str, Any]
    lens: list[dict[str, Any]]
    memories_used: list[dict[str, Any]]
    hindsight_facts: list[dict[str, Any]]
    withheld: list[dict[str, str]]
    trace: dict[str, Any]
    warnings: list[str]
    privacy_notice: dict[str, Any] | None = None
    duration_ms: int
    engine_mode: str
    engine_simulated: bool
    request_id: str
    # Hindsight returned more facts than the actor is allowed to read. Counted,
    # never printed, so the trace can stay honest without leaking content.
    fact_count: int = 0
    suppressed_fact_count: int = 0
    outdated: bool = False
    confidence: dict[str, Any] = Field(default_factory=dict)


# --- outcome --------------------------------------------------------------
class OutcomeRequest(BaseModel):
    question: str
    recommendation: str
    actual_action: str
    result: str
    notes: str = ""
    queue_depth: float | None = None
    scope: str = "Payment Queue v1"
    actor: str = "maya"
    outcome_id: str | None = None
    # Optional: the reporter states whether it worked. When omitted the system
    # classifies the result text and always returns its reasoning.
    successful: bool | None = None


class OutcomeResponse(BaseModel):
    outcome_id: str
    memory_id: str
    status: str
    confidence: float
    band: str
    evidence_count: int
    contradiction: dict[str, Any] | None = None
    message: str
    engine_mode: str
    engine_simulated: bool
    linked_memories: list[str] = Field(default_factory=list)
    linked_detail: list[dict[str, Any]] = Field(default_factory=list)
    reinforced: list[dict[str, Any]] = Field(default_factory=list)
    confidence_before: float = 0.0
    confidence_delta: float = 0.0
    successful: bool | None = None
    verdict: dict[str, Any] = Field(default_factory=dict)


# --- architecture change ---------------------------------------------------
class ArchitectureChangeRequest(BaseModel):
    id: str | None = None
    title: str
    system: str = "Payment Platform"
    component: str
    summary: str
    effective_at: datetime | None = None
    invalidates_scope: str | None = None


class ArchitectureChangeResponse(BaseModel):
    change_id: str
    current_environment: str
    previous_environment: str
    contradictions: list[dict[str, Any]]
    new_memory_ids: list[str]
    message: str
    engine_mode: str
    engine_simulated: bool


# --- memories -------------------------------------------------------------
class MemoryActionRequest(BaseModel):
    actor: str = "steward"
    note: str = ""
    reason: str = ""


class PromoteRequest(MemoryActionRequest):
    target: Visibility = Visibility.ORGANIZATION


class RestrictRequest(MemoryActionRequest):
    access_level: AccessLevel | None = None


class ExpireRequest(MemoryActionRequest):
    days: int | None = None


class ResolveContradictionRequest(BaseModel):
    action: Literal["confirm", "restrict", "update", "stale"]
    actor: str = "steward"
    note: str = ""


# --- demo -----------------------------------------------------------------
class DemoSeedRequest(BaseModel):
    include_incidents: bool = True
    include_handover: bool = True
    include_architecture: bool = True
    auto_confirm_evidence: bool = True
    promote_key_lesson: bool = True
    reset: bool = True


class DemoStepRequest(BaseModel):
    step: int
    note: str = ""


class DemoActionResponse(BaseModel):
    ok: bool
    step: str = ""
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)


class DemoRunResponse(BaseModel):
    id: str
    mode: str
    status: str
    started_at: str
    finished_at: str | None = None
    steps: list[dict[str, Any]]
    progress_percent: int = 0
    duration_ms: int = 0


__all__ = [
    "ArchitectureChangeRequest",
    "ArchitectureChangeResponse",
    "AskRequest",
    "AskResponse",
    "CaptureRequest",
    "CaptureResponse",
    "CaptureTurn",
    "DemoActionResponse",
    "DemoRunResponse",
    "DemoSeedRequest",
    "DemoStepRequest",
    "ExpireRequest",
    "HealthResponse",
    "MemoryActionRequest",
    "OutcomeRequest",
    "OutcomeResponse",
    "PromoteRequest",
    "ResolveContradictionRequest",
    "RestrictRequest",
]
