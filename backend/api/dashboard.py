"""Dashboard + health endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends

from backend.api.schemas import HealthResponse
from backend.models.memory import MemoryStatus, Visibility, utcnow
from backend.seed.novatech import COMPANY, SYNTHETIC_BANNER
from backend.services import Services, get_services
from backend.utils import truncate

router = APIRouter(tags=["dashboard"])

# Every number on the dashboard is demo data and must say so.
SYNTHETIC_LABEL = "Synthetic prototype metric"


def build_dashboard(s: Services) -> dict[str, Any]:
    """Every number here is computed from real application state."""
    db = s.db
    memories = db.all_memories()
    metrics = db.metrics()
    contradictions = db.list_contradictions()
    open_contradictions = [c for c in contradictions if c.status == "REVIEW_REQUIRED"]

    captured = len(memories)
    validated = [
        m
        for m in memories
        if str(m.status)
        in {str(MemoryStatus.ACTIVE), str(MemoryStatus.REVALIDATED), str(MemoryStatus.SUPPORTED)}
    ]
    stale = [m for m in memories if str(m.status) == str(MemoryStatus.STALE)]
    personal_only = [m for m in memories if str(m.visibility) == str(Visibility.PERSONAL)]
    at_risk = s.governance.knowledge_at_risk()

    return {
        "statement": "Your organization has a memory.",
        "synthetic": True,
        "synthetic_banner": SYNTHETIC_BANNER,
        "synthetic_label": SYNTHETIC_LABEL,
        "generated_at": utcnow().isoformat(),
        "metrics": {
            "critical_knowledge_dependencies": {
                "label": "Critical knowledge dependencies",
                "value": len([r for r in at_risk if r["risk"] == "High"]),
                "detail": "Systems whose critical knowledge still depends on one person.",
                "synthetic": True,
                "synthetic_label": SYNTHETIC_LABEL,
            },
            "captured_knowledge": {
                "label": "Captured knowledge",
                "value": captured,
                "detail": f"{len(db.list_incidents())} incident records, {len(memories)} memory items.",
                "synthetic": True,
                "synthetic_label": SYNTHETIC_LABEL,
            },
            "validated_memories": {
                "label": "Validated memories",
                "value": len(validated),
                "detail": "Active, re-validated or outcome-supported.",
                "synthetic": True,
                "synthetic_label": SYNTHETIC_LABEL,
            },
            "stale_memories": {
                "label": "Stale memories",
                "value": len(stale),
                "detail": "Preserved for history, not surfaced as guidance.",
                "synthetic": True,
                "synthetic_label": SYNTHETIC_LABEL,
            },
            "contradictions": {
                "label": "Contradictions",
                "value": len(open_contradictions),
                "detail": "Open items awaiting human review.",
                "synthetic": True,
                "synthetic_label": SYNTHETIC_LABEL,
            },
            "learning_events": {
                "label": "Recent learning events",
                "value": len(db.list_learning_events(limit=500)),
                "detail": "Real events recorded by the application.",
                "synthetic": True,
                "synthetic_label": SYNTHETIC_LABEL,
            },
        },
        "recent_intelligence": [
            {
                "id": e.id,
                "at": e.at.isoformat(),
                "kind": e.kind,
                "message": e.message,
                "detail": e.detail,
                "synthetic": e.synthetic,
            }
            for e in db.list_learning_events(limit=12)
        ],
        "event_counters": {
            "memories_created": metrics.get("memories_created", 0),
            "memories_retrieved": metrics.get("memories_retrieved", 0),
            "memories_used": metrics.get("memories_used", 0),
            "outcomes_recorded": metrics.get("outcomes_recorded", 0),
            "contradictions_detected": metrics.get("contradictions_detected", 0),
            "memories_updated": metrics.get("memories_updated", 0),
            "memories_revalidated": metrics.get("memories_revalidated", 0),
            "knowledge_dependencies": len([r for r in at_risk if r["risk"] == "High"]),
            "note": "Counters are incremented by real application events.",
        },
        "knowledge_at_risk": at_risk,
        "continuity": s.governance.knowledge_continuity(),
        "engine": s.describe(),
        "health_counts": {
            "memories": captured,
            "personal_only": len(personal_only),
            "organizational": len([m for m in memories if str(m.visibility) == "ORGANIZATION"]),
            "incidents": len(db.list_incidents()),
            "audit_events": len(db.list_audit(limit=10_000)),
            "open_contradictions": len(open_contradictions),
        },
    }


@router.get("/health", response_model=HealthResponse)
async def health(s: Services = Depends(get_services)) -> HealthResponse:
    engine_health = await s.engine.health()
    status = s.engine.status()
    db = s.db
    return HealthResponse(
        status="ok" if engine_health.available else "degraded",
        app=s.settings.app_name,
        version="1.0.0",
        memory_engine="hindsight",
        bank_id=status.bank_id,
        engine_mode=engine_health.mode,
        engine_label=engine_health.label,
        engine_simulated=engine_health.simulated,
        degraded_reason=status.reason,
        hindsight_base_url=s.settings.hindsight_base_url,
        memory_count=len(db.all_memories()),
        incident_count=len(db.list_incidents()),
        config=s.settings.public_dict(),
        at=utcnow(),
    )


@router.get("/dashboard")
async def dashboard(s: Services = Depends(get_services)) -> dict[str, Any]:
    return build_dashboard(s)


@router.get("/catalogue")
async def catalogue(s: Services = Depends(get_services)) -> dict[str, Any]:
    """Reference data so the UI can render entities and choices."""
    return {
        "company": COMPANY["name"],
        "synthetic_banner": SYNTHETIC_BANNER,
        "employees": s.db.list_employees(),
        "systems": s.db.list_systems(),
        "incidents": [
            {
                "id": i["id"],
                "title": i["title"],
                "system": i["system"],
                "service": i["service"],
                "component": i["component"],
                "severity": i["severity"],
                "queue_depth": i.get("queue_depth"),
                "action": i["action"],
                "outcome": i["outcome"],
                "engineer": i["engineer"],
                "duplicate_processing": i.get("duplicate_processing", False),
                "opened_at": i["opened_at"],
                "resolved_at": i.get("resolved_at"),
            }
            for i in s.db.list_incidents()
        ],
        "architecture_changes": s.db.list_architecture_changes(),
        "memory_types": [
            "FACT", "EXPERIENCE", "LESSON", "OBSERVATION", "DECISION",
            "EXCEPTION", "RELATIONSHIP", "COMMITMENT", "HYPOTHESIS",
            "CORRECTION", "EVENT",
        ],
        "scopes": sorted({m.scope for m in s.db.all_memories()}),
        "generated_at": datetime.now().astimezone().isoformat(),
    }


__all__ = ["SYNTHETIC_LABEL", "build_dashboard", "router", "truncate"]
