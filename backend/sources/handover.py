"""Handover document adapter.

A departing owner's written note. This is where the personal/organizational
boundary becomes concrete: the note contains a personal preference that must be
retained as PERSONAL and never surface through an organizational question.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.models.memory import MemoryType, Visibility
from backend.seed.novatech import HANDOVER_DOCUMENTS
from backend.sources.base import ExtractedClaim, KnowledgeSource, SourceDocument


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


class HandoverDocumentSource(KnowledgeSource):
    source_type = "handover_document"
    display_name = "Handover document"

    def __init__(self, document_id: str | None = None) -> None:
        self.document_id = document_id

    def _select(self) -> list[dict]:
        if self.document_id:
            return [d for d in HANDOVER_DOCUMENTS if d["id"] == self.document_id]
        return list(HANDOVER_DOCUMENTS)

    def available(self) -> bool:
        return bool(self._select())

    def documents(self) -> list[SourceDocument]:
        docs: list[SourceDocument] = []
        for doc in self._select():
            claims: list[ExtractedClaim] = []
            if doc["id"] == "handover-arun-payment":
                # Personal: must never be retrievable as operational knowledge.
                claims.append(
                    ExtractedClaim(
                        type=MemoryType.OBSERVATION,
                        title="Arun prefers to work early in the morning",
                        content=(
                            "Arun prefers to work early in the morning. This is a personal "
                            "working preference and not operationally useful."
                        ),
                        summary="Personal preference. Deliberately never promoted.",
                        scope="Personal",
                        owner=doc["author"],
                        domain="personal",
                        purpose="Personal context only. Must not become organizational memory.",
                        is_operational=False,
                        entities=["Arun"],
                        visibility=Visibility.PERSONAL,
                        observed_at=_parse(doc["created_at"]),
                        tags=["personal"],
                    )
                )
                claims.append(
                    ExtractedClaim(
                        type=MemoryType.COMMITMENT,
                        title="Payment runbook is incomplete on the restart step",
                        content=(
                            "The Payment API runbook instructs a restart on connection-reset "
                            "alerts and does not mention checking the queue first. The runbook "
                            "is owned by another team and has never been corrected."
                        ),
                        summary="The documentation gap that makes this memory necessary.",
                        scope=doc["scope"],
                        owner=doc["author"],
                        domain="payments",
                        purpose="Record why the operational lesson exists at all.",
                        entities=["Payment API", "Payment Queue v1", doc["author"]],
                        visibility=Visibility.PERSONAL,
                        observed_at=_parse(doc["created_at"]),
                    )
                )
            else:
                claims.append(
                    ExtractedClaim(
                        type=MemoryType.LESSON,
                        title=f"{doc['author']} — {doc['system']} handover summary",
                        content=doc["content"],
                        summary=f"Written handover note for {doc['system']}.",
                        scope=doc["scope"],
                        owner=doc["author"],
                        domain=doc["system"].split()[0].lower(),
                        purpose="Carry documented knowledge across a change of owner.",
                        entities=[doc["author"], doc["system"], doc["scope"]],
                        visibility=Visibility.TEAM,
                        observed_at=_parse(doc["created_at"]),
                    )
                )
            docs.append(
                SourceDocument(
                    source_type=self.source_type,
                    source_id=doc["id"],
                    source_name=f"{doc['author']} handover note",
                    title=doc["title"],
                    content=doc["content"],
                    context="Departing owner handover",
                    document_id=f"doc-{doc['id']}",
                    scope=doc["scope"],
                    owner=doc["author"],
                    team=doc["system"].split()[0] + " Operations",
                    domain=doc["system"].split()[0].lower(),
                    purpose="Preserve written knowledge at the point of handover.",
                    claims=claims,
                    observed_at=_parse(doc["created_at"]),
                    captured_at=_parse(doc["created_at"]),
                    visibility=Visibility.PERSONAL,
                    entities=[doc["author"], doc["system"], doc["scope"]],
                    tags=["handover"],
                    is_operational=True,
                    metadata={"author": doc["author"], "role": doc["role"]},
                )
            )
        return docs


__all__ = ["HandoverDocumentSource"]
