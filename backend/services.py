"""Service container.

One place that wires the database, the memory engine, the resolver and every
service, so routes and tests share the same object graph.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from backend.agents.successor_agent import SuccessorAgent
from backend.config import Settings, get_settings
from backend.db.database import Database, get_db
from backend.memory.confidence import ConfidenceEngine
from backend.memory.contradiction import ContradictionDetector
from backend.memory.governance import GovernanceService
from backend.memory.hindsight_client import EngineManager, get_engine_manager
from backend.memory.ingestion import MemoryIngestionService
from backend.memory.retrieval import RetrievalService
from backend.models.permissions import MemoryResolver


@dataclass
class Services:
    settings: Settings
    db: Database
    engine: EngineManager
    resolver: MemoryResolver
    confidence: ConfidenceEngine
    ingestion: MemoryIngestionService
    retrieval: RetrievalService
    governance: GovernanceService
    agent: SuccessorAgent
    contradictions: ContradictionDetector

    @classmethod
    def build(
        cls,
        settings: Settings | None = None,
        db: Database | None = None,
        engine: EngineManager | None = None,
    ) -> "Services":
        settings = settings or get_settings()
        db = db or get_db()
        engine = engine or get_engine_manager()
        resolver = MemoryResolver()
        confidence = ConfidenceEngine()
        ingestion = MemoryIngestionService(db, engine, resolver)
        retrieval = RetrievalService(db, engine, resolver)
        governance = GovernanceService(db, resolver)
        agent = SuccessorAgent(db, engine, resolver)
        contradictions = ContradictionDetector()
        return cls(
            settings=settings,
            db=db,
            engine=engine,
            resolver=resolver,
            confidence=confidence,
            ingestion=ingestion,
            retrieval=retrieval,
            governance=governance,
            agent=agent,
            contradictions=contradictions,
        )

    def describe(self) -> dict[str, Any]:
        status = self.engine.status()
        return {
            "memory_engine": "hindsight",
            "bank_id": status.bank_id,
            "mode": status.mode,
            "simulated": status.simulated,
            "degraded_reason": status.reason,
            "checked_at": status.checked_at,
        }

    def reset_for_tests(self) -> None:
        """Drop all application state and clear the memory engine.

        Used by the demo reset endpoint and by the test suite. It never touches a
        real Hindsight server: when Hindsight is live its bank contents are left
        alone, so a live run accumulates history rather than pretending to erase
        it.
        """
        self.db.reset()
        self.engine.clear_local()


@lru_cache(maxsize=1)
def get_services() -> Services:
    return Services.build()


def reset_services() -> None:
    get_services.cache_clear()


__all__ = ["Services", "get_services", "reset_services"]
