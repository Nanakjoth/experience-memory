"""Permission model.

Organizational memory is not employee surveillance. A PERSONAL memory is never
returned by an organizational query, no matter how semantically similar it is.
Promotion from PERSONAL -> TEAM -> ORGANIZATION is always an explicit human act.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from backend.models.memory import (
    AccessLevel,
    MemoryGateDecision,
    MemoryRecord,
    Sensitivity,
    Visibility,
    utcnow,
)

#: Words that indicate the capture is actually a secret. The Memory Gate refuses
#: to store these. This is a prototype heuristic, not a DLP product.
SECRET_PATTERNS: tuple[str, ...] = (
    "password",
    "passwd",
    "api key",
    "api_key",
    "secret key",
    "private key",
    "access token",
    "bearer token",
    "credential",
    "aws_access_key",
    "bearer sk-",
    "-----begin",
    "client_secret",
)


@dataclass(frozen=True)
class Actor:
    """The person or agent making a request."""

    id: str
    display_name: str
    role: str  # e.g. "Senior DevOps Engineer", "Successor Engineer", "System"
    team: str = ""
    visibility_ceiling: Visibility = Visibility.ORGANIZATION

    @property
    def is_system(self) -> bool:
        return self.role == "System"


@dataclass
class MemoryPolicy:
    """Configurable retention / access policy, per visibility level."""

    visibility: Visibility
    default_access_level: AccessLevel
    default_sensitivity: Sensitivity
    retention_days: int
    requires_review: bool
    description: str = ""
    extra: dict = field(default_factory=dict)


DEFAULT_POLICIES: dict[Visibility, MemoryPolicy] = {
    Visibility.PERSONAL: MemoryPolicy(
        visibility=Visibility.PERSONAL,
        default_access_level=AccessLevel.OWNER_ONLY,
        default_sensitivity=Sensitivity.CONFIDENTIAL,
        retention_days=180,
        requires_review=False,
        description=(
            "Private to the owner. Never surfaced through organizational recall. "
            "Used for personal preferences, working habits and private notes."
        ),
    ),
    Visibility.TEAM: MemoryPolicy(
        visibility=Visibility.TEAM,
        default_access_level=AccessLevel.TEAM_ONLY,
        default_sensitivity=Sensitivity.INTERNAL,
        retention_days=365,
        requires_review=True,
        description="Shared inside the owning team after an explicit review.",
    ),
    Visibility.ORGANIZATION: MemoryPolicy(
        visibility=Visibility.ORGANIZATION,
        default_access_level=AccessLevel.PUBLIC_ORG,
        default_sensitivity=Sensitivity.INTERNAL,
        retention_days=730,
        requires_review=True,
        description=(
            "Operational knowledge available to any authorized successor. "
            "Requires explicit human promotion."
        ),
    ),
}


class PermissionDenied(Exception):
    """Raised when an actor may not read or act on a memory."""

    def __init__(self, message: str, reason: str = "not_authorized") -> None:
        super().__init__(message)
        self.reason = reason


# Visibility widens in this order. Never compare the raw strings: alphabetically
# "PERSONAL" > "ORGANIZATION" > "TEAM", which is the wrong direction.
VISIBILITY_ORDER: tuple[Visibility, ...] = (
    Visibility.PERSONAL,
    Visibility.TEAM,
    Visibility.ORGANIZATION,
)


def visibility_rank(visibility: Visibility) -> int:
    """0 = personal, 1 = team, 2 = organization. -1 if unknown."""
    try:
        return VISIBILITY_ORDER.index(Visibility(visibility))
    except ValueError:
        return -1


def can_reach(ceiling: Visibility, target: Visibility) -> bool:
    """True when an actor whose ceiling is `ceiling` may read `target` scope."""
    if ceiling is None:
        return False
    rank = visibility_rank(ceiling)
    return rank >= 0 and rank >= visibility_rank(target)


class MemoryResolver:
    """The only component allowed to decide whether a memory is visible."""

    def policy_for(self, visibility: Visibility) -> MemoryPolicy:
        return DEFAULT_POLICIES[Visibility(visibility)]

    # --- gate ---------------------------------------------------------
    def evaluate_gate(
        self,
        *,
        content: str,
        purpose: str,
        scope: str,
        visibility: Visibility,
        owner: str,
        team: str,
        is_operational_knowledge: bool,
        retention_days: int | None = None,
    ) -> MemoryGateDecision:
        """The Memory Gate. Runs before anything reaches Hindsight or SQLite."""
        lowered = content.lower()
        reasons: list[str] = []
        contains_secret = any(p in lowered for p in SECRET_PATTERNS)
        # Personal life signals that are explicitly not operational knowledge.
        personal_markers = (
            "prefers to work",
            "personal preference",
            "weekend",
            "birthday",
            "home address",
            "personal email",
        )
        contains_personal = any(m in lowered for m in personal_markers)

        policy = self.policy_for(visibility)
        future_useful = is_operational_knowledge or visibility != Visibility.PERSONAL
        needs_persistent = is_operational_knowledge

        if contains_secret:
            decision = "REJECT_SECRET"
            reasons.append(
                "Capture contains credential-shaped content. Secrets are never stored."
            )
        elif not purpose.strip():
            decision = "REJECT_UNPURPOSED"
            reasons.append("A memory without a stated purpose is not retained.")
        elif not scope.strip():
            decision = "REJECT_UNSCOPED"
            reasons.append(
                "Memory must declare the scope it applies to so it can be retired later."
            )
        elif not is_operational_knowledge and visibility == Visibility.ORGANIZATION:
            decision = "REJECT_NOT_OPERATIONAL"
            reasons.append(
                "Only organizationally useful operational experience can be promoted."
            )
        else:
            decision = "STORE"
            reasons.append("Operationally useful and correctly scoped.")
            if visibility == Visibility.PERSONAL:
                reasons.append(
                    "Stored as PERSONAL. It will not be retrievable as organizational "
                    "knowledge until a human promotes it."
                )
            if policy.requires_review:
                reasons.append("Requires human review before becoming active.")

        return MemoryGateDecision(
            purpose=purpose,
            scope=scope,
            sensitivity=policy.default_sensitivity,
            retention_days=retention_days or policy.retention_days,
            authorization_required=True,
            future_useful=future_useful,
            needs_persistent_memory=needs_persistent,
            contains_secret=contains_secret,
            contains_personal_data=contains_personal,
            decision=decision,
            reasons=reasons,
        )

    # --- access -------------------------------------------------------
    @staticmethod
    def owns(actor: Actor, memory: MemoryRecord) -> bool:
        """Is this actor the owner of this memory?

        Memories are stored with a human-readable owner (that is what the UI
        shows) while actors carry a stable id, so both are accepted. Getting
        this wrong would lock an expert out of their own knowledge.
        """
        owner = (memory.owner or "").strip().lower()
        if not owner:
            return False
        return owner in {
            (actor.id or "").strip().lower(),
            (actor.display_name or "").strip().lower(),
        }

    def can_read(self, actor: Actor, memory: MemoryRecord) -> tuple[bool, str]:
        visibility = Visibility(memory.visibility)
        if memory.access_level == AccessLevel.RESTRICTED:
            return False, "Memory has been explicitly restricted."
        if visibility == Visibility.PERSONAL:
            if self.owns(actor, memory) or actor.is_system:
                return True, "Owner access."
            return (
                False,
                "PERSONAL memory. Private to its owner and never returned through "
                "organizational recall.",
            )
        if memory.access_level == AccessLevel.OWNER_ONLY:
            if not self.owns(actor, memory) and not actor.is_system:
                return False, "Owner-only memory."
            return True, "Owner access."
        if memory.access_level == AccessLevel.TEAM_ONLY:
            if actor.team and memory.extra.get("team") and actor.team == memory.extra["team"]:
                return True, "Same team."
            if not actor.team:
                return False, "Actor has no team and memory is team-only."
            return False, f"Team-only memory. Actor team '{actor.team}' cannot read it."
        if Visibility(actor.visibility_ceiling) < visibility:
            return False, "Actor visibility ceiling is below the memory visibility."
        return True, "Organizational knowledge available to authorized actors."

    def assert_can_read(self, actor: Actor, memory: MemoryRecord) -> None:
        allowed, reason = self.can_read(actor, memory)
        if not allowed:
            raise PermissionDenied(
                f"Access denied for memory {memory.id}: {reason}",
                reason="permission_denied",
            )

    def filter_readable(
        self, actor: Actor, memories: list[MemoryRecord]
    ) -> tuple[list[MemoryRecord], list[dict[str, str]]]:
        """Split memories into visible ones and redacted descriptions of the rest.

        The redacted list is deliberately enough to explain *that* something was
        withheld (the privacy demo needs that) but never its content.
        """
        visible: list[MemoryRecord] = []
        withheld: list[dict[str, str]] = []
        for m in memories:
            allowed, reason = self.can_read(actor, m)
            if allowed:
                visible.append(m)
            else:
                withheld.append(
                    {
                        "id": m.id,
                        "title": "Withheld memory",
                        "visibility": str(Visibility(m.visibility)),
                        "reason": reason,
                    }
                )
        return visible, withheld

    # --- promotion ----------------------------------------------------
    def may_promote_to(self, actor: Actor, target: Visibility) -> tuple[bool, str]:
        """Role-level promotion capability, independent of any one memory.

        This is what the UI shows before an operator picks a memory, and it is
        derived from exactly the same rules `can_promote` applies.
        """
        target_v = Visibility(target)
        if target_v == Visibility.PERSONAL:
            return False, "A memory always starts PERSONAL; it is not promoted down."
        if actor.is_system:
            return True, "System actor (demo seeding)."
        if target_v == Visibility.ORGANIZATION and actor.role not in {
            "Knowledge Steward",
            "Reviewer",
            "Lead",
        }:
            return (
                False,
                "Only a Knowledge Steward may promote memory to ORGANIZATION.",
            )
        return True, "Explicit promotion permitted."

    def can_promote(
        self, actor: Actor, memory: MemoryRecord, target: Visibility
    ) -> tuple[bool, str]:
        current = Visibility(memory.visibility)
        target_v = Visibility(target)
        if target_v == current:
            return False, "Memory already has that visibility."
        allowed, reason = self.may_promote_to(actor, target_v)
        if not allowed:
            return allowed, reason
        if target_v == Visibility.TEAM and not self.owns(actor, memory):
            return False, "Only the owner may promote a personal memory to TEAM."
        return True, "Explicit promotion permitted."

    def expiry_for(
        self, visibility: Visibility, now: datetime | None = None
    ) -> datetime:
        policy = self.policy_for(visibility)
        return (now or utcnow()) + timedelta(days=policy.retention_days)


__all__ = [
    "Actor",
    "DEFAULT_POLICIES",
    "MemoryPolicy",
    "MemoryResolver",
    "PermissionDenied",
    "SECRET_PATTERNS",
    "VISIBILITY_ORDER",
    "can_reach",
    "visibility_rank",
]
