"""Capture Experience endpoint.

The conversational capture screen posts here. The raw interview is retained into
Hindsight, then the Memory Gate decides what may become an application memory.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.actors import DEMO_ACTORS
from backend.api.schemas import CaptureRequest, CaptureResponse
from backend.models.audit import AuditEvent, AuditEventType
from backend.models.memory import Visibility, utcnow
from backend.models.permissions import Actor
from backend.services import Services, get_services
from backend.sources.expert_interview import CAPTURE_PROMPTS, ExpertInterviewSource
from backend.utils import new_id, stable_id

router = APIRouter(tags=["capture"])


@router.get("/capture/prompts")
async def prompts() -> dict[str, Any]:
    """The conversation script. Answers are free text, never a giant form."""
    return {
        "heading": "Capture what never made it into the documentation.",
        "prompts": CAPTURE_PROMPTS,
        "note": (
            "Answer naturally. MemoryOS retains the conversation into Hindsight and "
            "extracts EXPERIENCE, LESSON, EXCEPTION, RELATIONSHIP and FACT items."
        ),
        "visibility_note": (
            "Captured knowledge starts PERSONAL. It is never organizational knowledge "
            "until a human promotes it."
        ),
    }


@router.post("/capture", response_model=CaptureResponse)
async def capture(
    payload: CaptureRequest, s: Services = Depends(get_services)
) -> CaptureResponse:
    if not payload.turns and not (payload.free_text or "").strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nothing was captured. Answer at least one prompt.",
        )

    source_id = payload.source_id or stable_id(
        "expert", payload.expert, payload.scope, str(len(payload.turns))
    )
    lines: list[str] = [
        f"Expert interview. {payload.expert}, {payload.role}, {payload.team}.",
        f"System: {payload.system}. Scope discussed: {payload.scope}.",
        f"Captured at: {utcnow().isoformat()}.",
        "",
    ]
    for turn in payload.turns:
        lines.append(f"MemoryOS: {turn.prompt}")
        lines.append(f"{payload.expert}: {turn.answer.strip()}")
    if payload.free_text:
        lines.append(f"{payload.expert} (additional context): {payload.free_text.strip()}")

    document = ExpertInterviewSource().documents()[0]
    document.source_id = source_id
    document.source_name = f"{payload.expert} expert interview"
    document.title = f"{payload.expert} — {payload.system} capture"
    document.document_id = f"doc-{source_id}"
    document.content = "\n".join(lines)
    document.context = "Conversational expert capture"
    document.scope = payload.scope
    document.owner = payload.expert
    document.team = payload.team
    document.domain = payload.system.split()[0].lower()
    document.purpose = "Preserve undocumented operational judgment while it is still available."
    document.observed_at = utcnow()
    document.captured_at = utcnow()
    document.visibility = payload.visibility
    # A live capture cannot ship pre-authored claims: it is processed by
    # Hindsight's own extraction, and MemoryOS records the resulting facts.
    document.claims = [
        _claim_from_turn(turn, payload, source_id) for turn in payload.turns
    ]

    actor = DEMO_ACTORS.get(payload.expert.lower(), DEMO_ACTORS["arun"])
    actor = Actor(
        id=actor.id, display_name=payload.expert, role=payload.role, team=payload.team
    )
    result = await s.ingestion.ingest(document, owner_actor=actor, auto_confirm=False)

    s.db.add_audit(
        AuditEvent(
            id=new_id("aud"),
            event_type=AuditEventType.MEMORY_CAPTURED,
            actor=payload.expert,
            actor_role=payload.role,
            subject=document.title,
            detail=(
                f"Captured {len(payload.turns)} turn(s). {len(result.memories)} memory "
                f"item(s) approved by the Memory Gate, {len(result.rejected)} rejected."
            ),
            payload={"source_id": source_id, "scope": payload.scope},
        )
    )

    if payload.auto_promote:
        steward = DEMO_ACTORS["steward"]
        for mem in result.memories:
            s.governance.promote(
                mem.id,
                actor=steward,
                target=Visibility.ORGANIZATION,
                note="Auto-promoted by explicit request from the capture screen.",
            )

    return CaptureResponse(
        source_id=source_id,
        retained=result.retained,
        engine_mode=result.engine_mode,
        engine_simulated=result.engine_simulated,
        memories=[m.model_dump(mode="json") for m in result.memories],
        rejected=result.rejected,
        hindsight_fact_ids=result.hindsight_fact_ids,
        duration_ms=result.duration_ms,
    )


def _claim_from_turn(turn, payload: CaptureRequest, source_id: str):
    """Build one candidate memory per answered turn.

    Memory type is inferred from the answer's shape: a story is an EXPERIENCE, a
    prohibition is an EXCEPTION or LESSON, a 'who' answer is a RELATIONSHIP.
    """
    from backend.models.memory import MemoryType
    from backend.sources.base import ExtractedClaim

    answer = turn.answer.strip()
    lowered = answer.lower()
    prompt = turn.prompt.lower()

    if "not do" in prompt or "never" in lowered[:40] or "do not" in lowered[:40]:
        mtype = MemoryType.EXCEPTION
    elif "who" in prompt or "escalate" in prompt:
        mtype = MemoryType.RELATIONSHIP
    elif "check first" in prompt or "what should" in prompt or "procedure" in prompt:
        mtype = MemoryType.LESSON
    elif "failed" in prompt or "went wrong" in prompt or "incident" in lowered:
        mtype = MemoryType.EXPERIENCE
    else:
        mtype = MemoryType.FACT

    title = f"{payload.expert}: {turn.prompt.rstrip('?')}"
    return ExtractedClaim(
        type=mtype,
        title=title,
        content=answer,
        summary=answer[:160],
        scope=payload.scope,
        owner=payload.expert,
        domain=payload.system.split()[0].lower(),
        purpose="Preserve undocumented operational judgment.",
        visibility=Visibility(payload.visibility),
        observed_at=utcnow(),
    )


__all__ = ["router"]
