"""Memory lifecycle and knowledge evolution.

Created -> Confirmed -> Used -> Observed -> Supported/Contradicted -> Updated ->
Revalidated -> Active / Stale / Archived

History is append-only. Nothing is deleted when newer information arrives; a
memory is narrowed, updated or marked stale and the original text is preserved.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.models.memory import (
    LIFECYCLE_TRANSITIONS,
    MemoryEvent,
    MemoryRecord,
    MemoryStatus,
    utcnow,
)
from backend.utils import new_id

#: The ordered happy path, used by the Evolution page.
EVOLUTION_STAGES: list[MemoryStatus] = [
    MemoryStatus.CREATED,
    MemoryStatus.CONFIRMED,
    MemoryStatus.USED,
    MemoryStatus.OBSERVED,
    MemoryStatus.SUPPORTED,
    MemoryStatus.REVALIDATED,
    MemoryStatus.ACTIVE,
]

TERMINAL_STATES = {MemoryStatus.ARCHIVED, MemoryStatus.REJECTED}


class InvalidTransition(ValueError):
    """Raised when a caller tries to make an illegal lifecycle jump."""


def can_transition(current: MemoryStatus, target: MemoryStatus) -> bool:
    if current == target:
        return True
    return target in LIFECYCLE_TRANSITIONS.get(current, set())


def assert_transition(current: MemoryStatus, target: MemoryStatus) -> None:
    if not can_transition(current, target):
        raise InvalidTransition(
            f"Cannot move memory from {current} to {target}."
        )


def apply_transition(
    memory: MemoryRecord,
    target: MemoryStatus,
    *,
    actor: str,
    action: str,
    note: str = "",
    payload: dict[str, Any] | None = None,
    at: datetime | None = None,
    strict: bool = True,
) -> MemoryEvent:
    """Move a memory to a new lifecycle state and append a history event."""
    current = MemoryStatus(memory.status)
    target_s = MemoryStatus(target)
    if strict:
        assert_transition(current, target_s)
    memory.status = target_s
    if target_s in {MemoryStatus.CONFIRMED, MemoryStatus.REVALIDATED}:
        memory.human_confirmed = True
        memory.last_validated_at = at or utcnow()
    if target_s == MemoryStatus.USED:
        memory.extra = {**(memory.extra or {}), "last_used_at": (at or utcnow()).isoformat()}
    if target_s in TERMINAL_STATES:
        memory.extra = {**(memory.extra or {}), "retired_at": (at or utcnow()).isoformat()}
    return MemoryEvent(
        id=new_id("mev"),
        memory_id=memory.id,
        at=at or utcnow(),
        from_status=current,
        to_status=target_s,
        action=action,
        actor=actor,
        note=note,
        payload=payload or {},
    )


def stage_progress(memory: MemoryRecord) -> dict[str, Any]:
    """Where this memory currently sits on the evolution ladder."""
    current = MemoryStatus(memory.status)
    reached: list[str] = []
    for stage in EVOLUTION_STAGES:
        reached.append(str(stage))
        if stage == current:
            break
    return {
        "stages": [str(s) for s in EVOLUTION_STAGES],
        "reached": reached,
        "current": str(current),
        "is_stale": current == MemoryStatus.STALE,
        "is_archived": current == MemoryStatus.ARCHIVED,
    }


__all__ = [
    "EVOLUTION_STAGES",
    "InvalidTransition",
    "TERMINAL_STATES",
    "apply_transition",
    "assert_transition",
    "can_transition",
    "stage_progress",
]
