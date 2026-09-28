"""Outcome feedback adapter.

The outcome of acting on a recommendation is the loop closer: it is retained as
a new observation so the organization gets stronger with use.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.models.memory import MemoryType, Visibility
from backend.sources.base import ExtractedClaim, KnowledgeSource, SourceDocument


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def build_outcome_document(
    *,
    outcome_id: str,
    question: str,
    recommendation: str,
    actual_action: str,
    result: str,
    notes: str,
    actor: str,
    scope: str,
    queue_depth: float | None,
    observed_at: datetime | None = None,
    source_type: str = "outcome",
    source_name: str | None = None,
    recommendation_ref: str | None = None,
) -> SourceDocument:
    """Turn a submitted outcome into a retainable source document."""
    observed = observed_at or datetime.now(timezone.utc)
    successful = "without" in result.lower() and (
        "duplicate" in result.lower() or "restart" in result.lower()
    )
    if "duplicate" in result.lower() and "without" not in result.lower():
        successful = False

    content_lines = [
        f"Outcome record {outcome_id} for the Payment Platform.",
        f"Question asked: {question}",
        f"Recommendation followed: {recommendation}",
        f"Actual action taken: {actual_action}",
        f"Result: {result}",
        f"Recorded by: {actor}.",
    ]
    if queue_depth is not None:
        content_lines.insert(0, f"Payment Queue v1 depth at decision time: {queue_depth} percent.")
    if notes:
        content_lines.append(f"Notes: {notes}")
    content_lines.append(
        "This outcome is a new observation of what the organization actually did."
    )

    claim_type = MemoryType.LESSON if successful else MemoryType.CORRECTION
    claim_title = (
        f"Outcome {outcome_id}: following the recommendation worked"
        if successful
        else f"Outcome {outcome_id}: following the recommendation did not work"
    )
    return SourceDocument(
        source_type=source_type,
        source_id=outcome_id,
        source_name=source_name or f"Outcome {outcome_id}",
        title=claim_title,
        content="\n".join(content_lines),
        context="Outcome of acting on an agent recommendation",
        document_id=f"doc-{outcome_id}",
        scope=scope,
        owner=actor,
        team="Payments Operations",
        domain="payments",
        purpose="Convert a result into organizational experience.",
        claims=[
            ExtractedClaim(
                type=claim_type,
                title=claim_title,
                content=(
                    f"{actor} asked: '{question}'. Action taken: {actual_action}. "
                    f"Result: {result}. Queue depth at decision time: "
                    f"{queue_depth if queue_depth is not None else 'not recorded'} percent."
                ),
                summary=result,
                scope=scope,
                owner=actor,
                domain="payments",
                purpose="Strengthen or correct the memory that produced the recommendation.",
                entities=[scope, "Payment API", outcome_id],
                visibility=Visibility.ORGANIZATION,
                observed_at=observed,
                confidence_hint=0.9 if successful else 0.6,
                evidence_refs=[("outcome", outcome_id, result)],
            )
        ],
        observed_at=observed,
        captured_at=observed,
        visibility=Visibility.ORGANIZATION,
        entities=[scope, "Payment API", outcome_id, actor],
        tags=["outcome"],
        is_operational=True,
        metadata={
            "queue_depth": queue_depth if queue_depth is not None else "",
            "successful": int(successful),
            "recommendation_ref": recommendation_ref or "",
        },
    )


class OutcomeSource(KnowledgeSource):
    """Replays previously recorded outcomes. Live outcomes arrive via the API."""

    source_type = "outcome"
    display_name = "Outcome feedback"

    def __init__(self, outcomes: list[dict[str, Any]] | None = None) -> None:
        self.outcomes = outcomes or []

    def available(self) -> bool:
        return bool(self.outcomes)

    def documents(self) -> list[SourceDocument]:
        docs: list[SourceDocument] = []
        for o in self.outcomes:
            docs.append(
                build_outcome_document(
                    outcome_id=o["id"],
                    question=o.get("question", ""),
                    recommendation=o.get("recommendation", ""),
                    actual_action=o.get("actual_action", ""),
                    result=o.get("result", ""),
                    notes=o.get("notes", ""),
                    actor=o.get("actor", "Unknown"),
                    scope=o.get("scope", "Payment Queue v1"),
                    queue_depth=o.get("queue_depth"),
                    observed_at=_parse(o["observed_at"]) if o.get("observed_at") else None,
                )
            )
        return docs


__all__ = ["OutcomeSource", "build_outcome_document"]
