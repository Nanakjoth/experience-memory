"""Contradiction detection.

The central claim of MemoryOS: new evidence does not erase old knowledge. It
produces a REVIEW_REQUIRED state that a human resolves by confirming, restricting
the scope, updating, or marking the old memory stale.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.models.memory import Contradiction, MemoryRecord, MemoryStatus, utcnow
from backend.utils import content_tokens, new_id, stable_id, truncate

#: Phrases in an architecture change that mean "previously learned procedure
#: may no longer hold".
INVALIDATION_MARKERS = (
    "no longer",
    "must not automatically",
    "changed",
    "deprecated",
    "replaced",
    "invalidated",
    "do not apply",
    "superseded",
    "new procedure",
    "requires validation",
    "is not valid",
)


@dataclass
class ScopeDrift:
    memory_id: str
    memory_title: str
    old_scope: str
    new_scope: str
    reason: str


def component_family(scope: str) -> str:
    """'Payment Queue v1' -> 'payment queue'."""
    cleaned = scope.lower()
    for suffix in (" v1", " v2", " v3", " 1", " 2", " 3"):
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)]
    return cleaned.strip()


def scope_changed(old_scope: str, new_scope: str) -> bool:
    return component_family(old_scope) == component_family(new_scope) and old_scope != new_scope


def expresses_invalidation(text: str) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in INVALIDATION_MARKERS)


class ContradictionDetector:
    """Compares incoming evidence against active memories."""

    def detect_against_change(
        self,
        *,
        memories: list[MemoryRecord],
        current_scope: str,
        new_scope: str,
        change_source_id: str,
        change_source_type: str,
        change_content: str,
    ) -> list[Contradiction]:
        """An architecture/environment change invalidates scoped knowledge.

        Only memories whose scope belongs to the same component family are
        flagged; unrelated knowledge is left alone.
        """
        found: list[Contradiction] = []
        invalidates = expresses_invalidation(change_content)
        for mem in memories:
            if not mem.is_usable():
                continue
            if not scope_changed(mem.scope, new_scope):
                continue
            reason = (
                f"Memory scope '{mem.scope}' was recorded against a previous "
                f"environment. The active component is now '{new_scope}'. "
                + (
                    "The change explicitly states the old procedure must not be "
                    "applied automatically."
                    if invalidates
                    else "Applicability must be re-validated."
                )
            )
            found.append(
                Contradiction(
                    id=stable_id(
                        "ctr",
                        mem.id,
                        change_source_id,
                        new_scope,
                    ),
                    memory_id=mem.id,
                    memory_title=mem.title,
                    memory_scope=mem.scope,
                    conflicting_source_id=change_source_id,
                    conflicting_source_type=change_source_type,
                    conflicting_content=truncate(change_content, 400),
                    current_environment=new_scope,
                    reason=reason,
                )
            )
        return found

    def detect_against_outcome(
        self,
        *,
        memory: MemoryRecord,
        outcome_text: str,
        outcome_source_id: str,
        successful: bool,
    ) -> Contradiction | None:
        """A failed outcome that followed a memory's guidance contradicts it."""
        if successful:
            return None
        tokens = set(content_tokens(memory.content)) | set(content_tokens(memory.title))
        tokens |= set(content_tokens(memory.scope))
        outcome_tokens = set(content_tokens(outcome_text))
        shared = tokens & outcome_tokens
        overlap = len(shared) / (len(tokens) or 1)
        if not shared or len(shared) < 2 and overlap < 0.18:
            return None
        return Contradiction(
            id=stable_id("ctr", memory.id, outcome_source_id),
            memory_id=memory.id,
            memory_title=memory.title,
            memory_scope=memory.scope,
            conflicting_source_id=outcome_source_id,
            conflicting_source_type="outcome",
            conflicting_content=truncate(outcome_text, 400),
            current_environment=memory.scope,
            reason=(
                f"Following this memory produced an unsuccessful outcome "
                f"({int(overlap * 100)}% content overlap: "
                f"{', '.join(sorted(shared)[:6])}). The recommendation may "
                "no longer hold."
            ),
        )

    def scope_drift(
        self, memories: list[MemoryRecord], new_scope: str
    ) -> list[ScopeDrift]:
        return [
            ScopeDrift(
                memory_id=m.id,
                memory_title=m.title,
                old_scope=m.scope,
                new_scope=new_scope,
                reason=(
                    f"Environment moved from {m.scope} to {new_scope}. This memory "
                    "no longer describes the running system unless re-validated."
                ),
            )
            for m in memories
            if m.is_usable() and scope_changed(m.scope, new_scope)
        ]


RESOLUTION_ACTIONS: dict[str, dict[str, str]] = {
    "confirm": {
        "label": "Confirm old memory",
        "description": (
            "The procedure is unchanged. Keep the memory ACTIVE and record that it "
            "was re-validated against the new environment."
        ),
        "resulting_status": str(MemoryStatus.REVALIDATED),
    },
    "restrict": {
        "label": "Restrict scope",
        "description": (
            "Keep the lesson, but only for the old environment. It stays available "
            "as historical knowledge and no longer applies to the new one. The "
            "lifecycle status is left unchanged."
        ),
        "resulting_status": "unchanged",
    },
    "update": {
        "label": "Update memory",
        "description": (
            "Add a correction that supersedes the old guidance. The original text "
            "is preserved in the history."
        ),
        "resulting_status": str(MemoryStatus.UPDATED),
    },
    "stale": {
        "label": "Mark stale",
        "description": (
            "Retire the memory pending re-validation. It is preserved but no longer "
            "surfaced as current guidance."
        ),
        "resulting_status": str(MemoryStatus.STALE),
    },
}


def new_contradiction_id(memory_id: str, source_id: str, new_scope: str) -> str:
    return new_id("ctr") if not memory_id else stable_id("ctr", memory_id, source_id, new_scope)


__all__ = [
    "ContradictionDetector",
    "INVALIDATION_MARKERS",
    "RESOLUTION_ACTIONS",
    "ScopeDrift",
    "component_family",
    "expresses_invalidation",
    "scope_changed",
]
