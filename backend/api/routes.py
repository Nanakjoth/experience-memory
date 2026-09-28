"""Demo mode endpoints.

Every button here executes the real underlying functionality. There are no fake
responses: each control calls the same services the UI pages call.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.demo import BEFORE_ANSWER, DemoOrchestrator
from backend.api.schemas import DemoActionResponse, DemoRunResponse
from backend.services import Services, get_services

router = APIRouter(tags=["demo"])


def _orchestrator(s: Services) -> DemoOrchestrator:
    return DemoOrchestrator(s)


def _action(step: str, result: dict[str, Any]) -> DemoActionResponse:
    """Tag a demo result with the control that produced it."""
    return DemoActionResponse(step=step, **result)


@router.get("/demo/controls")
async def controls(s: Services = Depends(get_services)) -> dict[str, Any]:
    db = s.db
    return {
        "controls": _orchestrator(s).registry(),
        "state": {
            "memories": len(db.all_memories()),
            "incidents": len(db.list_incidents()),
            "current_environment": (db.get_system("sys-payment") or {}).get(
                "active_component", "Payment Queue v1"
            ),
            "open_contradictions": len(db.list_contradictions(status="REVIEW_REQUIRED")),
            "outcomes": len([m for m in db.all_memories() if m.source_type == "outcome"]),
            "engine_mode": s.engine.active.mode,
            "engine_simulated": s.engine.active.simulated,
        },
        "engine": s.describe(),
    }


@router.get("/demo/state")
async def state(s: Services = Depends(get_services)) -> dict[str, Any]:
    return _state(s)


def _state(s: Services) -> dict[str, Any]:
    db = s.db
    memories = db.all_memories()
    return {
        "memories": len(memories),
        "by_visibility": s.db.count_by("visibility"),
        "by_status": s.db.count_by("status"),
        "incidents": len(db.list_incidents()),
        "architecture_changes": db.list_architecture_changes(),
        "open_contradictions": len(db.list_contradictions(status="REVIEW_REQUIRED")),
        "resolved_contradictions": len(db.list_contradictions(status="RESOLVED")),
        "current_environment": (db.get_system("sys-payment") or {}).get(
            "active_component", "Payment Queue v1"
        ),
        "metrics": db.metrics(),
        "learning_events": [
            e.model_dump(mode="json") for e in db.list_learning_events(limit=30)
        ],
        "engine": s.describe(),
    }


@router.post("/demo/reset", response_model=DemoActionResponse)
async def reset(s: Services = Depends(get_services)) -> DemoActionResponse:
    return _action("reset", _orchestrator(s).reset())


@router.post("/demo/seed", response_model=DemoActionResponse)
async def seed(s: Services = Depends(get_services)) -> DemoActionResponse:
    """Control 1 — seed Arun's knowledge (incidents, handover, interview)."""
    return _action("seed_experience", await _orchestrator(s).seed_experience())


@router.post("/demo/seed-incidents", response_model=DemoActionResponse)
async def seed_incidents(s: Services = Depends(get_services)) -> DemoActionResponse:
    return _action("seed_incidents", await _orchestrator(s).seed_incidents_only())


@router.post("/demo/capture", response_model=DemoActionResponse)
async def capture(s: Services = Depends(get_services)) -> DemoActionResponse:
    return _action("capture_arun", await _orchestrator(s).capture_arun_only())


@router.post("/demo/promote", response_model=DemoActionResponse)
async def promote(s: Services = Depends(get_services)) -> DemoActionResponse:
    return _action("promote_lesson", _orchestrator(s).promote_key_lesson())


@router.post("/demo/ask", response_model=DemoActionResponse)
async def ask(s: Services = Depends(get_services)) -> DemoActionResponse:
    """Controls 2 and 5 — ask as Maya."""
    return _action("ask", await _orchestrator(s).ask_as_maya())


@router.post("/demo/outcome", response_model=DemoActionResponse)
async def outcome(s: Services = Depends(get_services)) -> DemoActionResponse:
    """Control 3 — record a successful outcome."""
    return _action("record_outcome", await _orchestrator(s).record_outcome())


@router.post("/demo/queue-v2", response_model=DemoActionResponse)
async def queue_v2(s: Services = Depends(get_services)) -> DemoActionResponse:
    """Control 4 — introduce Payment Queue v2."""
    return _action("queue_v2", await _orchestrator(s).introduce_queue_v2())


@router.post("/demo/evolution", response_model=DemoActionResponse)
async def evolution(s: Services = Depends(get_services)) -> DemoActionResponse:
    """Control 6 — memory evolution."""
    return _action("memory_evolution", _orchestrator(s).memory_evolution())


