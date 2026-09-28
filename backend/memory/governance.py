"""Governance.

Every state change to a memory goes through here so that:
  * promotion is always explicit,
  * lifecycle transitions are legal and audited,
  * contradiction resolution never destroys the original text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.db.database import Database
from backend.memory.confidence import ConfidenceEngine
from backend.memory.contradiction import RESOLUTION_ACTIONS
from backend.memory.lifecycle import (
    InvalidTransition,
    apply_transition,
    stage_progress,
)
from backend.models.audit import AuditEvent, AuditEventType
from backend.models.memory import (
    AccessLevel,
    LearningEvent,
    MemoryEvent,
    MemoryRecord,
    MemoryStatus,
    Visibility,
    utcnow,
)
from backend.models.permissions import (
    DEFAULT_POLICIES,
    Actor,
    MemoryResolver,
    PermissionDenied,
)
from backend.utils import new_id, truncate


class MemoryNotFound(LookupError):
    pass


@dataclass
class GovernanceOutcome:
    memory: MemoryRecord
    action: str
    detail: str
    previous_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory": self.memory.model_dump(mode="json"),
            "action": self.action,
            "detail": self.detail,
            "previous_status": self.previous_status,
        }


class GovernanceService:
    def __init__(self, db: Database, resolver: MemoryResolver | None = None) -> None:
        self.db = db
        self.resolver = resolver or MemoryResolver()
        self.confidence = ConfidenceEngine()

    # --- helpers -------------------------------------------------------
    def _get(self, memory_id: str) -> MemoryRecord:
        mem = self.db.get_memory(memory_id)
        if mem is None:
            raise MemoryNotFound(f"Memory {memory_id} not found.")
        return mem

    def _audit(
        self,
        *,
        event_type: AuditEventType,
        actor: Actor,
        memory: MemoryRecord,
        detail: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.db.add_audit(
            AuditEvent(
                id=new_id("aud"),
                event_type=event_type,
                actor=actor.id,
                actor_role=actor.role,
                subject=memory.title,
                memory_id=memory.id,
                detail=detail,
                payload=payload or {},
            )
        )

    def _recompute(self, mem: MemoryRecord) -> MemoryRecord:
        open_contradiction = bool(
            self.db.list_contradictions(status="REVIEW_REQUIRED")
            and any(
                c.memory_id == mem.id
                for c in self.db.list_contradictions(status="REVIEW_REQUIRED")
            )
        )
        self.confidence.refresh(mem, contradiction_open=open_contradiction)
        self.db.upsert_memory(mem)
        return mem

    def current_scope(self) -> str:
        system = self.db.get_system("sys-payment")
        return (system or {}).get("active_component") or "Payment Queue v1"

    # --- actions -------------------------------------------------------
    def review(
        self, memory_id: str, *, actor: Actor, approve: bool, note: str = ""
    ) -> GovernanceOutcome:
        mem = self._get(memory_id)
        previous = str(mem.status)
        if not approve:
            event = apply_transition(
                mem,
                MemoryStatus.REJECTED,
                actor=actor.id,
                action="rejected",
                note=note or "Rejected during human review.",
            )
            self._audit(
                event_type=AuditEventType.MEMORY_REJECTED,
                actor=actor,
                memory=mem,
                detail="Memory rejected during review. Original text preserved.",
            )
        else:
            event = apply_transition(
                mem,
                MemoryStatus.CONFIRMED,
                actor=actor.id,
                action="reviewed",
                note=note or "Reviewed and confirmed by a human.",
            )
            self._audit(
                event_type=AuditEventType.MEMORY_REVIEWED,
                actor=actor,
                memory=mem,
                detail="Memory reviewed and confirmed.",
            )
        self.db.add_memory_event(event)
        self._recompute(mem)
        return GovernanceOutcome(
            memory=mem,
            action="reject" if not approve else "approve",
            detail="Memory rejected." if not approve else "Memory confirmed and awaiting promotion.",
            previous_status=previous,
        )

    def promote(
        self,
        memory_id: str,
        *,
        actor: Actor,
        target: Visibility,
        note: str = "",
    ) -> GovernanceOutcome:
        mem = self._get(memory_id)
        previous = str(mem.status)
        allowed, reason = self.resolver.can_promote(actor, mem, target)
        if not allowed:
            raise PermissionDenied(reason, reason="promotion_not_allowed")
        current = Visibility(mem.visibility)
        mem.visibility = target
        policy = self.resolver.policy_for(target)
        mem.access_level = policy.default_access_level
        mem.expiry_at = self.resolver.expiry_for(target)
        mem.promoted_by = actor.id
        event = apply_transition(
            mem,
            MemoryStatus.ACTIVE,
            actor=actor.id,
            action=f"promoted_{str(current).lower()}_to_{str(target).lower()}",
            note=note or f"Promoted from {current} to {target} by explicit human action.",
            payload={"from": str(current), "to": str(target)},
        )
        self.db.add_memory_event(event)
        self._recompute(mem)
        self._audit(
            event_type=AuditEventType.MEMORY_PROMOTED,
            actor=actor,
            memory=mem,
            detail=f"Promoted {current} -> {target}.",
            payload={"from": str(current), "to": str(target)},
        )
        self.db.add_learning_event(
            LearningEvent(
                id=new_id("lev"),
                kind="memory_promoted",
                message=(
                    f"One expert lesson was promoted to {str(target).lower()} "
                    f"knowledge."
                ),
                memory_id=mem.id,
                detail=mem.title,
            )
        )
        self.db.bump_metric("memories_updated")
        return GovernanceOutcome(
            memory=mem,
            action="promote",
            detail=f"Promoted to {target}. Explicit promotion only, never automatic.",
            previous_status=previous,
        )

    def validate(
        self, memory_id: str, *, actor: Actor, note: str = ""
    ) -> GovernanceOutcome:
        mem = self._get(memory_id)
        previous = str(mem.status)
        event = apply_transition(
            mem,
            MemoryStatus.REVALIDATED,
            actor=actor.id,
            action="revalidated",
            note=note
            or f"Re-validated by {actor.display_name} against {self.current_scope()}.",
        )
        self.db.add_memory_event(event)
        self._recompute(mem)
        self._audit(
            event_type=AuditEventType.MEMORY_REVALIDATED,
            actor=actor,
            memory=mem,
            detail=f"Re-validated against the current environment ({self.current_scope()}).",
        )
        self.db.bump_metric("memories_revalidated")
        return GovernanceOutcome(
            memory=mem,
            action="validate",
            detail="Memory re-validated. Internal confidence recalculated.",
            previous_status=previous,
        )

    def restrict(
        self,
        memory_id: str,
        *,
        actor: Actor,
        reason: str = "",
        access_level: AccessLevel | None = None,
    ) -> GovernanceOutcome:
        mem = self._get(memory_id)
        previous = str(mem.status)
        mem.access_level = access_level or AccessLevel.RESTRICTED
        event = apply_transition(
            mem,
            MemoryStatus.STALE,
            actor=actor.id,
            action="restricted",
            note=reason or "Access restricted. Content preserved.",
            payload={"access_level": str(mem.access_level)},
        )
        self.db.add_memory_event(event)
        self._recompute(mem)
        self._audit(
            event_type=AuditEventType.MEMORY_RESTRICTED,
            actor=actor,
            memory=mem,
            detail=reason or "Memory access restricted.",
            payload={"access_level": str(mem.access_level)},
        )
        return GovernanceOutcome(
            memory=mem,
            action="restrict",
            detail=f"Access set to {mem.access_level}. Content is preserved.",
            previous_status=previous,
        )

    def expire(
        self, memory_id: str, *, actor: Actor, reason: str = "", days: int | None = None
    ) -> GovernanceOutcome:
        from datetime import timedelta

        mem = self._get(memory_id)
        previous = str(mem.status)
        mem.expiry_at = utcnow() + timedelta(days=days if days is not None else 0)
        event = apply_transition(
            mem,
            MemoryStatus.STALE,
            actor=actor.id,
            action="expired",
            note=reason or "Expired. Preserved for history, not surfaced as guidance.",
        )
        self.db.add_memory_event(event)
        self._recompute(mem)
        self._audit(
            event_type=AuditEventType.MEMORY_EXPIRED,
            actor=actor,
            memory=mem,
            detail=reason or "Memory expired.",
        )
        return GovernanceOutcome(
            memory=mem,
            action="expire",
            detail="Memory expired. It is preserved in history and not deleted.",
            previous_status=previous,
        )

    def expire_stale(self, *, actor: Actor) -> list[GovernanceOutcome]:
        """Archive anything past its expiry date. Content is never deleted."""
        out: list[GovernanceOutcome] = []
        for mem in self.db.all_memories():
            if mem.is_expired() and mem.status not in {
                MemoryStatus.ARCHIVED,
                MemoryStatus.REJECTED,
            }:
                out.append(
                    self.expire(
                        mem.id, actor=actor, reason="Retention period elapsed."
                    )
                )
        return out

    # --- contradiction resolution --------------------------------------
    def resolve_contradiction(
        self, contradiction_id: str, *, action: str, actor: Actor, note: str = ""
    ) -> dict[str, Any]:
        if action not in RESOLUTION_ACTIONS:
            raise ValueError(
                f"Unknown resolution action '{action}'. "
                f"Expected one of {sorted(RESOLUTION_ACTIONS)}."
            )
        c = self.db.get_contradiction(contradiction_id)
        if c is None:
            raise MemoryNotFound(f"Contradiction {contradiction_id} not found.")
        mem = self._get(c.memory_id)
        previous = str(mem.status)
        spec = RESOLUTION_ACTIONS[action]
        target_status = spec["resulting_status"]
        result_status = (
            MemoryStatus(target_status)
            if target_status != "unchanged"
            else mem.status
        )
        detail = note or spec["description"]

        if action == "confirm":
            event = apply_transition(
                mem,
                MemoryStatus.REVALIDATED,
                actor=actor.id,
                action="contradiction_confirmed",
                note=detail,
                payload={"contradiction_id": contradiction_id},
            )
            self.db.bump_metric("memories_revalidated")
        elif action == "restrict":
            # Keep the lesson, narrow it: the memory keeps its lifecycle status
            # (it may be SUPPORTED or USED, not just ACTIVE) and is explicitly
            # marked as not applicable to the new environment.
            event = self.db.add_memory_event(
                MemoryEvent(
                    id=new_id("mev"),
                    memory_id=mem.id,
                    from_status=mem.status,
                    to_status=mem.status,
                    action="scope_restricted",
                    actor=actor.id,
                    note=detail,
                    payload={
                        "contradiction_id": contradiction_id,
                        "kept_scope": mem.scope,
                        "excluded_scope": c.current_environment,
                    },
                )
            )
            mem.related_entities = sorted(
                set(mem.related_entities) | {c.current_environment}
            )
            mem.extra = {
                **(mem.extra or {}),
                "excluded_scopes": sorted(
                    set((mem.extra or {}).get("excluded_scopes", []))
                    | {c.current_environment}
                ),
            }
        elif action == "update":
            mem.version += 1
            mem.content = (
                f"{mem.content} "
                f"[UPDATE {utcnow().date().isoformat()}] {c.conflicting_content}"
            )
            mem.extra = {
                **(mem.extra or {}),
                "superseded_note": (
                    f"Updated because {c.conflicting_source_id} changed the environment "
                    f"to {c.current_environment}."
                ),
                "previous_versions": [
                    *(mem.extra or {}).get("previous_versions", []),
                    {"version": mem.version - 1, "content": mem.content},
                ],
            }
            event = apply_transition(
                mem,
                MemoryStatus.UPDATED,
                actor=actor.id,
                action="updated",
                note=detail,
                payload={"contradiction_id": contradiction_id},
            )
        else:  # stale
            event = apply_transition(
                mem,
                MemoryStatus.STALE,
                actor=actor.id,
                action="marked_stale",
                note=detail,
                payload={"contradiction_id": contradiction_id},
            )

        self.db.add_memory_event(event)
        self._recompute(mem)

        c.status = "RESOLVED"
        c.resolution = action
        c.resolved_at = utcnow()
        c.resolved_by = actor.id
        self.db.add_contradiction(c)

        self._audit(
            event_type=AuditEventType.MEMORY_UPDATED,
            actor=actor,
            memory=mem,
            detail=(
                f"Contradiction {contradiction_id} resolved with '{action}'. "
                "The original memory text is preserved."
            ),
            payload={"contradiction_id": contradiction_id, "action": action},
        )
        self.db.add_learning_event(
            LearningEvent(
                id=new_id("lev"),
                kind="contradiction_resolved",
                message=(
                    f"A contradiction was resolved with '{action}'. History preserved."
                ),
                memory_id=mem.id,
                detail=truncate(detail, 200),
            )
        )
        self.db.bump_metric("memories_updated")
        return {
            "contradiction": c.model_dump(mode="json"),
            "memory": mem.model_dump(mode="json"),
            "action": action,
            "detail": detail,
            "previous_status": previous,
            "resolution_options": RESOLUTION_ACTIONS,
        }

    # --- views ---------------------------------------------------------
    def evolution_stages(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for mem in self.db.all_memories():
            progress = stage_progress(mem)
            rows.append(
                {
                    "memory_id": mem.id,
                    "title": mem.title,
                    "type": str(mem.type),
                    "scope": mem.scope,
                    "owner": mem.owner,
                    "visibility": str(mem.visibility),
                    "status": str(mem.status),
                    "confidence": mem.confidence,
                    "evidence_count": mem.evidence_count,
                    "progress": progress,
                    "history": [
                        e.model_dump(mode="json") for e in self.db.memory_history(mem.id)
                    ],
                    "excluded_scopes": (mem.extra or {}).get("excluded_scopes", []),
                }
            )
        rows.sort(key=lambda r: (r["status"] != "CONTRADICTED", r["title"]))
        return rows

    def knowledge_continuity(self, employee_id: str = "emp-arun") -> dict[str, Any]:
        emp = self.db.get_employee(employee_id) or {}
        owner = emp.get("name", "Arun")
        owned = [
            m
            for m in self.db.all_memories()
            if (m.owner or "").strip().lower() == owner.strip().lower()
        ]
        validated = [
            m
            for m in owned
            if m.status in {
                str(MemoryStatus.ACTIVE),
                str(MemoryStatus.REVALIDATED),
                str(MemoryStatus.SUPPORTED),
            }
        ]
        pending = [m for m in owned if m.status in {str(MemoryStatus.CREATED), str(MemoryStatus.CONFIRMED)}]
        stale = [m for m in owned if m.status == str(MemoryStatus.STALE)]
        return {
            "employee": {
                "id": emp.get("id", employee_id),
                "name": owner,
                "role": emp.get("role", "Senior DevOps Engineer"),
                "team": emp.get("team", "Payments Operations"),
                "status": emp.get("status", "unavailable"),
                "note": emp.get("note", ""),
            },
            "knowledge_captured": len(owned),
            "validated": len(validated),
            "pending_review": len(pending),
            "stale": len(stale),
            "personal_only": len([m for m in owned if str(m.visibility) == "PERSONAL"]),
            "promoted": len([m for m in owned if str(m.visibility) == "ORGANIZATION"]),
            "single_person_dependencies": {
                "before": 14,
                "after": max(0, 14 - len(validated)),
                "label": "Synthetic prototype metric",
            },
            "items": [
                {
                    "id": m.id,
                    "title": m.title,
                    "type": str(m.type),
                    "status": str(m.status),
                    "visibility": str(m.visibility),
                    "confidence": m.confidence,
                    "evidence_count": m.evidence_count,
                }
                for m in owned
            ],
        }

    def knowledge_at_risk(self) -> list[dict[str, Any]]:
        """Which critical knowledge still depends on one person?"""
        rows: list[dict[str, Any]] = []
        for system in self.db.list_systems():
            scoped = [
                m
                for m in self.db.all_memories()
                if m.scope.startswith(system["name"].split()[0]) or m.domain == system["domain"]
            ]
            owners = {m.owner for m in scoped}
            owner = system["owner"]
            personal_only = [
                m
                for m in scoped
                if str(m.visibility) == "PERSONAL"
                and (m.owner or "").strip().lower() == owner.strip().lower()
            ]
            validated = [
                m
                for m in scoped
                if m.status in {str(MemoryStatus.ACTIVE), str(MemoryStatus.REVALIDATED)}
            ]
            coverage = 0.0
            if scoped:
                coverage = round(len(validated) / len(scoped), 3)
            single_person = len(personal_only) > 0 or len(owners) <= 1
            risk = "High" if (single_person and coverage < 0.8) else (
                "Medium" if single_person else "Low"
            )
            rows.append(
                {
                    "system": system["name"],
                    "system_id": system["id"],
                    "owner": owner,
                    "team": system["team"],
                    "criticality": system["criticality"],
                    "risk": risk,
                    "knowledge_items": len(scoped),
                    "validated": len(validated),
                    "personal_only": len(personal_only),
                    "replacement_coverage": (
                        "Complete" if coverage >= 0.99
                        else "Partial" if coverage > 0.3
                        else "None"
                    ),
                    "coverage_ratio": coverage,
                    "knowledge_owners": sorted(owners),
                    "active_component": system.get("active_component"),
                    "synthetic": True,
                }
            )
        rows.sort(key=lambda r: {"High": 0, "Medium": 1, "Low": 2}[r["risk"]])
        return rows

    def governance_summary(self) -> dict[str, Any]:
        memories = self.db.all_memories()
        by_visibility: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for m in memories:
            by_visibility[str(m.visibility)] = by_visibility.get(str(m.visibility), 0) + 1
            by_status[str(m.status)] = by_status.get(str(m.status), 0) + 1
        return {
            "by_visibility": by_visibility,
            "by_status": by_status,
            "by_confidence": self.db.confidence_buckets(),
            "open_contradictions": len(
                self.db.list_contradictions(status="REVIEW_REQUIRED")
            ),
            "resolved_contradictions": len(
                self.db.list_contradictions(status="RESOLVED")
            ),
            "resolution_actions": RESOLUTION_ACTIONS,
            "policies": {
                str(visibility): {
                    "visibility": str(policy.visibility),
                    "default_access_level": str(policy.default_access_level),
                    "default_sensitivity": str(policy.default_sensitivity),
                    "retention_days": policy.retention_days,
                    "requires_review": policy.requires_review,
                    "description": policy.description,
                }
                for visibility, policy in DEFAULT_POLICIES.items()
            },
        }


__all__ = ["GovernanceOutcome", "GovernanceService", "InvalidTransition", "MemoryNotFound"]
