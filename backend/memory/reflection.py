"""Reflection: turning recalled evidence into a governed answer.

``reflect`` is called only when the question needs synthesis over accumulated
experience. Trivial lookups stop at ``recall``.

The structured answer always separates:

    DOCUMENTED FACT
    HISTORICAL EXPERIENCE
    CURRENT EVIDENCE
    INFERENCE
    RECOMMENDATION

and never presents inference as fact.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from backend.config import get_settings
from backend.db.database import Database
from backend.memory.confidence import CONFIDENCE_DISCLAIMER
from backend.memory.hindsight_client import EngineManager
from backend.memory.retrieval import LensEntry, RetrievalOutcome
from backend.models.audit import AuditEvent, AuditEventType
from backend.models.memory import ConfidenceBand, MemoryRecord, utcnow
from backend.utils import new_id, truncate

#: Words in the question that indicate a genuine reasoning task rather than a
#: lookup. Keeps ``reflect`` off the hot path for trivial requests.
REASONING_TRIGGERS = (
    "what should i",
    "should i",
    "what do i",
    "what did",
    "why did",
    "why do",
    "how do",
    "how should",
    "what happens",
    "is it safe",
    "can i",
    "should we",
    "tell me",
    "recommend",
    "explain",
)


def needs_reflection(question: str) -> bool:
    lowered = (question or "").lower().strip()
    if len(lowered) < 12:
        return False
    return any(trigger in lowered for trigger in REASONING_TRIGGERS)


@dataclass
class AnswerSection:
    label: str
    points: list[str] = field(default_factory=list)
    kind: str = "fact"  # fact | experience | evidence | inference | recommendation

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "kind": self.kind, "points": self.points}


@dataclass
class ReflectionResult:
    headline: str
    sections: list[AnswerSection]
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    outdated_warning: str | None = None
    reflect_text: str = ""
    reflect_mode: str = "not_called"
    reflect_latency_ms: int = 0
    based_on: list[str] = field(default_factory=list)
    confidence: dict[str, Any] = field(default_factory=dict)
    scope: dict[str, Any] = field(default_factory=dict)
    trace: list[dict[str, str]] = field(default_factory=list)
    call_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "headline": self.headline,
            "sections": [s.to_dict() for s in self.sections],
            "conflicts": self.conflicts,
            "outdated_warning": self.outdated_warning,
            "reflect_text": self.reflect_text,
            "reflect_mode": self.reflect_mode,
            "reflect_latency_ms": self.reflect_latency_ms,
            "based_on": self.based_on,
            "confidence": self.confidence,
            "scope": self.scope,
            "trace": self.trace,
            "call_count": self.call_count,
        }


class ReflectionService:
    def __init__(self, db: Database, engine: EngineManager) -> None:
        self.db = db
        self.engine = engine
        self._settings = get_settings()

    # --- public --------------------------------------------------------
    async def reflect(
        self,
        question: str,
        retrieval: RetrievalOutcome,
        *,
        actor_name: str,
        current_scope: str,
        request_id: str,
    ) -> ReflectionResult:
        trace: list[dict[str, str]] = [
            {"step": "Question", "value": truncate(question, 80)},
        ]
        result = ReflectionResult(headline="", sections=[])

        if not retrieval.memories:
            result.headline = (
                "We haven't experienced this before — follow the documented runbook."
            )
            result.sections = [
                AnswerSection(
                    label="RECOMMENDATION",
                    kind="recommendation",
                    points=[
                        "Follow the documented runbook for now. MemoryOS has no "
                        "organizational experience recorded for this question, so it "
                        "cannot add anything the documentation does not already say.",
                        "Capture the answer you end up using so the next person "
                        "inherits it.",
                    ],
                ),
                AnswerSection(
                    label="CURRENT EVIDENCE",
                    kind="evidence",
                    points=[
                        f"0 relevant memories recalled from bank "
                        f"{self.engine.bank_id}.",
                        f"{retrieval.fact_count} facts were recalled and none of them "
                        f"matched this question.",
                    ],
                ),
            ]
            result.scope = {
                "current_environment": current_scope,
                "note": "No scoped knowledge available.",
            }
            # Saying "we do not know" is itself a confident, evidence-backed
            # statement, and the UI shows the number either way.
            result.confidence = {
                "score": 0.0,
                "band": str(ConfidenceBand.LOW),
                "label": "Internal confidence",
                "disclaimer": CONFIDENCE_DISCLAIMER,
                "factors": [],
                "reason": (
                    "No organizational memory matches this question. MemoryOS is "
                    "answering from absence of experience, not from evidence."
                ),
            }
            result.trace = trace + [{"step": "Reflect", "value": "skipped (no memories)"}]
            return result

        lessons = [m for m in retrieval.memories if _is_lessonish(m)]
        failures = [
            m
            for m in retrieval.memories
            if "duplicate" in m.content.lower() or "wrong action" in m.title.lower()
        ]
        successes = [
            m
            for m in retrieval.memories
            if "without duplicate" in m.content.lower()
            or "no restart" in m.content.lower()
            or "resolved without" in m.content.lower()
        ]
        facts = [m for m in retrieval.memories if str(m.type) == "FACT"]
        hypotheses = [m for m in retrieval.memories if str(m.type) == "HYPOTHESIS"]

        contradictions = self.db.list_contradictions(status="REVIEW_REQUIRED")
        relevant_contradictions = [
            c for c in contradictions if c.memory_id in {m.id for m in retrieval.memories}
        ]

        # 1. reflect over the accumulated experience, only when warranted.
        reflect_text = ""
        reflect_mode = "not_called"
        reflect_latency = 0
        based_on: list[str] = []
        if needs_reflection(question):
            trace.append({"step": "Reflect", "value": "calling Hindsight reflect"})
            started = time.perf_counter()
            try:
                reflected = await self.engine.areflect(
                    question,
                    budget=self._settings.reflect_budget,
                    context=(
                        f"Answer for {actor_name}. Current environment: {current_scope}. "
                        "Distinguish documented fact, historical experience, current "
                        "evidence, inference and recommendation. Never present inference "
                        "as fact. Cite the scope of each memory."
                    ),
                )
                reflect_text = reflected.text
                reflect_mode = reflected.mode
                reflect_latency = int((time.perf_counter() - started) * 1000)
                based_on = [f.id for f in reflected.based_on]
                self.db.add_audit(
                    AuditEvent(
                        id=new_id("aud"),
                        event_type=AuditEventType.HINDSIGHT_REFLECT,
                        actor=actor_name,
                        subject=truncate(question, 120),
                        request_id=request_id,
                        detail=(
                            f"Reflect synthesised an answer from "
                            f"{len(reflected.based_on)} memories in {reflected.latency_ms}ms"
                        ),
                        payload={
                            "engine_mode": reflected.mode,
                            "based_on_count": len(reflected.based_on),
                            "budget": self._settings.reflect_budget,
                        },
                    )
                )
            except Exception as exc:  # noqa: BLE001
                reflect_mode = "failed"
                reflect_text = f"Reflection unavailable: {exc}"
        else:
            trace.append(
                {"step": "Reflect", "value": "skipped (lookup, not a reasoning task)"}
            )

        # 2. Compose the structured answer from the retrieved evidence.
        incident_lines = self._incident_lines(retrieval.lens)
        sections: list[AnswerSection] = []

        if facts:
            sections.append(
                AnswerSection(
                    label="DOCUMENTED FACT",
                    kind="fact",
                    points=[f"{m.title}. {truncate(m.content, 200)}" for m in facts[:4]],
                )
            )

        experience_points: list[str] = []
        for m in failures[:3]:
            experience_points.append(
                f"{m.source_id}: the action taken was '{truncate(m.content, 180)}'"
            )
        for m in successes[:3]:
            experience_points.append(
                f"{m.source_id}: resolved without repeating the failure — "
                f"{truncate(m.summary or m.content, 160)}"
            )
        if not experience_points:
            for m in lessons[:3]:
                experience_points.append(f"{m.source_id}: {truncate(m.content, 190)}")
        if experience_points:
            sections.append(
                AnswerSection(
                    label="HISTORICAL EXPERIENCE",
                    kind="experience",
                    points=experience_points[:6],
                )
            )

        current_evidence: list[str] = [
            f"Current environment: {current_scope}.",
            f"{len(retrieval.memories)} relevant memories recalled from Hindsight bank "
            f"{self.engine.bank_id} in {retrieval.latency_ms}ms.",
        ]
        if incident_lines:
            current_evidence.append("Supporting incidents:")
            current_evidence.extend(incident_lines)
        sections.append(
            AnswerSection(label="CURRENT EVIDENCE", kind="evidence", points=current_evidence)
        )

        if hypotheses:
            sections.append(
                AnswerSection(
                    label="UNPROVEN (held as hypothesis)",
                    kind="inference",
                    points=[
                        f"{m.title}: {truncate(m.content, 180)}" for m in hypotheses[:3]
                    ],
                )
            )

        inference: list[str] = []
        if lessons and current_scope:
            in_scope = [m for m in lessons if m.scope == current_scope]
            if in_scope:
                inference.append(
                    "The organization has repeatedly avoided the failure by following the "
                    "recorded procedure rather than the runbook, while the runbook is "
                    f"scoped to the active environment ({current_scope})."
                )
            else:
                inference.append(
                    f"The recorded lessons are scoped to "
                    f"{sorted({m.scope for m in lessons})}, which is not the active "
                    f"environment ({current_scope}). Applicability is unconfirmed."
                )
        if hypotheses:
            inference.append(
                "The retry-worker workaround is believed but not proven; it is recorded as "
                "a hypothesis and should not be treated as established procedure."
            )
        if inference:
            sections.append(
                AnswerSection(label="INFERENCE", kind="inference", points=inference)
            )

        # 3. Recommendation, gated on whether the knowledge is still in scope.
        if relevant_contradictions:
            headline = "Do NOT reuse the historical procedure — it may be outdated."
            recommendation = [
                "Do not apply the historical procedure to the current environment.",
                *[
                    f"Open contradiction: '{c.memory_title}' is scoped to "
                    f"{c.memory_scope} while the running component is "
                    f"{c.current_environment}."
                    for c in relevant_contradictions[:3]
                ],
                "Validate the new operational procedure with the owning team "
                "(Payments Operations) before acting.",
                "The historical lesson is preserved. It has not been deleted — it is "
                "awaiting a scope decision.",
            ]
            outdated_warning = (
                f"KNOWLEDGE MAY BE OUTDATED — {len(relevant_contradictions)} active "
                f"memory/memories are scoped to a previous environment."
            )
        else:
            headline = self._headline(retrieval.memories, current_scope)
            recommendation = self._recommendation(
                retrieval.memories, current_scope, successes, failures
            )
            outdated_warning = None

        sections.append(
            AnswerSection(
                label="RECOMMENDATION", kind="recommendation", points=recommendation
            )
        )

        # 4. Aggregate confidence across the memories used.
        confidence = self._aggregate_confidence(retrieval.lens, bool(relevant_contradictions))
        scope = {
            "current_environment": current_scope,
            "memory_scopes": sorted({m.scope for m in retrieval.memories}),
            "in_scope": [m.id for m in retrieval.memories if m.scope == current_scope],
            "out_of_scope": [
                {"id": m.id, "scope": m.scope, "title": m.title}
                for m in retrieval.memories
                if m.scope != current_scope
            ],
        }

        conflicts = [c.model_dump(mode="json") for c in relevant_contradictions]
        trace.append(
            {
                "step": "Response",
                "value": f"{len(sections)} structured sections, "
                f"{len(retrieval.memories)} memories cited",
            }
        )

        self.db.bump_metric("memories_used", len(retrieval.memories))
        return ReflectionResult(
            headline=headline,
            sections=sections,
            conflicts=conflicts,
            outdated_warning=outdated_warning,
            reflect_text=reflect_text,
            reflect_mode=reflect_mode,
            reflect_latency_ms=reflect_latency,
            based_on=based_on,
            confidence=confidence,
            scope=scope,
            trace=trace,
            call_count=1 if reflect_mode not in {"not_called"} else 0,
        )

    # --- helpers -------------------------------------------------------
    def _incident_lines(self, lens: list[LensEntry]) -> list[str]:
        lines: list[str] = []
        for entry in lens:
            for ev in entry.evidence:
                if ev["evidence_type"] != "incident":
                    continue
                detail = ev.get("detail") or ""
                lines.append(
                    f"{ev['evidence_id']}: {detail}" if detail else ev["evidence_id"]
                )
        seen: set[str] = set()
        unique: list[str] = []
        for line in lines:
            if line not in seen:
                seen.add(line)
                unique.append(line)
        return unique[:6]

    def _headline(self, memories: list[MemoryRecord], current_scope: str) -> str:
        text = " ".join(f"{m.title} {m.content}" for m in memories).lower()
        if "restart" in text and ("do not" in text or "never" in text):
            return f"Do not restart the Payment API yet — check {current_scope} depth first."
        if not memories:
            return "No organizational experience recorded yet."
        return "Follow the recorded organizational experience before the documented runbook."

    def _recommendation(
        self,
        memories: list[MemoryRecord],
        current_scope: str,
        successes: list[MemoryRecord],
        failures: list[MemoryRecord],
    ) -> list[str]:
        steps: list[str] = []
        scope_memories = [m for m in memories if m.scope == current_scope]
        if failures:
            steps.append("Do not restart immediately. Historical experience shows this is harmful.")
        for m in scope_memories:
            if m.type == "LESSON" and m.scope == current_scope:
                steps.append(f"{m.title}.")
                break
        escalation = next(
            (
                m
                for m in memories
                if m.type == "RELATIONSHIP" and "Payments Operations" in m.content
            ),
            None,
        )
        if escalation:
            steps.append(
                "If queue depth is above the recorded threshold, contact Payments "
                "Operations before restarting anything."
            )
        steps.append("Understand and drain the queue as instructed.")
        steps.append("Restart only after the condition is understood.")
        steps.append(
            "Record the outcome afterwards so the organization keeps this experience."
        )
        return steps

    def _aggregate_confidence(
        self, lens: list[LensEntry], has_contradiction: bool
    ) -> dict[str, Any]:
        if not lens:
            return {
                "score": 0.0,
                "band": "LOW",
                "label": "Internal confidence",
                "disclaimer": "No memories were used, so there is nothing to be confident about.",
                "factors": [],
                "penalties": [],
            }
        score = sum(e.confidence.get("score", 0.0) for e in lens) / len(lens)
        if has_contradiction:
            score *= 0.7
        from backend.memory.confidence import band_for

        evidence_total = sum(e.supporting_observations for e in lens)
        return {
            "score": round(score, 3),
            "band": band_for(score),
            "label": "Internal confidence",
            "disclaimer": (
                "Internal confidence is a MemoryOS heuristic over source reliability, "
                "supporting observations, human confirmation, recency, scope match and "
                "outcome success. It is not a probability that this is true."
            ),
            "evidence_total": evidence_total,
            "memories_used": len(lens),
            "penalties": (
                ["An open contradiction is attached to at least one memory used."]
                if has_contradiction
                else []
            ),
            "factors": [
                {
                    "key": f"memory:{e.memory_id}",
                    "label": e.title,
                    "score": e.confidence.get("score"),
                    "band": e.confidence.get("band"),
                }
                for e in lens
            ],
        }


def _is_lessonish(mem: MemoryRecord) -> bool:
    return str(mem.type) in {"LESSON", "EXPERIENCE", "OBSERVATION", "CORRECTION"}


__all__ = ["AnswerSection", "REASONING_TRIGGERS", "ReflectionResult", "ReflectionService", "needs_reflection"]
