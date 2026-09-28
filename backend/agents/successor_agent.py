"""The successor agent.

This is the *successor* of the engineer who left, not a simulation of the
engineer. It answers questions using organizational memory and always shows its
evidence. It never claims to be, or to represent, any individual.

Flow:

    question
      -> MemoryResolver (permission boundary)
      -> Hindsight recall   (evidence)
      -> Hindsight reflect  (synthesis, only when it is a reasoning task)
      -> structured answer + Memory Lens
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backend.db.database import Database
from backend.memory.hindsight_client import EngineManager
from backend.memory.lifecycle import apply_transition
from backend.memory.reflection import ReflectionResult, ReflectionService
from backend.memory.retrieval import RetrievalOutcome, RetrievalService
from backend.models.audit import AuditEvent, AuditEventType
from backend.models.memory import LearningEvent, MemoryStatus, utcnow
from backend.models.permissions import Actor, MemoryResolver
from backend.utils import new_id, truncate

DEFAULT_QUESTION = "Payment API is showing connection reset alerts. What should I do?"


@dataclass
class Answer:
    """Everything the UI needs for one question."""

    question: str
    asked_by: dict[str, str]
    at: datetime
    answer: ReflectionResult
    retrieval: RetrievalOutcome
    warnings: list[str] = field(default_factory=list)
    privacy_notice: dict[str, Any] | None = None
    duration_ms: int = 0
    engine_mode: str = "unknown"
    engine_simulated: bool = False

    def to_dict(self) -> dict[str, Any]:
        outdated = bool(
            self.answer.outdated_warning
            or self.answer.conflicts
            or self.warnings
        )
        return {
            "question": self.question,
            "asked_by": self.asked_by,
            "at": self.at.isoformat(),
            "answer": self.answer.to_dict(),
            "lens": [e.to_dict() for e in self.retrieval.lens],
            "memories_used": [m.model_dump(mode="json") for m in self.retrieval.memories],
            "hindsight_facts": [f.to_dict() for f in self.retrieval.facts],
            "withheld": self.retrieval.withheld,
            "trace": {
                "steps": self.retrieval.trace.get("steps", []),
                "recall": self.retrieval.trace,
                "reflect": self.answer.trace,
                "latency_ms": self.retrieval.latency_ms,
                "reflect_latency_ms": self.answer.reflect_latency_ms,
                "engine_mode": self.engine_mode,
                "engine_simulated": self.engine_simulated,
                "fact_ids": self.retrieval.trace.get("fact_ids", []),
                "fact_types": self.retrieval.trace.get("fact_types", []),
                "suppressed_fact_ids": self.retrieval.trace.get("suppressed_fact_ids", []),
                "reflect_mode": self.answer.reflect_mode,
                "reflect_call_count": self.answer.call_count,
            },
            "warnings": self.warnings,
            "privacy_notice": self.privacy_notice,
            "duration_ms": self.duration_ms,
            "engine_mode": self.engine_mode,
            "engine_simulated": self.engine_simulated,
            "request_id": self.retrieval.request_id,
            "fact_count": self.retrieval.fact_count,
            "suppressed_fact_count": len(self.retrieval.suppressed_fact_ids),
            "outdated": outdated,
            "confidence": self.answer.confidence,
        }


class SuccessorAgent:
    def __init__(
        self,
        db: Database,
        engine: EngineManager,
        resolver: MemoryResolver | None = None,
    ) -> None:
        self.db = db
        self.engine = engine
        self.resolver = resolver or MemoryResolver()
        self.retrieval = RetrievalService(db, engine, self.resolver)
        self.reflection = ReflectionService(db, engine)

    async def ask(
        self,
        question: str,
        *,
        actor: Actor,
        current_scope: str | None = None,
    ) -> Answer:
        started = time.perf_counter()
        question = (question or "").strip() or DEFAULT_QUESTION
        current_scope = current_scope or self.retrieval.current_scope()

        retrieval = await self.retrieval.recall_for_question(
            question, actor=actor, current_scope=current_scope
        )

        reflection = await self.reflection.reflect(
            question,
            retrieval,
            actor_name=actor.display_name,
            current_scope=current_scope,
            request_id=retrieval.request_id,
        )

        warnings: list[str] = []
        if self.engine.active.simulated:
            warnings.append(
                "SIMULATED: Hindsight is unreachable, so memory operations ran on the "
                "SIMULATED engine. Results are computed from actually stored memories "
                "but are not Hindsight output."
            )
        if reflection.conflicts:
            warnings.append(
                f"{len(reflection.conflicts)} open contradiction(s) affect the memories "
                "used in this answer."
            )
        if retrieval.withheld:
            warnings.append(
                f"{len(retrieval.withheld)} memory/memories were withheld by the permission "
                "boundary."
            )

        privacy_notice = None
        if retrieval.withheld:
            privacy_notice = {
                "withheld_count": len(retrieval.withheld),
                "items": retrieval.withheld,
                "explanation": (
                    "MemoryOS enforces the personal/organizational boundary at query time. "
                    "PERSONAL memory is never returned through an organizational question, "
                    "even when it is semantically similar."
                ),
            }

        # Mark the memories that were actually used.
        for mem in retrieval.memories:
            if MemoryStatus(mem.status) in {
                MemoryStatus.ACTIVE,
                MemoryStatus.CONFIRMED,
                MemoryStatus.SUPPORTED,
            }:
                event = apply_transition(
                    mem,
                    MemoryStatus.USED,
                    actor=actor.id,
                    action="used_by_agent",
                    note=f"Used to answer: {truncate(question, 80)}",
                    payload={"request_id": retrieval.request_id},
                    strict=False,
                )
                self.db.upsert_memory(mem)
                self.db.add_memory_event(event)

        self.db.add_audit(
            AuditEvent(
                id=new_id("aud"),
                event_type=AuditEventType.MEMORY_USED_BY_AGENT,
                actor=actor.id,
                actor_role=actor.role,
                subject=truncate(question, 120),
                request_id=retrieval.request_id,
                detail=(
                    f"Agent answered using {len(retrieval.memories)} memories; "
                    f"reflect={reflection.reflect_mode}"
                ),
                payload={
                    "memories_used": [m.id for m in retrieval.memories],
                    "open_contradictions": len(reflection.conflicts),
                    "engine_mode": self.engine.active.mode,
                },
            )
        )
        self.db.add_learning_event(
            LearningEvent(
                id=new_id("lev"),
                kind="successor_answered",
                message=(
                    "A successor resolved a question using historical organizational "
                    "experience."
                    if retrieval.memories
                    else "A successor asked a question with no organizational experience yet."
                ),
                detail=truncate(question, 160),
                memory_id=retrieval.memories[0].id if retrieval.memories else None,
            )
        )

        return Answer(
            question=question,
            asked_by={
                "id": actor.id,
                "display_name": actor.display_name,
                "role": actor.role,
                "team": actor.team,
            },
            at=utcnow(),
            answer=reflection,
            retrieval=retrieval,
            warnings=warnings,
            privacy_notice=privacy_notice,
            duration_ms=int((time.perf_counter() - started) * 1000),
            engine_mode=self.engine.active.mode,
            engine_simulated=self.engine.active.simulated,
        )


__all__ = ["Answer", "DEFAULT_QUESTION", "SuccessorAgent"]