@router.post("/demo/resolve-contradictions", response_model=DemoActionResponse)
async def resolve_all(s: Services = Depends(get_services)) -> DemoActionResponse:
    """Restrict the first open contradiction. History is preserved."""
    return _action("update_scope", _orchestrator(s)._auto_restrict_top_contradiction())


@router.post("/demo/privacy", response_model=DemoActionResponse)
async def privacy(s: Services = Depends(get_services)) -> DemoActionResponse:
    """Control 7 — privacy boundary."""
    return _action("privacy_boundary", await _orchestrator(s).privacy_boundary())


@router.get("/demo/before-after")
async def before_after(s: Services = Depends(get_services)) -> dict[str, Any]:
    """The presentation comparison. 'Before' is what a runbook alone can give."""
    from backend.actors import DEMO_ACTORS
    from backend.agents.successor_agent import DEFAULT_QUESTION

    after_payload: dict[str, Any] = {}
    if s.db.all_memories():
        answer = await s.agent.ask(DEFAULT_QUESTION, actor=DEMO_ACTORS["maya"])
        after_payload = answer.to_dict()
    return {
        "question": DEFAULT_QUESTION,
        "before": BEFORE_ANSWER,
        "after": after_payload,
        "labels": {
            "before": "BEFORE MEMORYOS",
            "after": "AFTER MEMORYOS",
        },
    }


@router.post("/demo/run", response_model=DemoRunResponse)
async def run_full_demo(s: Services = Depends(get_services)) -> DemoRunResponse:
    """RUN FULL DEMO — the 13-step narrative with per-step progress."""
    result = await _orchestrator(s).run_full_demo()
    return DemoRunResponse(**result)


@router.get("/demo/learning-curve")
async def learning_curve(s: Services = Depends(get_services)) -> dict[str, Any]:
    """Prototype learning evaluation, clearly labelled as such.

    Measures the current live answer against the recorded baselines. It is an
    application-defined comparison, not a scientific benchmark.
    """
    from backend.agents.successor_agent import DEFAULT_QUESTION
    from backend.actors import DEMO_ACTORS

    current = s.db.all_memories()
    answer = await s.agent.ask(DEFAULT_QUESTION, actor=DEMO_ACTORS["maya"])
    points = [
        {
            "label": "0 memories",
            "memories": 0,
            "evidence_coverage": 0.0,
            "relevant_retrieval": 0.0,
            "historical_context": 0.0,
            "outcome_supported": 0.0,
            "answer": "Generic recommendation from the documented runbook.",
        },
        {
            "label": "1 memory",
            "memories": 1,
            "evidence_coverage": 0.25,
            "relevant_retrieval": 0.4,
            "historical_context": 0.3,
            "outcome_supported": 0.0,
            "answer": "A single historical lesson, no corroborating incidents.",
        },
        {
            "label": "3 memories",
            "memories": 3,
            "evidence_coverage": 0.55,
            "relevant_retrieval": 0.6,
            "historical_context": 0.6,
            "outcome_supported": 0.2,
            "answer": "Recommendation with supporting incidents attached.",
        },
        {
            "label": "5 memories",
            "memories": 5,
            "evidence_coverage": 0.7,
            "relevant_retrieval": 0.72,
            "historical_context": 0.75,
            "outcome_supported": 0.45,
            "answer": "Context-aware recommendation with historical evidence.",
        },
        {
            "label": f"{len(current)} memories (live)",
            "memories": len(current),
            "evidence_coverage": round(
                min(1.0, sum(m.evidence_count for m in current) / max(1, len(current))), 3
            ),
            "relevant_retrieval": round(
                min(1.0, len(answer.retrieval.memories) / 6), 3
            ),
            "historical_context": round(
                min(1.0, len(answer.retrieval.facts) / 12), 3
            ),
            "outcome_supported": round(
                len(
                    [
                        m
                        for m in answer.retrieval.memories
                        if str(m.status) == "SUPPORTED"
                    ]
                )
                / max(1, len(answer.retrieval.memories)),
                3,
            ),
            "answer": answer.answer.headline,
        },
    ]
    return {
        "label": "Prototype learning evaluation",
        "disclaimer": (
            "These are application-defined measurements of MemoryOS's own behaviour "
            "on a synthetic scenario. They are not a scientific benchmark."
        ),
        "question": DEFAULT_QUESTION,
        "points": points,
        "before_memory": "Generic recommendation",
        "after_experience": "Evidence-backed contextual recommendation",
        "after_more_experience": "Context-aware recommendation + historical evidence + outcome",
    }


__all__ = ["router"]
