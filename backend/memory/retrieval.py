"""Retrieval and the Memory Lens.

``recall`` is used for evidence retrieval (which memories and incidents back a
question). ``reflect`` is reserved for nuanced synthesis and is not called for
trivial requests.

The Memory Lens is the answer to "why did you say that?". It is assembled from
the real recalled facts, the real evidence links, the real provenance and the
real confidence computation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from backend.config import get_settings
from backend.db.database import Database
from backend.memory.confidence import ConfidenceEngine
from backend.memory.hindsight_client import (
    EngineFact,
    EngineManager,
    EngineRecallResult,
)
from backend.memory.provenance import provenance_view
from backend.models.audit import AuditEvent, AuditEventType
from backend.models.memory import (
    Contradiction,
    MemoryRecord,
    MemoryStatus,
    Visibility,
    utcnow,
)
from backend.models.permissions import Actor, MemoryResolver
from backend.utils import content_tokens, new_id, truncate


@dataclass
class LensEntry:
    """One memory as presented in the Memory Lens."""

    memory_id: str
    title: str
    content: str
    type: str
    source: dict[str, Any]
    scope: str
    environment_match: bool
    environment_note: str
    status: str
    last_validated_at: str | None
    observed_at: str | None
    evidence: list[dict[str, Any]] = field(default_factory=list)
    supporting_observations: int = 0
    confidence: dict[str, Any] = field(default_factory=dict)
    why_relevant: str = ""
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    relevance_score: float = 0.0
    hindsight_fact_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "title": self.title,
            "content": self.content,
            "type": self.type,
            "source": self.source,
            "scope": self.scope,
            "environment_match": self.environment_match,
            "environment_note": self.environment_note,
            "status": self.status,
            "last_validated_at": self.last_validated_at,
            "observed_at": self.observed_at,
            "evidence": self.evidence,
            "supporting_observations": self.supporting_observations,
            "confidence": self.confidence,
            "why_relevant": self.why_relevant,
            "contradictions": self.contradictions,
            "relevance_score": round(self.relevance_score, 4),
            "hindsight_fact_id": self.hindsight_fact_id,
        }


@dataclass
class RetrievalOutcome:
    question: str
    memories: list[MemoryRecord]
    lens: list[LensEntry]
    facts: list[EngineFact]
    withheld: list[dict[str, str]]
    latency_ms: int
    engine_mode: str
    engine_simulated: bool
    fact_count: int
    trace: dict[str, Any]
    request_id: str = ""
    suppressed_fact_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "memories": [m.model_dump(mode="json") for m in self.memories],
            "lens": [entry.to_dict() for entry in self.lens],
            "hindsight_facts": [f.to_dict() for f in self.facts],
            "withheld": self.withheld,
            "latency_ms": self.latency_ms,
            "engine_mode": self.engine_mode,
            "engine_simulated": self.engine_simulated,
            "fact_count": self.fact_count,
            "suppressed_fact_count": len(self.suppressed_fact_ids),
            "trace": self.trace,
            "request_id": self.request_id,
        }


class RetrievalService:
    def __init__(
        self,
        db: Database,
        engine: EngineManager,
        resolver: MemoryResolver | None = None,
    ) -> None:
        self.db = db
        self.engine = engine
        self.resolver = resolver or MemoryResolver()
        self.confidence = ConfidenceEngine()

    # --- current environment -------------------------------------------
    def current_scope(self) -> str:
        """The active component for the Payment Platform right now."""
        system = self.db.get_system("sys-payment")
        return (system or {}).get("active_component") or "Payment Queue v1"

    def open_contradictions(self, memory_id: str | None = None) -> list[Contradiction]:
        items = self.db.list_contradictions(status="REVIEW_REQUIRED")
        if memory_id:
            items = [c for c in items if c.memory_id == memory_id]
        return items

    # --- recall --------------------------------------------------------
    async def recall_for_question(
        self,
        question: str,
        *,
        actor: Actor,
        current_scope: str | None = None,
        include_stale: bool = True,
        max_memories: int = 12,
    ) -> RetrievalOutcome:
        settings = get_settings()
        started = time.perf_counter()
        request_id = new_id("req")
        current_scope = current_scope or self.current_scope()

        # Hindsight recall: the memory engine does the retrieval.
        recall: EngineRecallResult = await self.engine.arecall(
            question,
            max_tokens=settings.recall_max_tokens,
            budget=settings.recall_budget,
        )

        # Map recalled Hindsight facts onto application memories.
        evidence_map = self.db.evidence_map()
        by_fact = {m.hindsight_fact_id: m for m in self.db.all_memories() if m.hindsight_fact_id}
        by_document: dict[str, list[MemoryRecord]] = {}
        for m in self.db.all_memories():
            if m.hindsight_document_id:
                by_document.setdefault(m.hindsight_document_id, []).append(m)

        scored: dict[str, float] = {}
        matched: list[MemoryRecord] = []
        question_tokens = set(content_tokens(question))
        for fact in recall.facts:
            fact_score = float(fact.scores.get("hybrid") or 1.0)
            hit = by_fact.get(fact.id)
            pool = [hit] if hit else by_document.get(fact.document_id or "", [])
            for mem in pool:
                overlap = len(question_tokens & set(content_tokens(mem.content)))
                boost = 1.0 + (0.12 * min(overlap, 6))
                score = fact_score * boost
                if mem.id not in scored or score > scored[mem.id]:
                    scored[mem.id] = score
                if mem not in matched:
                    matched.append(mem)

        # Permission filter happens before anything is shown to the actor.
        visible, withheld = self.resolver.filter_readable(actor, matched)
        if not include_stale:
            visible = [m for m in visible if MemoryStatus(m.status) != MemoryStatus.STALE]

        # Raw recalled facts are only exposed when the actor may read every
        # memory they belong to. A fact whose content is gated (personal memory,
        # a rejected claim, a claim that never became a memory) is counted in the
        # trace but its text is never returned, so Hindsight cannot become a side
        # channel around the Memory Gate.
        readable_facts: list[EngineFact] = []
        suppressed_ids: list[str] = []
        for fact in recall.facts:
            hit = by_fact.get(fact.id)
            owners = [hit] if hit is not None else by_document.get(fact.document_id or "", [])
            if not owners:
                # A fact MemoryOS never turned into a governed memory. It may
                # come from a rejected claim, so its text is not returned.
                suppressed_ids.append(fact.id)
                continue
            if all(self._may_read(actor, m) for m in owners):
                readable_facts.append(fact)
            else:
                suppressed_ids.append(fact.id)

        # Direct-scope memories are relevant to a question only when the question
        # actually touches them. Running the same system is not on its own a
        # reason to answer: an unfamiliar question must be allowed to return
        # nothing rather than borrow in-scope knowledge it did not ask about.
        for mem in self.db.all_memories():
            if mem.scope != current_scope or mem.id in scored or not mem.is_usable():
                continue
            if Visibility(mem.visibility) not in (
                Visibility.ORGANIZATION,
                Visibility.TEAM,
            ):
                continue
            if not self._question_touches(question_tokens, mem):
                continue
            allowed, _ = self.resolver.can_read(actor, mem)
            if not allowed:
                continue
            scored[mem.id] = 0.05
            if mem not in visible:
                visible.append(mem)

        ranked = sorted(visible, key=lambda m: scored.get(m.id, 0.0), reverse=True)
        memories = ranked[:max_memories]

        contradictions = self.open_contradictions()
        lens: list[LensEntry] = []
        for mem in memories:
            lens.append(
                self._lens_entry(
                    mem,
                    question=question,
                    current_scope=current_scope,
                    evidence_map=evidence_map,
                    contradictions=contradictions,
                    relevance=scored.get(mem.id, 0.0),
                )
            )

        latency = int((time.perf_counter() - started) * 1000)
        self.db.add_audit(
            AuditEvent(
                id=new_id("aud"),
                event_type=AuditEventType.HINDSIGHT_RECALL,
                actor=actor.id,
                actor_role=actor.role,
                subject=truncate(question, 120),
                request_id=request_id,
                detail=(
                    f"Recall returned {len(recall.facts)} memories from bank "
                    f"{recall.bank_id} in {recall.latency_ms}ms"
                ),
                payload={
                    "engine_mode": recall.mode,
                    "latency_ms": recall.latency_ms,
                    "fact_count": len(recall.facts),
                    "memories_used": [m.id for m in memories],
                    "withheld_count": len(withheld),
                },
            )
        )
        self.db.bump_metric("memories_retrieved", len(memories))

        return RetrievalOutcome(
            question=question,
            memories=memories,
            lens=lens,
            facts=readable_facts,
            withheld=withheld,
            latency_ms=latency,
            engine_mode=recall.mode,
            engine_simulated=self.engine.active.simulated,
            fact_count=len(recall.facts),
            trace={
                "steps": [
                    {"step": "Question", "value": truncate(question, 90)},
                    {"step": "Recall", "value": f"{recall.mode} / budget={settings.recall_budget}"},
                    {"step": "Memories found", "value": str(len(recall.facts))},
                    {"step": "Permission filter", "value": f"{len(matched) - len(withheld)} readable, {len(withheld)} withheld"},
                    {"step": "Relevant evidence", "value": f"{sum(len(e) for e in evidence_map.values())} linked evidence items"},
                    {
                        "step": "Fact visibility",
                        "value": f"{len(readable_facts)} shown, {len(suppressed_ids)} suppressed by the Memory Gate",
                    },
                ],
                "recall": recall.trace,
                "strategy_counts": recall.strategy_counts,
                "latency_ms": recall.latency_ms,
                "fact_ids": [f.id for f in readable_facts][:25],
                "fact_types": sorted({f.type for f in recall.facts}),
                "suppressed_fact_ids": suppressed_ids[:25],
            },
            request_id=request_id,
            suppressed_fact_ids=suppressed_ids,
        )

    # --- memory lens ---------------------------------------------------
    @staticmethod
    def _question_touches(question_tokens: set[str], mem: MemoryRecord) -> bool:
        """True when the question shares real vocabulary with the memory.

        Scope and entity names count, because that is how an operator actually
        refers to knowledge. Generic English does not.
        """
        haystack = set(content_tokens(mem.scope))
        haystack |= {
            token for entity in mem.related_entities for token in content_tokens(entity)
        }
        haystack |= set(content_tokens(mem.content))
        return bool(question_tokens & haystack)

    def _may_read(self, actor: Actor, mem: MemoryRecord) -> bool:
        allowed, _ = self.resolver.can_read(actor, mem)
        return allowed

    def _lens_entry(
        self,
        mem: MemoryRecord,
        *,
        question: str,
        current_scope: str,
        evidence_map: dict[str, list],
        contradictions: list[Contradiction],
        relevance: float,
    ) -> LensEntry:
        links = evidence_map.get(mem.id, [])
        open_here = [c for c in contradictions if c.memory_id == mem.id]
        confidence = self.confidence.evaluate(
            mem,
            current_scope=current_scope,
            contradiction_open=bool(open_here),
        )
        env_match = mem.scope == current_scope
        if env_match:
            env_note = f"Scope matches the running environment ({current_scope})."
        else:
            env_note = (
                f"Scoped to '{mem.scope}' but the running component is "
                f"'{current_scope}'. This knowledge may be outdated."
            )
        return LensEntry(
            memory_id=mem.id,
            title=mem.title,
            content=mem.content,
            type=str(mem.type),
            source=provenance_view(mem).to_dict(),
            scope=mem.scope,
            environment_match=env_match,
            environment_note=env_note,
            status=str(mem.status),
            last_validated_at=(
                mem.last_validated_at.isoformat() if mem.last_validated_at else None
            ),
            observed_at=mem.observed_at.isoformat() if mem.observed_at else None,
            evidence=[
                {
                    "evidence_type": l.evidence_type,
                    "evidence_id": l.evidence_id,
                    "label": l.evidence_label,
                    "polarity": l.polarity,
                    "detail": l.detail,
                }
                for l in links
            ],
            supporting_observations=sum(1 for l in links if l.polarity == "supports"),
            confidence=confidence.to_dict(),
            why_relevant=self._why_relevant(mem, question, relevance),
            contradictions=[c.model_dump(mode="json") for c in open_here],
            relevance_score=relevance,
            hindsight_fact_id=mem.hindsight_fact_id,
        )

    def _why_relevant(self, mem: MemoryRecord, question: str, relevance: float) -> str:
        q = set(content_tokens(question))
        m = set(content_tokens(mem.content + " " + mem.title))
        shared = sorted(q & m)
        reasons = [
            f"Recalled from Hindsight bank '{self.engine.bank_id}' with a hybrid "
            f"retrieval score of {relevance:.2f}."
        ]
        if shared:
            reasons.append(
                "Shared terms with the question: " + ", ".join(shared[:6]) + "."
            )
        if mem.evidence_count:
            reasons.append(
                f"Backed by {mem.evidence_count} linked incident(s) or outcome(s)."
            )
        if mem.scope:
            reasons.append(f"Recorded scope: {mem.scope}.")
        return " ".join(reasons)

    def lens_for_memory(self, mem: MemoryRecord) -> LensEntry:
        return self._lens_entry(
            mem,
            question="",
            current_scope=self.current_scope(),
            evidence_map=self.db.evidence_map(),
            contradictions=self.open_contradictions(),
            relevance=1.0,
        )

    def graph(self, system: str = "Payment Platform") -> dict[str, Any]:
        """A small graph generated from application data, not hard-coded UI."""
        memories = [
            m
            for m in self.db.all_memories()
            if m.scope.startswith("Payment") or "Payment" in m.scope
        ]
        nodes: dict[str, dict[str, Any]] = {}

        def node(nid: str, label: str, ntype: str, **extra: Any) -> None:
            if nid not in nodes:
                nodes[nid] = {"id": nid, "label": label, "type": ntype, **extra}

        sysrow = self.db.get_system("sys-payment")
        if sysrow:
            node("Payment Platform", "Payment Platform", "system", criticality=sysrow.get("criticality"))
            for comp in sysrow.get("components", []):
                node(
                    comp,
                    comp,
                    "component",
                    active=comp == sysrow.get("active_component"),
                )
        for emp in self.db.list_employees():
            node(emp["name"], emp["name"], "person", role=emp["role"], status=emp["status"])
        for inc in self.db.list_incidents(system="Payment Platform"):
            node(inc["id"], inc["id"], "incident", severity=inc["severity"], depth=inc.get("queue_depth"))
        node("Payments Operations", "Payments Operations", "team")
        node("Queue saturation lesson", "Queue saturation lesson", "lesson", active=True)

        for mem in memories:
            if mem.type in {"LESSON", "EXPERIENCE"} and "restart" in mem.title.lower():
                node(mem.id, truncate(mem.title, 44), "memory", status=str(mem.status))

        edges = [
            {"from": "Arun", "to": "Payment Platform", "label": "knows", "kind": "person_system"},
            {"from": "Payment API", "to": "Payment Queue v1", "label": "depends_on", "kind": "dependency"},
            {"from": "Payment API", "to": "Payment Queue v2", "label": "depends_on", "kind": "dependency"},
            {"from": "INC-1042", "to": "Queue saturation lesson", "label": "demonstrates", "kind": "failure"},
            {"from": "INC-1088", "to": "Queue saturation lesson", "label": "supports", "kind": "support"},
            {"from": "INC-1104", "to": "Queue saturation lesson", "label": "supports", "kind": "support"},
            {"from": "INC-1111", "to": "Queue saturation lesson", "label": "supports", "kind": "support"},
            {"from": "Queue saturation lesson", "to": "Payments Operations", "label": "escalates_to", "kind": "escalation"},
            {"from": "Arun", "to": "Queue saturation lesson", "label": "authored", "kind": "authorship"},
            {"from": "Payment Queue v2", "to": "Queue saturation lesson", "label": "invalidates", "kind": "change"},
        ]
        # Only keep edges whose endpoints exist in the generated node set.
        resolved = [e for e in edges if e["from"] in nodes and e["to"] in nodes]
        # Attach real memory nodes that carry supporting incidents.
        for mem in memories:
            if mem.id in nodes:
                for link in self.db.evidence_for(mem.id):
                    if link.evidence_id in nodes:
                        resolved.append(
                            {
                                "from": link.evidence_id,
                                "to": mem.id,
                                "label": link.polarity,
                                "kind": "evidence",
                            }
                        )
        return {"nodes": list(nodes.values()), "edges": resolved}

    def timeline(self, system: str = "Payment Platform") -> dict[str, Any]:
        """Real timeline built from audit, incidents, memories and changes."""
        from backend.seed.novatech import TIMELINE_EVENTS

        entries: list[dict[str, Any]] = []
        for ev in TIMELINE_EVENTS:
            entries.append(
                {
                    "at": ev["at"],
                    "label": ev["label"],
                    "detail": ev["detail"],
                    "kind": ev["kind"],
                    "critical": ev.get("critical", False),
                    "supporting": ev.get("supporting", False),
                    "synthetic": True,
                }
            )
        for mem in self.db.all_memories():
            entries.append(
                {
                    "at": mem.created_at.isoformat(),
                    "label": f"Memory {mem.id} captured",
                    "detail": f"{mem.type}: {mem.title}",
                    "kind": "memory",
                    "critical": False,
                    "supporting": False,
                    "synthetic": False,
                }
            )
        for c in self.db.list_contradictions():
            entries.append(
                {
                    "at": c.detected_at.isoformat(),
                    "label": f"Contradiction {c.id}",
                    "detail": c.reason,
                    "kind": "contradiction",
                    "critical": True,
                    "supporting": False,
                    "synthetic": False,
                }
            )
        for change in self.db.list_architecture_changes():
            entries.append(
                {
                    "at": change["effective_at"],
                    "label": change["id"],
                    "detail": change["summary"][:200],
                    "kind": "change",
                    "critical": bool(change.get("invalidates_scope")),
                    "supporting": False,
                    "synthetic": False,
                }
            )
        entries.sort(key=lambda e: e["at"])
        return {"system": system, "entries": entries, "now": utcnow().isoformat()}


__all__ = ["LensEntry", "RetrievalOutcome", "RetrievalService"]
