"""Outcome recording.

The loop closer. The outcome is retained into Hindsight as a new observation and
linked as evidence to the memory that produced the recommendation, which raises
that memory's internal confidence.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.actors import actor_for
from backend.api.schemas import OutcomeRequest, OutcomeResponse
from backend.memory.confidence import band_for
from backend.models.audit import AuditEvent, AuditEventType
from backend.models.memory import LearningEvent, MemoryEvent, MemoryStatus, utcnow
from backend.services import Services, get_services
from backend.sources.outcomes import build_outcome_document
from backend.utils import new_id, stable_id, tokenize, truncate

router = APIRouter(tags=["outcomes"])

# A naive "does the text contain a success word" check gets this product wrong:
# "Duplicate processing did not recur" is a *success* that mentions a failure
# word. So cues are matched with a small negation window, and the caller may
# always state the result explicitly.
POSITIVE_CUES = (
    "succeeded",
    "succeeds",
    "success",
    "successful",
    "worked",
    "works",
    "resolved",
    "resolved without",
    "stable",
    "healthy",
    "clean",
    "no errors",
    "no incidents",
    "without duplicate",
    "no duplicate",
    "back to normal",
    "completed",
    "passed",
    "recovered",
    "fixed",
    "within sla",
)
NEGATIVE_CUES = (
    "failed",
    "failure",
    "error",
    "errors",
    "outage",
    "broke",
    "broken",
    "incident",
    "duplicate",
    "duplicated",
    "rollback",
    "rolled back",
    "timeout",
    "timed out",
    "escalated",
    "paged",
    "complaint",
    "complaints",
    "complained",
    "delayed",
    "delay",
    "delays",
    "data loss",
    "corrupt",
    "wrong",
    "regression",
    "delayed",
    "backlog",
    "stuck",
    "crash",
    "crashed",
    "blocker",
    "workaround",
    "did not work",
    "went wrong",
    "went badly",
)
NEGATION_CUES = (
    "not",
    "no",
    "never",
    "without",
    "nor",
    "hardly",
    "barely",
    "stopped",
    "avoided",
    "prevented",
    "free of",
)
NEGATION_WINDOW = 5
# "duplicate processing did not recur" puts the negation *after* the cue.
NEGATION_WINDOW_AFTER = 3


def _is_negated(
    tokens: list[str], i: int, width: int, *, allow_after: bool = True
) -> bool:
    before = tokens[max(0, i - NEGATION_WINDOW) : i]
    if any(t in NEGATION_CUES for t in before):
        return True
    if not allow_after:
        return False
    after = tokens[i + width : i + width + NEGATION_WINDOW_AFTER]
    return any(t in NEGATION_CUES for t in after)


def _cue_score(text: str, cues: tuple[str, ...], *, allow_after: bool = True) -> tuple[int, list[str]]:
    """Count cues that are not inside a negation window."""
    tokens = tokenize(text)
    score = 0
    hits: list[str] = []
    for cue in cues:
        needle = tokenize(cue)
        if not needle:
            continue
        for i in range(len(tokens) - len(needle) + 1):
            if tokens[i : i + len(needle)] != needle:
                continue
            if _is_negated(tokens, i, len(needle), allow_after=allow_after):
                continue
            score += 1
            hits.append(cue)
    return score, hits


def classify_outcome(result: str, *, stated: bool | None = None) -> dict[str, Any]:
    """Decide whether an outcome succeeded, and always explain the decision.

    `stated` wins when the human told us the result directly. Otherwise the
    classifier is used and the rationale is returned so the UI can show it.
    """
    positive, positive_hits = _cue_score(result, POSITIVE_CUES, allow_after=False)
    negative, negative_hits = _cue_score(result, NEGATIVE_CUES)
    if stated is True:
        return {
            "successful": True,
            "source": "stated_by_reporter",
            "rationale": "The reporter marked this outcome as successful.",
            "cues": positive_hits,
        }
    if stated is False:
        return {
            "successful": False,
            "source": "stated_by_reporter",
            "rationale": "The reporter marked this outcome as unsuccessful.",
            "cues": negative_hits,
        }
    if positive == negative:
        return {
            "successful": None,
            "source": "unclassified",
            "rationale": (
                "The result text was not classifiable as a success or a failure, so "
                "no memory was reinforced and nothing was contradicted."
            ),
            "cues": positive_hits + negative_hits,
        }
    successful = positive > negative
    return {
        "successful": successful,
        "source": "derived_from_text",
        "rationale": (
            f"Classified as {'success' if successful else 'failure'} from the result "
            f"text (success cues: {positive_hits or 'none'}; failure cues: "
            f"{negative_hits or 'none'})."
        ),
        "cues": (positive_hits if successful else negative_hits),
    }


def _successful(result: str) -> bool:
    return bool(classify_outcome(result)["successful"])


OUTCOME_LINK_MIN_OVERLAP = 0.12
OUTCOME_LINK_MAX = 3


def _recommendation_targets(
    s: Services,
    *,
    scope: str,
    recommendation: str,
    question: str,
) -> list[Any]:
    """The memories an outcome should be attributed to.

    An outcome strengthens the specific memory that produced the recommendation,
    not every lesson that happens to share a scope. Candidates are ranked by
    content overlap with the recommendation, falling back to the question.
    """
    from backend.utils import content_tokens

    candidates = [
        m
        for m in s.db.all_memories()
        if m.scope == scope
        and m.is_usable()
        and m.type in {"LESSON", "EXPERIENCE"}
    ]
    if not candidates:
        return []

    probe = set(content_tokens(recommendation)) or set(content_tokens(question))
    if not probe:
        candidates.sort(key=lambda m: m.created_at, reverse=True)
        return candidates[:1]

    scored: list[tuple[float, Any]] = []
    for mem in candidates:
        haystack = set(content_tokens(f"{mem.title} {mem.content} {mem.scope}"))
        haystack |= {
            t for e in mem.related_entities for t in content_tokens(e)
        }
        overlap = len(probe & haystack) / max(1, len(probe))
        if overlap >= OUTCOME_LINK_MIN_OVERLAP:
            scored.append((overlap, mem))
    scored.sort(key=lambda pair: (pair[0], pair[1].created_at), reverse=True)
    return [mem for _score, mem in scored[:OUTCOME_LINK_MAX]]


async def record_outcome(
    s: Services,
    *,
    question: str,
    recommendation: str,
    actual_action: str,
    result: str,
    notes: str,
    queue_depth: float | None,
    scope: str,
    actor: str,
    outcome_id: str | None,
    stated_result: bool | None = None,
) -> dict[str, Any]:
    if not (actual_action or "").strip() or not (result or "").strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Both an actual action and a result are required.",
        )
    if queue_depth is not None and not (0 <= queue_depth <= 100):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Queue depth must be a percentage between 0 and 100.",
        )

    who = actor_for(actor)
    verdict = classify_outcome(result, stated=stated_result)
    successful = verdict["successful"]
    oid = outcome_id or stable_id("out", question, actual_action, result)
    document = build_outcome_document(
        outcome_id=oid,
        question=question,
        recommendation=recommendation,
        actual_action=actual_action,
        result=result,
        notes=notes,
        actor=who.display_name,
        scope=scope,
        queue_depth=queue_depth,
    )
    result_obj = await s.ingestion.ingest(document, owner_actor=who, auto_confirm=True)
    if not result_obj.memories:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The outcome could not be stored. Check the memory engine status.",
        )
    memory = result_obj.memories[0]

    # Link the outcome as evidence on the memory that actually produced the
    # recommendation, so this observation strengthens or challenges that one
    # memory rather than every lesson in the scope.
    linked: list[str] = []
    link_report: list[dict[str, Any]] = []
    if successful is not None:
        for mem in _recommendation_targets(
            s, scope=scope, recommendation=recommendation, question=question
        ):
            from backend.models.memory import EvidenceLink

            s.db.add_evidence(
                EvidenceLink(
                    memory_id=mem.id,
                    evidence_type="outcome",
                    evidence_id=oid,
                    evidence_label=f"Outcome {oid}",
                    polarity="supports" if successful else "contradicts",
                    detail=truncate(result, 160),
                )
            )
            linked.append(mem.id)
            link_report.append({"id": mem.id, "title": mem.title})
    s.db.refresh_evidence_counts()

    # Re-evaluate lifecycle + confidence for the linked memories.
    contradiction_payload = None
    reinforced: list[dict[str, Any]] = []
    confidence_before = 0.0
    for mem in s.db.all_memories():
        if mem.id not in linked:
            continue
        before = mem.confidence
        confidence_before = max(confidence_before, before)
        mem.evidence_count = sum(
            1 for l in s.db.evidence_for(mem.id) if l.polarity == "supports"
        )
        if successful is True:
            previous = mem.status
            mem.status = MemoryStatus.SUPPORTED
            s.db.add_memory_event(
                MemoryEvent(
                    id=new_id("mev"),
                    memory_id=mem.id,
                    from_status=previous,
                    to_status=MemoryStatus.SUPPORTED,
                    action="outcome_supported",
                    actor=who.id,
                    note=f"Outcome {oid} followed this memory successfully.",
                )
            )
        else:
            contradiction = s.contradictions.detect_against_outcome(
                memory=mem,
                outcome_text=f"{actual_action} {result}",
                outcome_source_id=oid,
                successful=False,
            )
            if contradiction:
                s.db.add_contradiction(contradiction)
                s.db.bump_metric("contradictions_detected")
                contradiction_payload = contradiction.model_dump(mode="json")
        open_c = [
            c
            for c in s.db.list_contradictions(status="REVIEW_REQUIRED")
            if c.memory_id == mem.id
        ]
        s.confidence.refresh(mem, contradiction_open=bool(open_c))
        s.db.upsert_memory(mem)
        refreshed = s.db.get_memory(mem.id) or mem
        reinforced.append(
            {
                "id": refreshed.id,
                "title": refreshed.title,
                "status": str(refreshed.status),
                "confidence_before": round(before, 3),
                "confidence_after": round(refreshed.confidence, 3),
                "confidence_delta": round(refreshed.confidence - before, 3),
                "evidence_count": refreshed.evidence_count,
            }
        )

    primary = s.db.get_memory(memory.id)
    strongest = (
        max(reinforced, key=lambda r: r["confidence_after"]) if reinforced else None
    )
    reported = strongest["confidence_after"] if strongest else (
        primary.confidence if primary else memory.confidence
    )
    reported_status = (
        strongest["status"]
        if strongest
        else str(primary.status if primary else memory.status)
    )
    s.db.add_audit(
        AuditEvent(
            id=new_id("aud"),
            event_type=AuditEventType.OUTCOME_RECORDED,
            actor=who.id,
            actor_role=who.role,
            subject=f"Outcome {oid}",
            memory_id=memory.id,
            detail=(
                f"Outcome retained into Hindsight. "
                f"{len(linked)} memories were updated."
            ),
            payload={
                "outcome_id": oid,
                "linked": linked,
                "successful": successful,
                "verdict": verdict,
            },
        )
    )
    s.db.add_learning_event(
        LearningEvent(
            id=new_id("lev"),
            kind="outcome_recorded",
            message=(
                "An operational lesson was strengthened by a new outcome."
                if successful is True
                else (
                    "An outcome contradicted an existing recommendation."
                    if successful is False
                    else "An outcome was recorded but could not be classified."
                )
            ),
            memory_id=memory.id,
            detail=truncate(f"{actual_action} → {result}", 200),
        )
    )
    s.db.bump_metric("outcomes_recorded")
    s.db.bump_metric("memories_revalidated", len(linked))

    return {
        "outcome_id": oid,
        "memory_id": memory.id,
        "status": reported_status,
        "confidence": reported,
        "band": band_for(reported),
        "confidence_before": round(confidence_before, 3),
        "confidence_delta": round(
            reported - confidence_before if reinforced else 0.0, 3
        ),
        "evidence_count": (
            strongest["evidence_count"]
            if strongest
            else (primary.evidence_count if primary else memory.evidence_count)
        ),
        "contradiction": contradiction_payload,
        "successful": successful,
        "verdict": verdict,
        "message": (
            f"Outcome retained. {len(linked)} memories were updated with this new "
            "observation."
            if successful is not None
            else f"Outcome retained. {verdict['rationale']}"
        ),
        "engine_mode": result_obj.engine_mode,
        "engine_simulated": result_obj.engine_simulated,
        "linked_memories": linked,
        "linked_detail": link_report,
        "reinforced": reinforced,
    }


@router.post("/outcome", response_model=OutcomeResponse)
async def outcome(
    payload: OutcomeRequest, s: Services = Depends(get_services)
) -> OutcomeResponse:
    return OutcomeResponse(
        **await record_outcome(
            s,
            question=payload.question,
            recommendation=payload.recommendation,
            actual_action=payload.actual_action,
            result=payload.result,
            notes=payload.notes,
            queue_depth=payload.queue_depth,
            scope=payload.scope,
            actor=payload.actor,
            outcome_id=payload.outcome_id,
            stated_result=payload.successful,
        )
    )


@router.get("/outcomes")
async def list_outcomes(s: Services = Depends(get_services)) -> dict[str, Any]:
    memories = [
        m
        for m in s.db.all_memories()
        if m.source_type == "outcome"
    ]
    return {
        "outcomes": [
            {
                "id": m.id,
                "title": m.title,
                "content": m.content,
                "observed_at": m.observed_at.isoformat() if m.observed_at else None,
                "confidence": m.confidence,
                "status": str(m.status),
                "evidence_count": m.evidence_count,
            }
            for m in sorted(memories, key=lambda x: x.observed_at or x.created_at, reverse=True)
        ],
        "count": len(memories),
    }


__all__ = ["record_outcome", "router"]
