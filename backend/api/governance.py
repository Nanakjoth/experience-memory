"""Governance endpoints: review, promote, validate, restrict, expire,
architecture change registration and contradiction resolution.
"""

from __future__ import annotations

from datetime import timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.actors import actor_for
from backend.api.schemas import (
    ArchitectureChangeRequest,
    ArchitectureChangeResponse,
    ExpireRequest,
    MemoryActionRequest,
    PromoteRequest,
    ResolveContradictionRequest,
    RestrictRequest,
)
from backend.memory.contradiction import RESOLUTION_ACTIONS
from backend.memory.governance import MemoryNotFound
from backend.memory.lifecycle import InvalidTransition
from backend.models.audit import AuditEvent, AuditEventType
from backend.models.memory import LearningEvent, utcnow
from backend.models.permissions import PermissionDenied
from backend.services import Services, get_services
from backend.sources.architecture import build_change_document
from backend.utils import new_id, truncate

router = APIRouter(tags=["governance"])


def _wrap(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except MemoryNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except PermissionDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": str(exc), "reason": exc.reason},
        ) from exc
    except InvalidTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.post("/memories/{memory_id}/review")
async def review(
    memory_id: str, payload: MemoryActionRequest, s: Services = Depends(get_services)
) -> dict[str, Any]:
    actor = actor_for(payload.actor)
    out = _wrap(
        s.governance.review,
        memory_id,
        actor=actor,
        approve=True,
        note=payload.note,
    )
    return out.to_dict()


@router.post("/memories/{memory_id}/reject")
async def reject(
    memory_id: str, payload: MemoryActionRequest, s: Services = Depends(get_services)
) -> dict[str, Any]:
    actor = actor_for(payload.actor)
    out = _wrap(
        s.governance.review,
        memory_id,
        actor=actor,
        approve=False,
        note=payload.note,
    )
    return out.to_dict()


@router.post("/memories/{memory_id}/promote")
async def promote(
    memory_id: str, payload: PromoteRequest, s: Services = Depends(get_services)
) -> dict[str, Any]:
    actor = actor_for(payload.actor)
    out = _wrap(
        s.governance.promote, memory_id, actor=actor, target=payload.target
    )
    return out.to_dict()


@router.post("/memories/{memory_id}/validate")
async def validate(
    memory_id: str, payload: MemoryActionRequest, s: Services = Depends(get_services)
) -> dict[str, Any]:
    actor = actor_for(payload.actor)
    out = _wrap(s.governance.validate, memory_id, actor=actor, note=payload.note)
    return out.to_dict()


@router.post("/memories/{memory_id}/restrict")
async def restrict(
    memory_id: str, payload: RestrictRequest, s: Services = Depends(get_services)
) -> dict[str, Any]:
    actor = actor_for(payload.actor)
    out = _wrap(
        s.governance.restrict,
        memory_id,
        actor=actor,
        reason=payload.reason,
        access_level=payload.access_level,
    )
    return out.to_dict()


@router.post("/memories/{memory_id}/expire")
async def expire(
    memory_id: str, payload: ExpireRequest, s: Services = Depends(get_services)
) -> dict[str, Any]:
    actor = actor_for(payload.actor)
    out = _wrap(
        s.governance.expire, memory_id, actor=actor, reason=payload.reason, days=payload.days
    )
    return out.to_dict()


# --- architecture change --------------------------------------------------
def register_architecture_change(
    s: Services,
    *,
    id: str | None,
    title: str,
    system: str,
    component: str,
    summary: str,
    invalidates_scope: str | None,
) -> dict[str, Any]:
    """Register a change, move the environment forward, detect contradictions."""
    change_id = id or new_id("arch").upper()
    sysrow = s.db.get_system("sys-payment")
    previous_environment = (
        (sysrow or {}).get("active_component") or "Payment Queue v1"
    )
    change = {
        "id": change_id,
        "title": title,
        "system": system,
        "component": component,
        "effective_at": (utcnow().isoformat()),
        "summary": summary,
        "invalidates_scope": invalidates_scope,
    }
    s.db.upsert_architecture_change(change)

    if sysrow:
        sysrow["active_component"] = component
        if component not in sysrow.get("components", []):
            sysrow["components"] = [*sysrow.get("components", []), component]
        s.db.upsert_system(sysrow)

    s.db.add_audit(
        AuditEvent(
            id=new_id("aud"),
            event_type=AuditEventType.ARCHITECTURE_CHANGE,
            actor="platform-architecture",
            subject=f"{change_id}: {title}",
            detail=(
                f"Environment moved from {previous_environment} to {component}. "
                "Scoped memory is no longer automatically applicable."
            ),
            payload={
                "previous_environment": previous_environment,
                "new_environment": component,
                "invalidates_scope": invalidates_scope,
            },
        )
    )
    s.db.add_audit(
        AuditEvent(
            id=new_id("aud"),
            event_type=AuditEventType.ENVIRONMENT_CHANGED,
            actor="platform-architecture",
            subject=component,
            detail=f"Current environment for the Payment Platform is now {component}.",
        )
    )

    document = build_change_document(change)
    return {
        "change_id": change_id,
        "current_environment": component,
        "previous_environment": previous_environment,
        "contradictions": [],
        "new_memory_ids": [],
        "message": "Change registered.",
        "engine_mode": s.engine.active.mode,
        "engine_simulated": s.engine.active.simulated,
        "_document": document,
    }


