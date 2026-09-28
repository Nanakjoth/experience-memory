"""Audit trail."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from backend.models.audit import AuditEventType
from backend.services import Services, get_services

router = APIRouter(tags=["audit"])

EVENT_LABELS: dict[str, str] = {
    "memory_captured": "Memory captured",
    "memory_reviewed": "Memory reviewed",
    "memory_promoted": "Memory promoted",
    "memory_retrieved": "Memory retrieved",
    "memory_used_by_agent": "Memory used by agent",
    "memory_contradicted": "Memory contradicted",
    "memory_updated": "Memory updated",
    "memory_restricted": "Memory restricted",
    "memory_expired": "Memory expired",
    "memory_revalidated": "Memory revalidated",
    "memory_archived": "Memory archived",
    "memory_rejected": "Memory rejected",
    "outcome_recorded": "Outcome recorded",
    "architecture_change": "Architecture change",
    "memory_recalled": "Memory recalled",
    "hindsight_retain": "Hindsight retain",
    "hindsight_recall": "Hindsight recall",
    "hindsight_reflect": "Hindsight reflect",
    "permission_denied": "Permission denied",
    "environment_changed": "Environment changed",
    "demo_step": "Demo step",
    "demo_reset": "Demo reset",
}


@router.get("/audit")
async def audit(
    s: Services = Depends(get_services),
    event_type: str | None = Query(None),
    actor: str | None = Query(None),
    memory_id: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
) -> dict[str, Any]:
    events = s.db.list_audit(
        event_type=event_type, actor=actor, memory_id=memory_id, limit=limit
    )
    return {
        "events": [
            {
                "id": e.id,
                "at": e.at.isoformat(),
                "time": e.at.strftime("%H:%M"),
                "event_type": str(e.event_type),
                "label": EVENT_LABELS.get(str(e.event_type), str(e.event_type)),
                "actor": e.actor,
                "actor_role": e.actor_role,
                "subject": e.subject,
                "memory_id": e.memory_id,
                "request_id": e.request_id,
                "detail": e.detail,
                "payload": e.payload,
            }
            for e in events
        ],
        "count": len(events),
        "event_types": [str(e) for e in AuditEventType],
        "labels": EVENT_LABELS,
    }


__all__ = ["EVENT_LABELS", "router"]
