"""Internal confidence.

This is an **application-level heuristic**, not a calibrated probability. The UI
labels it "Internal confidence" and shows the factor breakdown so a reviewer can
see exactly why a memory scores what it scores.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from backend.models.memory import (
    ConfidenceBand,
    MemoryRecord,
    MemoryStatus,
    utcnow,
)

#: Relative weight of each factor. Sum is normalised at scoring time.
FACTOR_WEIGHTS: dict[str, float] = {
    "source_reliability": 0.22,
    "supporting_observations": 0.24,
    "human_confirmation": 0.20,
    "recency": 0.10,
    "scope_match": 0.12,
    "outcome_success": 0.12,
}

SOURCE_RELIABILITY: dict[str, float] = {
    "expert_interview": 0.78,
    "incident": 0.88,
    "outcome": 0.92,
    "architecture_change": 0.95,
    "handover_document": 0.62,
    "agent_synthesis": 0.45,
}

#: How old a memory must be before the recency factor starts to decay.
RECENCY_HALFLIFE_DAYS = 240.0

#: Shown next to every confidence number. Confidence is a MemoryOS heuristic over
#: a synthetic scenario, never a claim about the real world.
CONFIDENCE_DISCLAIMER = (
    "Internal confidence is a MemoryOS heuristic over source reliability, "
    "supporting observations, human confirmation, recency, scope match and "
    "outcome success. Synthetic prototype metric — not a statistical guarantee."
)

BAND_THRESHOLDS: list[tuple[float, ConfidenceBand]] = [
    (0.78, ConfidenceBand.VERY_HIGH),
    (0.60, ConfidenceBand.HIGH),
    (0.40, ConfidenceBand.MEDIUM),
    (0.0, ConfidenceBand.LOW),
]


def band_for(score: float) -> str:
    for threshold, band in BAND_THRESHOLDS:
        if score >= threshold:
            return str(band)
    return str(ConfidenceBand.LOW)


@dataclass
class ConfidenceFactor:
    key: str
    label: str
    weight: float
    value: float
    contribution: float
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "weight": round(self.weight, 3),
            "value": round(self.value, 3),
            "contribution": round(self.contribution, 3),
            "explanation": self.explanation,
        }


@dataclass
class ConfidenceResult:
    score: float
    band: str
    factors: list[ConfidenceFactor] = field(default_factory=list)
    penalties: list[str] = field(default_factory=list)
    label: str = "Internal confidence"
    disclaimer: str = (
        "Internal confidence is a MemoryOS heuristic, not a probability that this "
        "memory is true."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 3),
            "band": self.band,
            "label": self.label,
            "disclaimer": self.disclaimer,
            "factors": [f.to_dict() for f in self.factors],
            "penalties": self.penalties,
        }


class ConfidenceEngine:
    """Computes and refreshes internal confidence for a memory."""

    def _recency(self, memory: MemoryRecord, now: datetime) -> float:
        anchor = memory.last_validated_at or memory.observed_at or memory.created_at
        age_days = max(0.0, (now - anchor).total_seconds() / 86400.0)
        # Exponential decay: 0.5 ^ (age / halflife)
        return round(0.5 ** (age_days / RECENCY_HALFLIFE_DAYS), 4)

    def _supporting_observations(self, evidence_count: int) -> float:
        # 0 obs -> 0.15, 1 -> 0.45, 2 -> 0.7, 3+ -> 1.0
        table = {0: 0.15, 1: 0.45, 2: 0.70}
        return table.get(evidence_count, 1.0 if evidence_count >= 3 else 0.3)

    def _scope_match(self, memory: MemoryRecord, current_scope: str | None) -> float:
        if not current_scope:
            return 0.85
        if memory.scope == current_scope:
            return 1.0
        # Same family, different version (Payment Queue v1 vs v2)
        if current_scope.split()[-1][:1] == memory.scope.split()[-1][:1]:
            return 0.30
        return 0.45

    def _outcome_success(self, memory: MemoryRecord) -> float:
        if memory.status == MemoryStatus.SUPPORTED:
            return 1.0
        if memory.status == MemoryStatus.OBSERVED:
            return 0.75
        if memory.status == MemoryStatus.CONTRADICTED:
            return 0.15
        return 0.55

    def evaluate(
        self,
        memory: MemoryRecord,
        *,
        current_scope: str | None = None,
        contradiction_open: bool = False,
        now: datetime | None = None,
    ) -> ConfidenceResult:
        now = now or utcnow()
        penalties: list[str] = []

        source_value = SOURCE_RELIABILITY.get(memory.source_type, 0.5)
        support_value = self._supporting_observations(memory.evidence_count)
        confirm_value = 1.0 if memory.human_confirmed else 0.45
        recency_value = self._recency(memory, now)
        scope_value = self._scope_match(memory, current_scope)
        outcome_value = self._outcome_success(memory)

        values = {
            "source_reliability": source_value,
            "supporting_observations": support_value,
            "human_confirmation": confirm_value,
            "recency": recency_value,
            "scope_match": scope_value,
            "outcome_success": outcome_value,
        }
        labels = {
            "source_reliability": "Source reliability",
            "supporting_observations": "Supporting observations",
            "human_confirmation": "Human confirmation",
            "recency": "Recency",
            "scope_match": "Scope match",
            "outcome_success": "Outcome success",
        }
        explanations = {
            "source_reliability": f"Captured from a {memory.source_type.replace('_', ' ')}.",
            "supporting_observations": (
                f"{memory.evidence_count} supporting incident(s)/outcome(s) linked."
            ),
            "human_confirmation": (
                "Confirmed by a human reviewer."
                if memory.human_confirmed
                else "Not yet confirmed by a human reviewer."
            ),
            "recency": "Validated recently." if recency_value > 0.7 else "Ageing; never revalidated.",
            "scope_match": (
                f"Scope '{memory.scope}' matches the current environment."
                if scope_value >= 0.9
                else f"Scope '{memory.scope}' does not fully match the current environment."
            ),
            "outcome_success": f"Lifecycle status is {memory.status}.",
        }

        factors: list[ConfidenceFactor] = []
        score = 0.0
        for key, weight in FACTOR_WEIGHTS.items():
            value = values[key]
            contribution = weight * value
            score += contribution
            factors.append(
                ConfidenceFactor(
                    key=key,
                    label=labels[key],
                    weight=weight,
                    value=value,
                    contribution=contribution,
                    explanation=explanations[key],
                )
            )

        # Contradiction and staleness penalties.
        if contradiction_open:
            score *= 0.6
            penalties.append("An open contradiction is attached to this memory (-40%).")
        if memory.status == MemoryStatus.CONTRADICTED:
            score *= 0.5
            penalties.append("Memory is marked CONTRADICTED (-50%).")
        if memory.status == MemoryStatus.STALE:
            score *= 0.55
            penalties.append("Memory is marked STALE (-45%).")
        if memory.is_expired(now):
            score *= 0.4
            penalties.append("Memory is past its expiry date (-60%).")
        if not memory.is_usable(now):
            score = min(score, 0.2)
            penalties.append("Memory is archived or rejected.")

        score = max(0.0, min(1.0, score))
        return ConfidenceResult(
            score=score,
            band=band_for(score),
            factors=factors,
            penalties=penalties,
        )

    def refresh(
        self,
        memory: MemoryRecord,
        *,
        current_scope: str | None = None,
        contradiction_open: bool = False,
        persist: bool | None = None,
    ) -> MemoryRecord:
        result = self.evaluate(
            memory, current_scope=current_scope, contradiction_open=contradiction_open
        )
        memory.confidence = round(result.score, 4)
        memory.extra = {
            **(memory.extra or {}),
            "confidence_breakdown": result.to_dict(),
        }
        return memory


def default_expiry(visibility_retention_days: int, from_now: datetime | None = None) -> datetime:
    return (from_now or utcnow()) + timedelta(days=visibility_retention_days)


__all__ = [
    "CONFIDENCE_DISCLAIMER",
    "ConfidenceEngine",
    "ConfidenceFactor",
    "ConfidenceResult",
    "FACTOR_WEIGHTS",
    "SOURCE_RELIABILITY",
    "band_for",
    "default_expiry",
]