async def apply_architecture_change(
    s: Services,
    *,
    id: str | None = None,
    title: str,
    system: str = "Payment Platform",
    component: str,
    summary: str,
    invalidates_scope: str | None = None,
) -> dict[str, Any]:
    """Register a change, retain it, move the environment, detect contradictions.

    This is the whole flow in one place so the API route and the demo control
    cannot drift apart.
    """
    staged = register_architecture_change(
        s,
        id=id,
        title=title,
        system=system,
        component=component,
        summary=summary,
        invalidates_scope=invalidates_scope,
    )
    document = staged.pop("_document")

    ingestion = await s.ingestion.ingest(
        document, owner_actor=actor_for("system"), auto_confirm=True
    )

    candidates = [
        m
        for m in s.db.all_memories()
        if m.scope == (invalidates_scope or previous_component(component))
        and m.is_usable()
    ]
    contradictions = s.contradictions.detect_against_change(
        memories=candidates,
        current_scope=invalidates_scope or previous_component(component),
        new_scope=component,
        change_source_id=id or staged["change_id"],
        change_source_type="architecture_change",
        change_content=summary,
    )
    for c in contradictions:
        s.db.add_contradiction(c)
        s.db.add_audit(
            AuditEvent(
                id=new_id("aud"),
                event_type=AuditEventType.MEMORY_CONTRADICTED,
                actor="platform-architecture",
                subject=c.memory_title,
                memory_id=c.memory_id,
                detail=c.reason,
                payload={"contradiction_id": c.id, "status": "REVIEW_REQUIRED"},
            )
        )
    if contradictions:
        s.db.bump_metric("contradictions_detected", len(contradictions))
        s.db.add_learning_event(
            LearningEvent(
                id=new_id("lev"),
                kind="contradiction_detected",
                message=(
                    f"{len(contradictions)} historical assumption(s) became outdated after "
                    f"{staged['change_id']}."
                ),
                memory_id=contradictions[0].memory_id,
                detail=truncate(contradictions[0].reason, 240),
            )
        )

    return {
        **staged,
        "contradictions": [c.model_dump(mode="json") for c in contradictions],
        "new_memory_ids": [m.id for m in ingestion.memories],
        "message": (
            f"Environment is now {component}. {len(contradictions)} scoped memory/memories "
            "flagged for human review. History is preserved."
        ),
    }


@router.post("/architecture-change", response_model=ArchitectureChangeResponse)
async def architecture_change(
    payload: ArchitectureChangeRequest, s: Services = Depends(get_services)
) -> ArchitectureChangeResponse:
    result = await apply_architecture_change(
        s,
        id=payload.id,
        title=payload.title,
        system=payload.system,
        component=payload.component,
        summary=payload.summary,
        invalidates_scope=payload.invalidates_scope,
    )
    return ArchitectureChangeResponse(**result)


def previous_component(component: str) -> str:
    if component.endswith("v2"):
        return component[:-2] + "v1"
    return component


# --- contradictions -------------------------------------------------------
@router.get("/contradictions")
async def list_contradictions(
    s: Services = Depends(get_services), status_filter: str | None = None
) -> dict[str, Any]:
    items = s.db.list_contradictions(status=status_filter)
    return {
        "contradictions": [c.model_dump(mode="json") for c in items],
        "count": len(items),
        "open": len([c for c in items if c.status == "REVIEW_REQUIRED"]),
        "resolved": len([c for c in items if c.status == "RESOLVED"]),
        "resolution_actions": RESOLUTION_ACTIONS,
    }


@router.post("/contradictions/{contradiction_id}/resolve")
async def resolve_contradiction(
    contradiction_id: str,
    payload: ResolveContradictionRequest,
    s: Services = Depends(get_services),
) -> dict[str, Any]:
    out = _wrap(
        s.governance.resolve_contradiction,
        contradiction_id,
        action=payload.action,
        actor=actor_for(payload.actor),
        note=payload.note,
    )
    return out


@router.get("/governance/summary")
async def governance_summary(s: Services = Depends(get_services)) -> dict[str, Any]:
    return s.governance.governance_summary()


@router.get("/governance/policies")
async def governance_policies(s: Services = Depends(get_services)) -> dict[str, Any]:
    from backend.models.permissions import DEFAULT_POLICIES

    return {
        "policies": {
            str(k): {
                "visibility": str(v.visibility),
                "default_access_level": str(v.default_access_level),
                "default_sensitivity": str(v.default_sensitivity),
                "retention_days": v.retention_days,
                "requires_review": v.requires_review,
                "description": v.description,
            }
            for k, v in DEFAULT_POLICIES.items()
        },
        "promotion_rule": (
            "PERSONAL -> TEAM -> ORGANIZATION is never automatic. Promotion requires an "
            "explicit human action, and ORGANIZATION requires a Knowledge Steward."
        ),
        "retention_rule": (
            "Expiry marks a memory stale and removes it from guidance. Content is never "
            "deleted."
        ),
    }


__all__ = ["previous_component", "register_architecture_change", "router"]
