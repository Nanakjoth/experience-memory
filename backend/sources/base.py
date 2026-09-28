"""Knowledge source adapters.

Every input channel in MemoryOS implements :class:`KnowledgeSource`. Adapters are
synthetic for the prototype but the interface is the real extension point, so a
real Jira / ServiceNow / transcript connector would slot in without touching the
memory layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backend.models.memory import MemoryType, Visibility


@dataclass
class ExtractedClaim:
    """One candidate application memory proposed by a source.

    In live mode Hindsight independently extracts facts from the same text; the
    claim is what MemoryOS records on top of that so governance metadata exists.
    """

    type: MemoryType
    title: str
    content: str
    summary: str = ""
    scope: str = ""
    owner: str = ""
    domain: str = ""
    purpose: str = ""
    is_operational: bool = True
    entities: list[str] = field(default_factory=list)
    confidence_hint: float | None = None
    visibility: Visibility | None = None
    tags: list[str] = field(default_factory=list)
    evidence_refs: list[tuple[str, str, str]] = field(default_factory=list)
    observed_at: datetime | None = None


@dataclass
class SourceDocument:
    """A unit of experience handed to the Memory Ingestion Service."""

    source_type: str
    source_id: str
    source_name: str
    title: str
    content: str
    context: str
    document_id: str
    scope: str
    owner: str
    team: str
    domain: str
    purpose: str
    claims: list[ExtractedClaim] = field(default_factory=list)
    observed_at: datetime | None = None
    captured_at: datetime | None = None
    visibility: Visibility = Visibility.ORGANIZATION
    entities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    is_operational: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def retain_metadata(self) -> dict[str, str]:
        """Flat metadata handed to Hindsight ``retain``."""
        md = {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "scope": self.scope,
            "owner": self.owner,
            "domain": self.domain,
            "purpose": self.purpose,
            "visibility": str(self.visibility),
        }
        for k, v in self.metadata.items():
            if isinstance(v, (str, int, float, bool)):
                md[k] = str(v)
        if self.claims:
            md["memory_type"] = str(self.claims[0].type)
        return md

    def retain_tags(self) -> list[str]:
        tags = [f"source:{self.source_type}", f"scope:{self.scope.replace(' ', '-')}"]
        tags.extend(self.tags)
        return sorted(set(tags))


class KnowledgeSource(ABC):
    """Adapter contract."""

    source_type: str = "unknown"
    display_name: str = "Unknown source"

    @abstractmethod
    def available(self) -> bool:
        """Whether this source can currently produce documents."""

    @abstractmethod
    def documents(self) -> list[SourceDocument]:
        """Produce the synthetic source documents for this channel."""


__all__ = ["ExtractedClaim", "KnowledgeSource", "SourceDocument"]
