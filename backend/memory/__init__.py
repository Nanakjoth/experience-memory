"""MemoryOS memory layer.

Hindsight is the engine; everything else here is the governance envelope around
it: ingestion, retrieval, reflection, confidence, contradiction handling,
lifecycle and provenance.
"""

from backend.memory.confidence import ConfidenceEngine, band_for
from backend.memory.contradiction import (
    RESOLUTION_ACTIONS,
    ContradictionDetector,
    scope_changed,
)
from backend.memory.governance import GovernanceService, MemoryNotFound
from backend.memory.hindsight_client import (
    BANK_DIRECTIVES,
    BANK_DISPOSITION,
    BANK_MISSION,
    EngineManager,
    HindsightEngine,
    MemoryEngine,
    MemoryEngineUnavailable,
    SimulatedHindsightEngine,
    get_engine_manager,
    reset_engine_manager,
)
from backend.memory.ingestion import IngestionResult, MemoryIngestionService
from backend.memory.lifecycle import apply_transition, stage_progress
from backend.memory.provenance import provenance_view
from backend.memory.reflection import ReflectionService, needs_reflection
from backend.memory.retrieval import RetrievalService

__all__ = [
    "BANK_DIRECTIVES",
    "BANK_DISPOSITION",
    "BANK_MISSION",
    "ContradictionDetector",
    "ConfidenceEngine",
    "EngineManager",
    "GovernanceService",
    "HindsightEngine",
    "IngestionResult",
    "MEMORY_LAYER",
    "MemoryEngine",
    "MemoryEngineUnavailable",
    "MemoryIngestionService",
    "MemoryNotFound",
    "RESOLUTION_ACTIONS",
    "ReflectionService",
    "RetrievalService",
    "SimulatedHindsightEngine",
    "apply_transition",
    "band_for",
    "get_engine_manager",
    "needs_reflection",
    "provenance_view",
    "reset_engine_manager",
    "scope_changed",
    "stage_progress",
]

MEMORY_LAYER = "hindsight"
