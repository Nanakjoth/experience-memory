"""Audit + demo-event models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.models.memory import utcnow


class AuditEventType(StrEnum):
    MEMORY_CAPTURED = "memory_captured"
    MEMORY_REVIEWED = "memory_reviewed"
    MEMORY_PROMOTED = "memory_promoted"
    MEMORY_RETRIEVED = "memory_retrieved"
    MEMORY_USED_BY_AGENT = "memory_used_by_agent"
    MEMORY_CONTRADICTED = "memory_contradicted"
    MEMORY_UPDATED = "memory_updated"
    MEMORY_RESTRICTED = "memory_restricted"
    MEMORY_EXPIRED = "memory_expired"
    MEMORY_REVALIDATED = "memory_revalidated"
    MEMORY_ARCHIVED = "memory_archived"
    MEMORY_REJECTED = "memory_rejected"
    OUTCOME_RECORDED = "outcome_recorded"
    ARCHITECTURE_CHANGE = "architecture_change"
    MEMORY_RECALLED = "memory_recalled"
    HINDSIGHT_RETAIN = "hindsight_retain"
    HINDSIGHT_RECALL = "hindsight_recall"
    HINDSIGHT_REFLECT = "hindsight_reflect"
    PERMISSION_DENIED = "permission_denied"
    ENVIRONMENT_CHANGED = "environment_changed"
    DEMO_STEP = "demo_step"
    DEMO_RESET = "demo_reset"


class AuditEvent(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str
    at: datetime = Field(default_factory=utcnow)
    event_type: AuditEventType
    actor: str
    actor_role: str = "system"
    subject: str = ""
    memory_id: str | None = None
    request_id: str | None = None
    detail: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


class DemoStepResult(BaseModel):
    """One executed step of the guided demo."""

    model_config = ConfigDict(use_enum_values=True)

    index: int
    key: str
    title: str
    narration: str
    status: str = "ok"  # ok | error | skipped
    duration_ms: int = 0
    payload: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class DemoRun(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None
    mode: str = "full"
    steps: list[DemoStepResult] = Field(default_factory=list)
    status: str = "running"

    @property
    def progress_percent(self) -> int:
        if not self.steps:
            return 0
        return int(round(100 * len(self.steps) / self.steps[-1].index))


__all__ = ["AuditEvent", "AuditEventType", "DemoRun", "DemoStepResult"]
