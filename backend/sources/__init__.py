"""Source adapter registry.

Adding a real integration (Jira, ServiceNow, transcripts) means implementing
:class:`~backend.sources.base.KnowledgeSource` and registering it here.
"""

from __future__ import annotations

from backend.sources.architecture import ArchitectureChangeSource, build_change_document
from backend.sources.base import ExtractedClaim, KnowledgeSource, SourceDocument
from backend.sources.expert_interview import (
    CAPTURE_PROMPTS,
    TRANSCRIPT_TO_PROMPT,
    ExpertInterviewSource,
)
from backend.sources.handover import HandoverDocumentSource
from backend.sources.incidents import IncidentSource, incident_narrative, incident_summary
from backend.sources.outcomes import OutcomeSource, build_outcome_document

SOURCE_REGISTRY: dict[str, type[KnowledgeSource]] = {
    ExpertInterviewSource.source_type: ExpertInterviewSource,
    IncidentSource.source_type: IncidentSource,
    HandoverDocumentSource.source_type: HandoverDocumentSource,
    OutcomeSource.source_type: OutcomeSource,
    ArchitectureChangeSource.source_type: ArchitectureChangeSource,
}


def all_sources(**kwargs) -> list[KnowledgeSource]:
    """Every adapter, instantiated with the default synthetic dataset."""
    return [
        ExpertInterviewSource(),
        IncidentSource(),
        HandoverDocumentSource(),
        ArchitectureChangeSource(),
        OutcomeSource(),
    ]


__all__ = [
    "CAPTURE_PROMPTS",
    "ArchitectureChangeSource",
    "ExpertInterviewSource",
    "ExtractedClaim",
    "HandoverDocumentSource",
    "IncidentSource",
    "KnowledgeSource",
    "OutcomeSource",
    "SOURCE_REGISTRY",
    "SourceDocument",
    "TRANSCRIPT_TO_PROMPT",
    "all_sources",
    "build_change_document",
    "build_outcome_document",
    "incident_narrative",
    "incident_summary",
]
