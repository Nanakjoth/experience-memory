"""Memory Ingestion Service.

Pipeline for every piece of experience that enters the organization:

    KnowledgeSource -> SourceDocument
        -> Memory Gate (authorize / purpose / scope / sensitivity / retention)
        -> Hindsight retain  (only approved claims reach the memory bank)
        -> app MemoryRecord  (governance metadata, linked by hindsight_fact_id)
        -> evidence links
        -> audit + learning event

The gate runs *before* retention, so the memory engine cannot become a store
that outlives the Memory Gate. Nothing is retained, persisted or surfaced that
was not approved, and every decision is audited.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backend.db.database import Database
from backend.memory.confidence import ConfidenceEngine
from backend.memory.hindsight_client import (
    EngineManager,
    MemoryEngineUnavailable,
)
from backend.memory.lifecycle import apply_transition
from backend.models.audit import AuditEvent, AuditEventType
from backend.models.memory import (
    AccessLevel,
    EvidenceLink,
    LearningEvent,
    MemoryEvent,
    MemoryGateDecision,
    MemoryRecord,
    MemoryStatus,
    MemoryType,
    Sensitivity,
    Visibility,
    utcnow,
)
from backend.models.permissions import Actor, MemoryResolver
from backend.sources.base import ExtractedClaim, SourceDocument
from backend.utils import new_id, stable_id, truncate

SENSITIVE_HINTS = ("confidential", "restricted", "private", "salary", "compensation")


@dataclass
class IngestionResult:
    document: SourceDocument
    retained: bool = False
    hindsight_fact_ids: list[str] = field(default_factory=list)
    memories: list[MemoryRecord] = field(default_factory=list)
    rejected: list[dict[str, str]] = field(default_factory=list)
    engine_mode: str = "unknown"
    engine_simulated: bool = False
    error: str | None = None
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.document.source_type,
            "source_id": self.document.source_id,
            "source_name": self.document.source_name,
            "title": self.document.title,
            "retained": self.retained,
            "hindsight_fact_ids": self.hindsight_fact_ids,
            "engine_mode": self.engine_mode,
            "engine_simulated": self.engine_simulated,
            "memory_ids": [m.id for m in self.memories],
            "rejected": self.rejected,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


class MemoryIngestionService:
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

    # --- audit helpers -------------------------------------------------
    def _audit(
        self,
        *,
        event_type: AuditEventType,
        actor: str,
        subject: str = "",
        memory_id: str | None = None,
        detail: str = "",
        payload: dict[str, Any] | None = None,
        actor_role: str = "system",
    ) -> None:
        self.db.add_audit(
            AuditEvent(
                id=new_id("aud"),
                event_type=event_type,
                actor=actor,
                actor_role=actor_role,
                subject=subject,
                memory_id=memory_id,
                detail=detail,
                payload=payload or {},
            )
        )

    # --- gate ----------------------------------------------------------
    def evaluate(
        self, claim: ExtractedClaim, document: SourceDocument, owner_actor: Actor
    ) -> MemoryGateDecision:
        return self.resolver.evaluate_gate(
            content=f"{claim.title} {claim.content}",
            purpose=claim.purpose or document.purpose,
            scope=claim.scope or document.scope,
            visibility=Visibility(claim.visibility or document.visibility),
            owner=claim.owner or document.owner,
            team=document.team,
            is_operational_knowledge=claim.is_operational,
        )

    # --- ingestion -----------------------------------------------------
    async def ingest(
        self,
        document: SourceDocument,
        *,
        owner_actor: Actor | None = None,
        auto_confirm: bool = False,
    ) -> IngestionResult:
        import time

        started = time.perf_counter()
        owner_actor = owner_actor or Actor(
            id=document.owner, display_name=document.owner, role="System"
        )
        result = IngestionResult(document=document)

        # 1. The Memory Gate runs first, per claim. Only approved claims are ever
        #    written to Hindsight, so a rejected claim cannot be recalled later
        #    through the engine's own storage.
        approved: list[tuple[ExtractedClaim, MemoryGateDecision]] = []
        for claim in document.claims:
            gate = self.evaluate(claim, document, owner_actor)
            if gate.decision != "STORE":
                result.rejected.append(
                    {
                        "title": claim.title,
                        "decision": gate.decision,
                        "reason": "; ".join(gate.reasons),
                    }
                )
                self._audit(
                    event_type=AuditEventType.MEMORY_REJECTED,
                    actor=document.owner,
                    subject=claim.title,
                    detail=f"Memory Gate decision: {gate.decision}",
                    payload={"reasons": gate.reasons},
                )
                continue
            approved.append((claim, gate))

        if not approved:
            result.duration_ms = int((time.perf_counter() - started) * 1000)
            return result

        # 2. Retain the approved experience into Hindsight. The raw text that
        #    reaches the memory bank is exactly what the gate allowed.
        try:
            retain_resp = await self.engine.aretain(
                self._retainable_text(approved),
                context=document.context,
                document_id=document.document_id,
                metadata=document.retain_metadata(),
                tags=document.retain_tags(),
                timestamp=document.observed_at,
            )
            result.retained = True
            result.hindsight_fact_ids = list(retain_resp.get("fact_ids") or [])
            result.engine_mode = retain_resp.get("mode") or self.engine.active.mode
            self._audit(
                event_type=AuditEventType.HINDSIGHT_RETAIN,
                actor=document.owner,
                subject=document.source_id,
                detail=(
                    f"Retained '{document.title}' into Hindsight bank "
                    f"{self.engine.bank_id}"
                ),
                payload={
                    "document_id": document.document_id,
                    "source_type": document.source_type,
                    "items_count": retain_resp.get("items_count"),
                    "approved_claims": len(approved),
                    "rejected_claims": len(result.rejected),
                    "engine_mode": result.engine_mode,
                    "simulated": bool(retain_resp.get("simulated")),
                },
            )
        except MemoryEngineUnavailable as exc:
            result.error = str(exc)
            self._audit(
                event_type=AuditEventType.HINDSIGHT_RETAIN,
                actor=document.owner,
                subject=document.source_id,
                detail=f"Hindsight retain failed: {exc}",
                payload={"error": str(exc)},
            )
            return result

        # 3. Link the Hindsight fact ids so provenance is real, not implied.
        if not result.hindsight_fact_ids:
            linked = await self._link_facts(document)
            result.hindsight_fact_ids = linked

        # 4. Persist the approved claims as governed application memories.
        for claim, gate in approved:
            memory = self._persist_claim(
                claim=claim,
                document=document,
                gate=gate,
                hindsight_fact_ids=result.hindsight_fact_ids,
                owner_actor=owner_actor,
                auto_confirm=auto_confirm,
            )
            result.memories.append(memory)

        result.engine_simulated = self.engine.active.simulated
        result.engine_mode = self.engine.active.mode
        result.duration_ms = int((time.perf_counter() - started) * 1000)

        self.db.add_learning_event(
            LearningEvent(
                id=new_id("lev"),
                kind="memory_captured",
                message=(
                    f"New {document.source_type.replace('_', ' ')} captured: "
                    f"{document.title}"
                ),
                detail=f"{len(result.memories)} memory item(s) approved by the Memory Gate.",
                memory_id=result.memories[0].id if result.memories else None,
            )
        )
        return result

    @staticmethod
    def _retainable_text(approved: list[tuple[ExtractedClaim, MemoryGateDecision]]) -> str:
        """The exact text handed to the memory engine.

        Only gate-approved claim text is included, so Hindsight never stores
        something the Memory Gate would refuse to surface.
        """
        lines: list[str] = []
        for claim, _gate in approved:
            lines.append(f"{claim.title}. {claim.content}".strip())
        return "\n".join(lines)

    async def _link_facts(self, document: SourceDocument) -> list[str]:
        """Ask Hindsight which facts it produced for this document.

        In live mode the retain response does not enumerate fact ids, so we look
        them up. The bank + document id filter keeps this precise.
        """
        try:
            facts = await self.engine.active.alist_memories(limit=1000)
        except MemoryEngineUnavailable:
            return []
        return [
            f.id
            for f in facts
            if f.document_id == document.document_id
        ][:20]

    def _persist_claim(
        self,
        *,
        claim: ExtractedClaim,
        document: SourceDocument,
        gate: MemoryGateDecision,
        hindsight_fact_ids: list[str],
        owner_actor: Actor,
        auto_confirm: bool,
    ) -> MemoryRecord:
        visibility = Visibility(claim.visibility or document.visibility)
        policy = self.resolver.policy_for(visibility)
        now = document.observed_at or utcnow()
        memory_id = stable_id("mem", document.source_id, claim.title)

        memory = MemoryRecord(
            id=memory_id,
            type=MemoryType(claim.type),
            title=claim.title,
            content=claim.content,
            summary=claim.summary or truncate(claim.content, 160),
            source_type=document.source_type,
            source_id=document.source_id,
            source_name=document.source_name,
            captured_at=document.captured_at or now,
            observed_at=claim.observed_at or document.observed_at or now,
            scope=claim.scope or document.scope,
            owner=claim.owner or document.owner,
            domain=claim.domain or document.domain,
            purpose=claim.purpose or document.purpose,
            created_at=now,
            last_validated_at=now if auto_confirm else None,
            expiry_at=self.resolver.expiry_for(visibility, now),
            confidence=claim.confidence_hint or 0.5,
            evidence_count=0,
            status=MemoryStatus.CREATED,
            sensitivity=(
                Sensitivity.CONFIDENTIAL
                if any(h in claim.content.lower() for h in SENSITIVE_HINTS)
                else policy.default_sensitivity
            ),
            access_level=policy.default_access_level,
            visibility=visibility,
            related_entities=sorted(
                set(claim.entities) | set(document.entities)
            ),
            hindsight_fact_id=hindsight_fact_ids[0] if hindsight_fact_ids else None,
            hindsight_document_id=document.document_id,
            gate=gate,
            human_confirmed=auto_confirm,
            tags=sorted(set(document.tags) | set(claim.tags)),
            extra={
                "team": document.team,
                "document_id": document.document_id,
                "claim_type": str(claim.type),
                "source_metadata": document.metadata,
                "synthetic": True,
            },
        )

        # Evidence links.
        for ev_type, ev_id, detail in claim.evidence_refs:
            self.db.add_evidence(
                EvidenceLink(
                    memory_id=memory.id,
                    evidence_type=ev_type,
                    evidence_id=ev_id,
                    evidence_label=f"{ev_type} {ev_id}",
                    detail=detail,
                )
            )
        self.db.refresh_evidence_counts()
        memory.evidence_count = sum(
            1
            for link in self.db.evidence_for(memory.id)
            if link.polarity == "supports"
        )

        # Lifecycle: the promotion to ACTIVE is explicit, never automatic for
        # PERSONAL memory.
        event = apply_transition(
            memory,
            MemoryStatus.CONFIRMED if auto_confirm else MemoryStatus.CREATED,
            actor=owner_actor.id,
            action="captured" if not auto_confirm else "captured_and_confirmed",
            note=f"Ingested from {document.source_name}.",
            payload={"gate_decision": gate.decision},
        )
        if not auto_confirm and visibility == Visibility.ORGANIZATION:
            event = apply_transition(
                memory,
                MemoryStatus.ACTIVE,
                actor="system",
                action="activated",
                note="Organizational evidence is active on ingest.",
            )
        elif not auto_confirm:
            event = apply_transition(
                memory,
                MemoryStatus.CREATED,
                actor="system",
                action="awaiting_review",
                note="Awaiting human review before promotion.",
            )

        self.confidence.refresh(memory)
        self.db.upsert_memory(memory)
        for e in [event]:
            self.db.add_memory_event(e)
        if not auto_confirm:
            self.db.add_memory_event(
                MemoryEvent(
                    id=new_id("mev"),
                    memory_id=memory.id,
                    from_status=MemoryStatus.CREATED,
                    to_status=MemoryStatus.CREATED,
                    action="gate",
                    actor="memory-gate",
                    note="; ".join(gate.reasons),
                    payload={"decision": gate.decision},
                )
            )

        self._audit(
            event_type=AuditEventType.MEMORY_CAPTURED,
            actor=owner_actor.id,
            subject=memory.title,
            memory_id=memory.id,
            detail=(
                f"Captured {memory.type} '{memory.title}' from "
                f"{document.source_name} (visibility {memory.visibility})."
            ),
            payload={
                "source_type": document.source_type,
                "source_id": document.source_id,
                "evidence_count": memory.evidence_count,
                "confidence": memory.confidence,
            },
        )
        self.db.bump_metric("memories_created")
        return memory

    # --- bulk ----------------------------------------------------------
    async def ingest_all(
        self,
        documents: list[SourceDocument],
        *,
        owner_actor: Actor | None = None,
        auto_confirm: bool = False,
    ) -> list[IngestionResult]:
        results: list[IngestionResult] = []
        for doc in documents:
            results.append(
                await self.ingest(doc, owner_actor=owner_actor, auto_confirm=auto_confirm)
            )
        return results


async def maybe_await(value: Any) -> Any:
    if asyncio.iscoroutine(value):
        return await value
    return value


__all__ = ["IngestionResult", "MemoryIngestionService"]
