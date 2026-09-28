"""Demo orchestration.

Every demo control executes real application functionality against the real
services. There are no fake buttons and no canned answers: the same endpoints
the UI uses are called here.

The 8 controls:

    1. Seed Arun's knowledge
    2. Ask as Maya
    3. Record successful outcome
    4. Introduce Payment Queue v2
    5. Ask the same question again
    6. Show memory evolution
    7. Show privacy boundary
    8. Reset demo

RUN FULL DEMO executes the whole narrative in order and records each step.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable

from backend.agents.successor_agent import DEFAULT_QUESTION
from backend.db.database import Database
from backend.models.audit import AuditEvent, AuditEventType
from backend.models.memory import LearningEvent, Visibility, utcnow
from backend.models.permissions import Actor
from backend.actors import DEMO_ACTORS
from backend.seed.novatech import COMPANY, SYNTHETIC_BANNER
from backend.services import Services
from backend.sources.architecture import ArchitectureChangeSource
from backend.sources.expert_interview import ExpertInterviewSource
from backend.sources.handover import HandoverDocumentSource
from backend.sources.incidents import IncidentSource
from backend.sources.outcomes import build_outcome_document
from backend.utils import new_id, truncate

PAYMENT_INCIDENTS = ["INC-1042", "INC-1088", "INC-1104", "INC-1111"]

DEMO_CONTROL_LABELS: dict[str, dict[str, str]] = {
    "1": {
        "label": "Seed Arun's Knowledge",
        "narration": "Experienced engineers teach MemoryOS what the runbook leaves out.",
    },
    "2": {
        "label": "Ask as Maya",
        "narration": "A new engineer asks. The agent answers from historical experience.",
    },
    "3": {
        "label": "Record Successful Outcome",
        "narration": "The outcome is retained, so the organization remembers the win.",
    },
    "4": {
        "label": "Introduce Queue v2",
        "narration": "The environment changes. Old knowledge stops being automatically true.",
    },
    "5": {
        "label": "Ask Same Question Again",
        "narration": "The same question now produces a different, more careful answer.",
    },
    "6": {
        "label": "Show Memory Evolution",
        "narration": "History is preserved. Scope is narrowed, not deleted.",
    },
    "7": {
        "label": "Show Privacy Boundary",
        "narration": "Personal memory is never retrievable as organizational knowledge.",
    },
    "8": {
        "label": "Reset Demo",
        "narration": "Clears all synthetic state so the demo can be run again.",
    },
}

#: Maps each numbered control to the endpoint that performs it. The UI uses the
#: key to call the API, so the button and the backend can never drift apart.
DEMO_CONTROL_KEYS: dict[str, str] = {
    "1": "seed",
    "2": "ask",
    "3": "outcome",
    "4": "queue-v2",
    "5": "ask",
    "6": "evolution",
    "7": "privacy",
    "8": "reset",
}

FULL_DEMO_SCRIPT: list[dict[str, str]] = [    {
        "key": "reset",
        "title": "Reset demo state",
        "narration": "Starting from a clean organization with no captured experience.",
    },
    {
        "key": "seed_incidents",
        "title": "Seed historical incidents",
        "narration": "Four Payment Platform incidents enter the memory bank as evidence.",
    },
    {
        "key": "capture_arun",
        "title": "Capture Arun's lesson",
        "narration": "The expert interview becomes EXPERIENCE, LESSON, EXCEPTION, RELATIONSHIP and FACT.",
    },
    {
        "key": "ask_without_memory",
        "title": "Ask before the expert lesson",
        "narration": "With only incident records and no lesson, the answer is generic.",
    },
    {
        "key": "show_baseline",
        "title": "Show the baseline",
        "narration": "Before MemoryOS: a generic recommendation with no organizational evidence.",
    },
    {
        "key": "promote_lesson",
        "title": "Promote the lesson to organizational knowledge",
        "narration": "Explicit human promotion. Nothing is promoted automatically.",
    },
    {
        "key": "ask_with_memory",
        "title": "Ask again with accumulated memory",
        "narration": "Now the answer is evidence-backed, scoped and confidence-rated.",
    },
    {
        "key": "record_outcome",
        "title": "Record the outcome",
        "narration": "A new observation strengthens the organizational memory.",
    },
    {
        "key": "queue_v2",
        "title": "Introduce Payment Queue v2",
        "narration": "An architecture change invalidates the assumption behind the lesson.",
    },
    {
        "key": "ask_after_change",
        "title": "Ask the same question again",
        "narration": "The agent refuses to blindly apply the historical lesson.",
    },
    {
        "key": "detect_stale",
        "title": "Detect stale knowledge",
        "narration": "A potential contradiction is raised for human review, not auto-resolved.",
    },
    {
        "key": "update_scope",
        "title": "Restrict the memory scope",
        "narration": "Payment Queue v1 keeps its lesson. Queue v2 requires validation.",
    },
    {
        "key": "final_dashboard",
        "title": "Show the final dashboard",
        "narration": "Metrics are real application events, not fabricated numbers.",
    },
]

BEFORE_ANSWER = {
    "source": "Documented runbook (no organizational memory)",
    "text": (
        "Restart the Payment API and monitor the connection-reset alerts. If the "
        "alerts persist after a restart, check the Payment Queue and escalate to "
        "Payments Operations."
    ),
    "sections": [],
    "has_evidence": False,
    "has_scope": False,
    "has_confidence": False,
}


@dataclass
class StepLog:
    index: int
    key: str
    title: str
    narration: str
    status: str = "ok"
    duration_ms: int = 0
    payload: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "key": self.key,
            "title": self.title,
            "narration": self.narration,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "payload": self.payload or {},
            "error": self.error,
        }


class DemoOrchestrator:
    def __init__(self, services: Services) -> None:
        self.s = services
        self.db: Database = services.db
        self.runs: dict[str, list[StepLog]] = {}

    # --- registry ------------------------------------------------------
    def registry(self) -> list[dict[str, str]]:
        return [
            {"step": k, "key": DEMO_CONTROL_KEYS[k], **v}
            for k, v in sorted(DEMO_CONTROL_LABELS.items(), key=lambda kv: int(kv[0]))
        ]

    # --- reset ---------------------------------------------------------
    def reset(self) -> dict[str, Any]:
        self.db.reset()
        self.s.engine.simulated.reset()
        self._seed_reference_data()
        self.db.add_audit(
            AuditEvent(
                id=new_id("aud"),
                event_type=AuditEventType.DEMO_RESET,
                actor="demo",
                detail="Demo state reset. All synthetic memories, evidence and audit rows cleared.",
            )
        )
        self.db.add_learning_event(
            LearningEvent(
                id=new_id("lev"),
                kind="demo_reset",
                message="Demo reset. The organization starts with no captured experience.",
                detail=SYNTHETIC_BANNER,
                synthetic=True,
            )
        )
        return {
            "ok": True,
            "message": "Demo reset. Reference catalogue restored, memory bank emptied.",
            "memories": 0,
        }

    def _seed_reference_data(self) -> None:
        """Employees, systems, incidents and change records.

        These are reference data (like a CMDB), not memory. Seeding them on
        reset keeps the UI populated without pretending the organization has
        captured any experience yet.
        """
        for system in COMPANY["systems"]:
            self.db.upsert_system(system)
        for emp in COMPANY["employees"]:
            self.db.upsert_employee(emp)
        for inc in INCIDENT_SOURCE_DOCUMENTS_METADATA():
            self.db.upsert_incident(inc)
        for change in ArchitectureChangeSource().changes:
            if change["id"] != "ARCH-2026-09-28":
                # Queue v2 is introduced by demo step 4, not by the reset.
                self.db.upsert_architecture_change(change)

    # --- 1. seed -------------------------------------------------------
    async def seed_experience(self) -> dict[str, Any]:
        actor = DEMO_ACTORS["arun"]
        # Incidents first: they are the evidence the lesson will rest on.
        incident_docs = IncidentSource(incident_ids=PAYMENT_INCIDENTS).documents()
        handover_docs = HandoverDocumentSource("handover-arun-payment").documents()
        interview_docs = ExpertInterviewSource("expert-arun-payment").documents()

        results = await self.s.ingestion.ingest_all(
            incident_docs, owner_actor=actor, auto_confirm=True
        )
        handover_results = await self.s.ingestion.ingest_all(
            handover_docs, owner_actor=actor, auto_confirm=True
        )
        interview_results = await self.s.ingestion.ingest_all(
            interview_docs, owner_actor=actor, auto_confirm=False
        )

        # Keep the v2 change out of the initial state.
        self._drop_v2_change()

        return {
            "ok": True,
            "message": (
                f"Captured {len(interview_results[0].memories)} memory items from Arun's "
                f"interview plus {sum(len(r.memories) for r in results + handover_results)} "
                "from incident evidence and handover notes."
            ),
            "payload": {
                "incidents": [d.source_id for d in incident_docs],
                "interview_memories": [
                    {
                        "id": m.id,
                        "type": str(m.type),
                        "title": m.title,
                        "visibility": str(m.visibility),
                        "status": str(m.status),
                        "evidence_count": m.evidence_count,
                    }
                    for m in interview_results[0].memories
                ],
                "rejected": interview_results[0].rejected,
                "engine_mode": self.s.engine.active.mode,
                "engine_simulated": self.s.engine.active.simulated,
            },
        }

    def _drop_v2_change(self) -> None:
        with self.db.cursor() as cur:
            cur.execute("DELETE FROM architecture_changes WHERE id = ?", ("ARCH-2026-09-28",))

    # --- promotion -----------------------------------------------------
    def promote_key_lesson(self) -> dict[str, Any]:
        """Explicit human promotion of the queue-saturation lesson."""
        steward = DEMO_ACTORS["steward"]
        target_id = "mem-lesson-arun-002"
        memory = self.db.get_memory(target_id)
        if memory is None:
            candidates = [
                m
                for m in self.db.all_memories()
                if m.title.startswith("Check queue depth before restarting")
            ]
            if not candidates:
                return {
                    "ok": False,
                    "message": "Key lesson not found. Run 'Seed Arun's Knowledge' first.",
                }
            memory = candidates[0]
        outcome = self.s.governance.promote(
            memory.id, actor=steward, target=Visibility.ORGANIZATION
        )
        # Promote the supporting lesson set as organizational knowledge too.
        for title_prefix in (
            "Restarting Payment API during queue saturation",
            "The 80% threshold is a property",
            "Payments Operations owns queue-related escalation",
            "Payment API depends on Payment Queue v1",
        ):
            for m in self.db.all_memories():
                if m.title.startswith(title_prefix):
                    self.s.governance.promote(
                        m.id,
                        actor=steward,
                        target=Visibility.ORGANIZATION,
                        note="Promoted as part of the reviewed queue-saturation knowledge set.",
                    )
        return {
            "ok": True,
            "message": (
                "Promoted the queue-saturation lesson set to organizational knowledge. "
                "Promotion is always explicit; it never happens automatically."
            ),
            "payload": outcome.to_dict(),
        }

    # --- 2 / 5. ask ----------------------------------------------------
    async def ask_as_maya(self) -> dict[str, Any]:
        maya = DEMO_ACTORS["maya"]
        answer = await self.s.agent.ask(DEFAULT_QUESTION, actor=maya)
        return {
            "ok": True,
            "message": answer.answer.headline,
            "payload": answer.to_dict(),
        }

    # --- 3. outcome ----------------------------------------------------
    async def record_outcome(self) -> dict[str, Any]:
        from backend.api.outcomes import record_outcome as record

        out = await record(
            self.s,
            question=DEFAULT_QUESTION,
            recommendation=(
                "Do not restart the Payment API. Check Payment Queue v1 depth, and if it "
                "is above 80 percent contact Payments Operations before restarting."
            ),
            actual_action="Checked queue depth, contacted Payments Operations, did not restart",
            result="Resolved without restart and without duplicate processing",
            notes=(
                "Queue drained automatically after four minutes. Payments Operations "
                "confirmed the depth was a settlement batch."
            ),
            queue_depth=88,
            scope="Payment Queue v1",
            actor="maya",
            outcome_id=None,
        )
        return {
            "ok": True,
            "message": out["message"],
            "payload": out,
        }

    # --- 4. architecture change ----------------------------------------
    async def introduce_queue_v2(self) -> dict[str, Any]:
        from backend.api.governance import apply_architecture_change

        out = await apply_architecture_change(
            self.s,
            id="ARCH-2026-09-28",
            title="Payment Queue v2 deployed, replacing Payment Queue v1",
            system="Payment Platform",
            component="Payment Queue v2",
            summary=(
                "Payment Queue v2 was deployed and replaced Payment Queue v1. The restart "
                "procedure has changed. The historical Payment Queue v1 lesson must not "
                "automatically be applied to Queue v2. Validate the new operational "
                "procedure with Payments Operations before acting on the historical lesson."
            ),
            invalidates_scope="Payment Queue v1",
        )
        return {
            "ok": True,
            "message": out["message"],
            "payload": out,
        }

    # --- 6. evolution --------------------------------------------------
    def memory_evolution(self) -> dict[str, Any]:
        contradictions = self.db.list_contradictions()
        open_c = [c for c in contradictions if c.status == "REVIEW_REQUIRED"]
        return {
            "ok": True,
            "message": (
                f"{len(open_c)} open contradiction(s) awaiting human review. History is "
                "preserved: nothing was overwritten."
            ),
            "payload": {
                "stages": self.s.governance.evolution_stages(),
                "contradictions": [c.model_dump(mode="json") for c in contradictions],
                "open": len(open_c),
                "resolved": len(contradictions) - len(open_c),
            },
        }

    # --- 7. privacy ---------------------------------------------------
    async def privacy_boundary(self) -> dict[str, Any]:
        maya = DEMO_ACTORS["maya"]
        question = "What does Arun prefer, and how should I restart the Payment API?"
        answer = await self.s.agent.ask(question, actor=maya)
        private = [
            m
            for m in self.db.all_memories()
            if str(m.visibility) == "PERSONAL" and "morning" in m.title.lower()
        ]
        return {
            "ok": True,
            "message": (
                f"{answer.retrieval.withheld and 'Personal memory was withheld.' or 'No personal memory was in scope for this query.'} "
                f"Operational knowledge was still returned."
            ),
            "payload": {
                "question": question,
                "private_memory_present": len(private),
                "private_memory_titles": [m.title for m in private],
                "withheld": answer.retrieval.withheld,
                "operational_memories_returned": [
                    {"id": m.id, "title": m.title, "visibility": str(m.visibility)}
                    for m in answer.retrieval.memories
                ],
                "privacy_notice": answer.privacy_notice,
                "answer": answer.to_dict(),
            },
        }

    # --- full demo -----------------------------------------------------
    async def run_full_demo(self) -> dict[str, Any]:
        run_id = new_id("demo")
        logs: list[StepLog] = []
        state: dict[str, Any] = {}
        started = time.perf_counter()

        async def step(index: int, key: str, fn: Callable[[], Awaitable[dict[str, Any]] | dict[str, Any]], narration: str) -> None:
            t0 = time.perf_counter()
            try:
                out = fn()
                if asyncio.iscoroutine(out):
                    out = await out
                log = StepLog(
                    index=index,
                    key=key,
                    title=FULL_DEMO_SCRIPT[index - 1]["title"],
                    narration=narration,
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                    payload=out.get("payload") or {},
                )
            except Exception as exc:  # noqa: BLE001
                log = StepLog(
                    index=index,
                    key=key,
                    title=FULL_DEMO_SCRIPT[index - 1]["title"],
                    narration=narration,
                    status="error",
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                    error=str(exc),
                )
            logs.append(log)
            self.runs.setdefault(run_id, []).append(log)

        await step(1, "reset", self.reset, "Clean slate.")
        await step(2, "seed_incidents", self.seed_incidents_only, "Incidents become evidence.")
        await step(3, "capture_arun", self.capture_arun_only, "The expert lesson is captured.")
        await step(
            4,
            "ask_without_memory",
            lambda: self.ask_as_maya(),
            "Asked before the lesson was promoted: generic answer.",
        )
        state["baseline"] = {
            "memories_used": len(self.db.all_memories()),
            "before": BEFORE_ANSWER,
        }
        await step(5, "show_baseline", lambda: _ok("Before / after baseline captured."), "Generic recommendation.")
        await step(6, "promote_lesson", self.promote_key_lesson, "Explicit human promotion.")
        await step(7, "ask_with_memory", lambda: self.ask_as_maya(), "Evidence-backed answer.")
        await step(8, "record_outcome", self.record_outcome, "New observation retained.")
        await step(9, "queue_v2", self.introduce_queue_v2, "Environment changed.")
        await step(10, "ask_after_change", lambda: self.ask_as_maya(), "Refuses to apply blindly.")
        await step(11, "detect_stale", self.memory_evolution, "Contradiction raised.")
        await step(12, "update_scope", self._auto_restrict_top_contradiction, "Scope narrowed, history kept.")
        await step(
            13,
            "final_dashboard",
            lambda: _ok("Dashboard metrics are real application events.", self.dashboard_snapshot()),
            "Final state.",
        )

        self.runs[run_id] = logs
        all_ok = all(l.status == "ok" for l in logs)
        self.db.add_audit(
            AuditEvent(
                id=new_id("aud"),
                event_type=AuditEventType.DEMO_STEP,
                actor="demo",
                subject=run_id,
                detail=(
                    f"Full demo completed with {len(logs)} steps."
                    if all_ok
                    else f"Full demo finished with {len(logs)} steps and errors."
                ),
                payload={
                    "status": "ok" if all_ok else "failed",
                    "failed_steps": [l.key for l in logs if l.status != "ok"],
                },
            )
        )
        return {
            "id": run_id,
            "mode": "full",
            "status": "ok" if all_ok else "failed",
            "started_at": (utcnow() - _delta(started)).isoformat(),
            "finished_at": utcnow().isoformat(),
            "steps": [l.to_dict() for l in logs],
            "progress_percent": 100,
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }

    # --- granular steps used by the full demo --------------------------
    async def seed_incidents_only(self) -> dict[str, Any]:
        actor = DEMO_ACTORS["arun"]
        docs = IncidentSource(incident_ids=PAYMENT_INCIDENTS).documents()
        results = await self.s.ingestion.ingest_all(docs, owner_actor=actor, auto_confirm=True)
        return {
            "ok": True,
            "message": f"Retained {len(docs)} incident records into Hindsight.",
            "payload": {
                "incidents": [d.source_id for d in docs],
                "memories": sum(len(r.memories) for r in results),
                "engine_mode": self.s.engine.active.mode,
            },
        }

    async def capture_arun_only(self) -> dict[str, Any]:
        actor = DEMO_ACTORS["arun"]
        docs = ExpertInterviewSource("expert-arun-payment").documents()
        handover = HandoverDocumentSource("handover-arun-payment").documents()
        results = await self.s.ingestion.ingest_all(docs, owner_actor=actor, auto_confirm=False)
        handover_results = await self.s.ingestion.ingest_all(
            handover, owner_actor=actor, auto_confirm=True
        )
        self._drop_v2_change()
        all_memories = [m for r in results + handover_results for m in r.memories]
        return {
            "ok": True,
            "message": (
                f"Hindsight processed the interview into {len(all_memories)} memory "
                "items across 5 memory types."
            ),
            "payload": {
                "extracted": [
                    {
                        "id": m.id,
                        "type": str(m.type),
                        "title": m.title,
                        "status": str(m.status),
                        "visibility": str(m.visibility),
                        "evidence_count": m.evidence_count,
                    }
                    for m in all_memories
                ],
                "rejected": [r.rejected for r in results],
            },
        }

    def _auto_restrict_top_contradiction(self) -> dict[str, Any]:
        open_c = [
            c
            for c in self.db.list_contradictions()
            if c.status == "REVIEW_REQUIRED"
        ]
        if not open_c:
            return {
                "ok": True,
                "message": "No open contradictions to resolve.",
                "payload": {},
            }
        target = open_c[0]
        out = self.s.governance.resolve_contradiction(
            target.id, action="restrict", actor=DEMO_ACTORS["steward"]
        )
        return {
            "ok": True,
            "message": (
                "Scope restricted. Payment Queue v1 keeps its lesson; Payment Queue v2 "
                "requires validation. The original memory text is untouched."
            ),
            "payload": out,
        }

    # --- dashboard snapshot --------------------------------------------
    def dashboard_snapshot(self) -> dict[str, Any]:
        from backend.api.dashboard import build_dashboard

        return build_dashboard(self.s)

    def _step_log(self, index: int, key: str, title: str, narration: str, out: dict[str, Any], ms: int) -> StepLog:
        return StepLog(index=index, key=key, title=title, narration=narration, payload=out.get("payload"))


def _delta(seconds: float):
    from datetime import timedelta

    return timedelta(seconds=seconds)


def _ok(message: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"ok": True, "message": message, "payload": payload or {}}


def INCIDENT_SOURCE_DOCUMENTS_METADATA() -> list[dict[str, Any]]:
    from backend.seed.novatech import INCIDENTS

    return list(INCIDENTS)


__all__ = [
    "BEFORE_ANSWER",
    "DEMO_CONTROL_LABELS",
    "FULL_DEMO_SCRIPT",
    "PAYMENT_INCIDENTS",
    "DemoOrchestrator",
]
