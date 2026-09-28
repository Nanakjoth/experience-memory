"""Architecture / change record adapter.

The channel that proves memory can become wrong. A change that lands in a scope
does not delete the lesson; it triggers contradiction detection.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.models.memory import MemoryType, Visibility
from backend.seed.novatech import ARCHITECTURE_CHANGES
from backend.sources.base import ExtractedClaim, KnowledgeSource, SourceDocument


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def build_change_document(change: dict) -> SourceDocument:
    component = change["component"]
    old_scope = change.get("invalidates_scope")
    claims = [
        ExtractedClaim(
            type=MemoryType.EVENT,
            title=f"{change['id']}: {change['title']}",
            content=(
                f"{change['title']}. {change['summary']} Effective "
                f"{change['effective_at']}."
            ),
            summary=change["summary"][:200],
            scope=component,
            owner="Platform Architecture",
            domain=change["system"].split()[0].lower(),
            purpose="Keep the current environment description accurate.",
            entities=[change["id"], change["system"], component],
            visibility=Visibility.ORGANIZATION,
            observed_at=_parse(change["effective_at"]),
            evidence_refs=[("architecture_change", change["id"], change["title"])],
        )
    ]
    if old_scope:
        claims.append(
            ExtractedClaim(
                type=MemoryType.CORRECTION,
                title=f"Previously learned {old_scope} procedure must be re-validated",
                content=(
                    f"{change['summary']} Historical knowledge scoped to {old_scope} must "
                    f"not be applied automatically to {component}. Validate the new "
                    "operational procedure before acting on the old lesson."
                ),
                summary=f"Explicit invalidation signal for knowledge scoped to {old_scope}.",
                scope=component,
                owner="Platform Architecture",
                domain=change["system"].split()[0].lower(),
                purpose="Prevent stale scoped knowledge from being applied blindly.",
                entities=[change["id"], old_scope, component],
                visibility=Visibility.ORGANIZATION,
                observed_at=_parse(change["effective_at"]),
                evidence_refs=[("architecture_change", change["id"], "scope change")],
            )
        )
    return SourceDocument(
        source_type="architecture_change",
        source_id=change["id"],
        source_name=f"{change['id']} architecture change",
        title=change["title"],
        content=f"{change['title']}. {change['summary']}",
        context=f"{change['system']} change record",
        document_id=f"doc-{change['id']}",
        scope=component,
        owner="Platform Architecture",
        team=change["system"].split()[0] + " Operations",
        domain=change["system"].split()[0].lower(),
        purpose="Record environment change so scoped memory can be re-validated.",
        claims=claims,
        observed_at=_parse(change["effective_at"]),
        captured_at=_parse(change["effective_at"]),
        visibility=Visibility.ORGANIZATION,
        entities=[change["id"], change["system"], component],
        tags=["architecture", "change"],
        is_operational=True,
        metadata={
            "invalidates_scope": old_scope or "",
            "effective_at": change["effective_at"],
        },
    )


class ArchitectureChangeSource(KnowledgeSource):
    source_type = "architecture_change"
    display_name = "Architecture / change record"

    def __init__(self, changes: list[dict] | None = None) -> None:
        self.changes = changes if changes is not None else list(ARCHITECTURE_CHANGES)

    def available(self) -> bool:
        return bool(self.changes)

    def documents(self) -> list[SourceDocument]:
        return [build_change_document(c) for c in self.changes]


__all__ = ["ArchitectureChangeSource", "build_change_document"]
