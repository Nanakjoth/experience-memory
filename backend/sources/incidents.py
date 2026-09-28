"""Incident record adapter.

Incidents are the evidence layer. Each incident is retained into Hindsight so a
recommendation can be traced to what actually happened, not to an assertion.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.models.memory import MemoryType, Visibility
from backend.seed.novatech import INCIDENTS
from backend.sources.base import ExtractedClaim, KnowledgeSource, SourceDocument


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def incident_narrative(inc: dict) -> str:
    return inc["narrative"]


def incident_summary(inc: dict) -> str:
    depth = f" Queue depth {inc['queue_depth']} percent." if inc.get("queue_depth") else ""
    return (
        f"{inc['id']} ({inc['severity']}) on {inc['service']}, {inc['component']}.{depth} "
        f"Action: {inc['action']}. Outcome: {inc['outcome']}."
    )


class IncidentSource(KnowledgeSource):
    source_type = "incident"
    display_name = "Incident record"

    def __init__(self, incident_ids: list[str] | None = None, system: str | None = None):
        self.incident_ids = incident_ids
        self.system = system

    def _select(self) -> list[dict]:
        items = INCIDENTS
        if self.incident_ids:
            wanted = set(self.incident_ids)
            items = [i for i in items if i["id"] in wanted]
        if self.system:
            items = [i for i in items if i["system"] == self.system]
        return items

    def available(self) -> bool:
        return bool(self._select())

    def documents(self) -> list[SourceDocument]:
        docs: list[SourceDocument] = []
        for inc in self._select():
            dup = inc.get("duplicate_processing", False)
            outcome_claim_type = "EVENT"
            claims = [
                ExtractedClaim(
                    type=outcome_claim_type,
                    title=f"{inc['id']}: {inc['title']}",
                    content=incident_summary(inc),
                    summary=inc["outcome"],
                    scope=inc["component"],
                    owner=inc["engineer"],
                    domain=inc["system"].split()[0].lower(),
                    purpose="Provide historical evidence for future operational decisions.",
                    entities=[inc["id"], inc["service"], inc["component"], inc["engineer"]],
                    visibility=Visibility.ORGANIZATION,
                    observed_at=_parse(inc["resolved_at"] or inc["opened_at"]),
                    evidence_refs=[("incident", inc["id"], inc["outcome"])],
                )
            ]
            if dup:
                # Negative knowledge: what NOT to do, learned from a failure.
                claims.append(
                    ExtractedClaim(
                        type=MemoryType.EXPERIENCE,
                        title=f"{inc['id']} — restarting was the wrong action",
                        content=(
                            f"In {inc['id']} the chosen action '{inc['action']}' led to "
                            f"'{inc['outcome']}'. Queue depth was "
                            f"{inc.get('queue_depth')} percent."
                        ),
                        summary="Negative knowledge derived from a failed action.",
                        scope=inc["component"],
                        owner=inc["engineer"],
                        domain=inc["system"].split()[0].lower(),
                        purpose="Remember what NOT to repeat, not just what to do.",
                        entities=[inc["id"], inc["component"]],
                        visibility=Visibility.ORGANIZATION,
                        observed_at=_parse(inc["resolved_at"] or inc["opened_at"]),
                        evidence_refs=[("incident", inc["id"], "failed action")],
                    )
                )
            docs.append(
                SourceDocument(
                    source_type=self.source_type,
                    source_id=inc["id"],
                    source_name=f"{inc['id']} incident record",
                    title=inc["title"],
                    content=incident_narrative(inc),
                    context=f"{inc['system']} incident postmortem",
                    document_id=f"doc-{inc['id']}",
                    scope=inc["component"],
                    owner=inc["engineer"],
                    team="Payments Operations"
                    if inc["system"] == "Payment Platform"
                    else ("Identity Operations" if "Identity" in inc["system"] else "Network Operations"),
                    domain=inc["system"].split()[0].lower(),
                    purpose="Preserve incident evidence and outcomes as organizational memory.",
                    claims=claims,
                    observed_at=_parse(inc["opened_at"]),
                    captured_at=_parse(inc["resolved_at"] or inc["opened_at"]),
                    visibility=Visibility.ORGANIZATION,
                    entities=[inc["id"], inc["service"], inc["component"], inc["engineer"]],
                    tags=["incident", inc["severity"].lower()],
                    is_operational=True,
                    metadata={
                        "severity": inc["severity"],
                        "queue_depth": inc.get("queue_depth"),
                        "duplicate_processing": int(bool(dup)),
                        "incident_status": inc["status"],
                    },
                )
            )
        return docs


__all__ = ["IncidentSource", "incident_narrative", "incident_summary"]
