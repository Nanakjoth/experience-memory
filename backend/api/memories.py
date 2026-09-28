"""Memory Center: searchable explorer, detail, history, evidence."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.actors import actor_for
from backend.memory.governance import MemoryNotFound
from backend.memory.provenance import provenance_view
from backend.models.memory import LIFECYCLE_TRANSITIONS, MemoryStatus, Visibility
from backend.services import Services, get_services
from backend.utils import truncate

router = APIRouter(tags=["memories"])


@router.get("/memories")
async def list_memories(
    s: Services = Depends(get_services),
    type: str | None = Query(None),
    scope: str | None = Query(None),
    source: str | None = Query(None, description="source_type"),
    status_filter: str | None = Query(None, alias="status"),
    visibility: str | None = Query(None),
    owner: str | None = Query(None),
    entity: str | None = Query(None),
    system: str | None = Query(None),
    min_confidence: float | None = Query(None, ge=0, le=1),
    min_evidence: int | None = Query(None, ge=0),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    q: str | None = Query(None),
    actor: str = Query("maya"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    who = actor_for(actor)
    items, total = s.db.list_memories(
        type_=type,
        scope=scope,
        source_type=source,
        status=status_filter,
        visibility=visibility,
        owner=owner,
        entity=entity,
        system=system,
        min_confidence=min_confidence,
        min_evidence=min_evidence,
        date_from=date_from,
        date_to=date_to,
        search=q,
        limit=limit,
        offset=offset,
    )
    visible, withheld = s.resolver.filter_readable(who, items)
    return {
        "total": total,
        "count": len(visible),
        "offset": offset,
        "limit": limit,
        "withheld": withheld,
        "items": [_card(m) for m in visible],
        "filters": {
            "types": sorted({str(m.type) for m in s.db.all_memories()}),
            "scopes": sorted({m.scope for m in s.db.all_memories()}),
            "sources": sorted({m.source_type for m in s.db.all_memories()}),
            "statuses": sorted({str(m.status) for m in s.db.all_memories()}),
            "entities": sorted({e for m in s.db.all_memories() for e in m.related_entities})[:60],
            "visibilities": sorted({str(m.visibility) for m in s.db.all_memories()}),
        },
    }


def _card(m) -> dict[str, Any]:
    return {
        "id": m.id,
        "type": str(m.type),
        "title": m.title,
        "summary": m.summary or truncate(m.content, 160),
        "content": m.content,
        "source_type": m.source_type,
        "source_id": m.source_id,
        "source_name": m.source_name,
        "scope": m.scope,
        "owner": m.owner,
        "domain": m.domain,
        "purpose": m.purpose,
        "evidence_count": m.evidence_count,
        "confidence": m.confidence,
        "status": str(m.status),
        "visibility": str(m.visibility),
        "access_level": str(m.access_level),
        "sensitivity": str(m.sensitivity),
        "last_validated_at": m.last_validated_at.isoformat() if m.last_validated_at else None,
        "observed_at": m.observed_at.isoformat() if m.observed_at else None,
        "created_at": m.created_at.isoformat(),
        "expiry_at": m.expiry_at.isoformat() if m.expiry_at else None,
        "related_entities": m.related_entities,
        "hindsight_fact_id": m.hindsight_fact_id,
        "version": m.version,
        "excluded_scopes": (m.extra or {}).get("excluded_scopes", []),
        "tags": m.tags,
    }


@router.get("/memories/{memory_id}")
async def get_memory(
    memory_id: str,
    s: Services = Depends(get_services),
    actor: str = Query("maya"),
) -> dict[str, Any]:
    """Everything the Memory Center detail panel needs, in one call."""
    mem = s.db.get_memory(memory_id)
    if mem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory {memory_id} not found."
        )
    s.resolver.assert_can_read(actor_for(actor), mem)
    open_items = [c for c in s.db.list_contradictions() if c.memory_id == mem.id]
    confidence = s.retrieval.confidence.evaluate(
        mem,
        current_scope=s.retrieval.current_scope(),
        contradiction_open=bool(
            [c for c in open_items if c.status == "REVIEW_REQUIRED"]
        ),
    )
    return {
        "memory": _card(mem),
        "provenance": provenance_view(mem).to_dict(),
        "gate": mem.gate.model_dump(mode="json") if mem.gate else None,
        "lens": s.retrieval.lens_for_memory(mem).to_dict(),
        "excluded_scopes": (mem.extra or {}).get("excluded_scopes", []),
        "evidence": [
            {
                "evidence_type": l.evidence_type,
                "evidence_id": l.evidence_id,
                "label": l.evidence_label,
                "polarity": l.polarity,
                "detail": l.detail,
                "created_at": l.created_at,
            }
            for l in s.db.evidence_for(mem.id)
        ],
        "events": [e.model_dump(mode="json") for e in s.db.memory_history(mem.id)],
        "confidence": confidence.to_dict(),
        "previous_versions": (mem.extra or {}).get("previous_versions", []),
        "contradictions": [c.model_dump(mode="json") for c in open_items],
        "promotable": _promotable(s, actor_for(actor), mem),
        "lifecycle": _lifecycle(mem),
    }


#: UI action -> the lifecycle status it attempts to reach.
LIFECYCLE_ACTIONS: dict[str, MemoryStatus] = {
    "review": MemoryStatus.CONFIRMED,
    "reject": MemoryStatus.REJECTED,
    "validate": MemoryStatus.REVALIDATED,
    "restrict": None,  # scope restriction, status intentionally unchanged
    "expire": MemoryStatus.STALE,
}


def _lifecycle(mem) -> dict[str, Any]:
    """Which lifecycle actions are legal from the current status.

    The Memory Center renders exactly these, so the UI never offers a
    transition the lifecycle rules would reject with 409.
    """
    current = MemoryStatus(mem.status)
    reachable = LIFECYCLE_TRANSITIONS.get(current, set())
    actions = []
    for action, target in LIFECYCLE_ACTIONS.items():
        if target is None:
            allowed, reason = True, "Narrows the applicable scope. History is kept."
        elif target in reachable:
            allowed, reason = True, f"{current} → {target} is a legal transition."
        else:
            allowed = False
            reason = (
                f"{current} → {target} is not a legal transition. "
                f"Allowed from {current}: "
                + (", ".join(sorted(str(x) for x in reachable)) or "none")
            )
        actions.append(
            {"action": action, "target": str(target) if target else None, "allowed": allowed, "reason": reason}
        )
    return {"status": str(current), "allowed_transitions": sorted(str(x) for x in reachable), "actions": actions}


def _promotable(s: Services, who, mem) -> dict[str, Any]:
    """Which promotions this actor may perform, and why the others are blocked."""
    options = []
    for target in (Visibility.TEAM, Visibility.ORGANIZATION):
        allowed, reason = s.resolver.can_promote(who, mem, target)
        options.append({"target": str(target), "allowed": allowed, "reason": reason})
    return {"by": who.id, "options": options}


@router.get("/memories/{memory_id}/history")
async def memory_history(
    memory_id: str, s: Services = Depends(get_services)
) -> dict[str, Any]:
    mem = s.db.get_memory(memory_id)
    if mem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory {memory_id} not found."
        )
    return {
        "memory_id": memory_id,
        "status": str(mem.status),
        "version": mem.version,
        "events": [e.model_dump(mode="json") for e in s.db.memory_history(memory_id)],
    }


@router.get("/memories/{memory_id}/evidence")
async def memory_evidence(
    memory_id: str, s: Services = Depends(get_services)
) -> dict[str, Any]:
    mem = s.db.get_memory(memory_id)
    if mem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory {memory_id} not found."
        )
    links = s.db.evidence_for(memory_id)
    incidents: list[dict[str, Any]] = []
    for link in links:
        if link.evidence_type != "incident":
            continue
        inc = s.db.get_incident(link.evidence_id)
        if inc:
            incidents.append(
                {
                    "id": inc["id"],
                    "title": inc["title"],
                    "severity": inc["severity"],
                    "queue_depth": inc.get("queue_depth"),
                    "action": inc["action"],
                    "outcome": inc["outcome"],
                    "engineer": inc["engineer"],
                    "duplicate_processing": inc.get("duplicate_processing", False),
                    "opened_at": inc["opened_at"],
                    "resolved_at": inc.get("resolved_at"),
                    "polarity": link.polarity,
                }
            )
    return {
        "memory_id": memory_id,
        "evidence_count": mem.evidence_count,
        "links": [l.model_dump(mode="json") for l in links],
        "incidents": incidents,
    }


@router.get("/memories/{memory_id}/lens")
async def memory_lens(
    memory_id: str, s: Services = Depends(get_services)
) -> dict[str, Any]:
    mem = s.db.get_memory(memory_id)
    if mem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory {memory_id} not found."
        )
    return {"lens": s.retrieval.lens_for_memory(mem).to_dict()}


__all__ = ["MemoryNotFound", "router"]
