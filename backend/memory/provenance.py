"""Source provenance.

Every memory answers: where did this come from, when was it observed, and what
type of source produced it. Provenance is stored alongside the Hindsight
reference because Hindsight does not carry MemoryOS governance metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.models.memory import MemoryRecord, SourceProvenance, utcnow

SOURCE_TYPE_LABELS: dict[str, str] = {
    "expert_interview": "Expert interview",
    "incident": "Incident record",
    "handover_document": "Handover document",
    "outcome": "Outcome feedback",
    "architecture_change": "Architecture / change record",
    "agent_synthesis": "Agent synthesis",
}

SOURCE_RELIABILITY_NOTE: dict[str, str] = {
    "expert_interview": "First-hand account from the person who did the work.",
    "incident": "Machine-generated incident record with timestamps and metrics.",
    "handover_document": "Written by a departing owner; may be incomplete.",
    "outcome": "Observed result of acting on a recommendation.",
    "architecture_change": "Authoritative statement about the running system.",
    "agent_synthesis": "Derived by the agent. Requires human confirmation.",
}


@dataclass
class ProvenanceView:
    source_type: str
    source_type_label: str
    source_id: str
    source_name: str
    captured_at: str
    observed_at: str | None
    reliability_note: str
    hindsight_fact_id: str | None
    hindsight_document_id: str | None
    version: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_type_label": self.source_type_label,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "captured_at": self.captured_at,
            "observed_at": self.observed_at,
            "reliability_note": self.reliability_note,
            "hindsight_fact_id": self.hindsight_fact_id,
            "hindsight_document_id": self.hindsight_document_id,
            "version": self.version,
        }


def build_provenance(memory: MemoryRecord) -> SourceProvenance:
    return SourceProvenance(
        source_type=memory.source_type,
        source_id=memory.source_id,
        source_name=memory.source_name,
        captured_at=memory.captured_at,
        observed_at=memory.observed_at,
    )


def provenance_view(memory: MemoryRecord) -> ProvenanceView:
    return ProvenanceView(
        source_type=memory.source_type,
        source_type_label=SOURCE_TYPE_LABELS.get(
            memory.source_type, memory.source_type.replace("_", " ").title()
        ),
        source_id=memory.source_id,
        source_name=memory.source_name,
        captured_at=memory.captured_at.isoformat(),
        observed_at=memory.observed_at.isoformat() if memory.observed_at else None,
        reliability_note=SOURCE_RELIABILITY_NOTE.get(
            memory.source_type, "Source of unknown reliability."
        ),
        hindsight_fact_id=memory.hindsight_fact_id,
        hindsight_document_id=memory.hindsight_document_id,
        version=memory.version,
    )


def source_label(source_type: str) -> str:
    return SOURCE_TYPE_LABELS.get(source_type, source_type.replace("_", " ").title())


__all__ = [
    "ProvenanceView",
    "SOURCE_RELIABILITY_NOTE",
    "SOURCE_TYPE_LABELS",
    "build_provenance",
    "provenance_view",
    "source_label",
    "utcnow",
]
