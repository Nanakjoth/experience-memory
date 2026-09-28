"""Expert interview adapter.

Produces the conversational capture documents (the CAPTURE EXPERIENCE screen is
driven by the same prompt list) plus the expert's own pre-authored lessons.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.models.memory import MemoryType, Visibility
from backend.seed.novatech import EXPERT_INTERVIEWS, EXPERT_LESSONS
from backend.sources.base import ExtractedClaim, KnowledgeSource, SourceDocument

#: The conversation prompts shown in the Capture Experience UI.
CAPTURE_PROMPTS: list[dict[str, str]] = [
    {"id": "system", "prompt": "What system do you know well?"},
    {"id": "failure", "prompt": "What usually goes wrong?"},
    {"id": "never_do", "prompt": "What should a new engineer NOT do?"},
    {"id": "first_check", "prompt": "What do you check first?"},
    {"id": "escalate", "prompt": "When should someone escalate?"},
    {"id": "who", "prompt": "Who normally handles it?"},
    {"id": "workaround", "prompt": "What workaround have you used?"},
    {"id": "why", "prompt": "Why does that workaround exist?"},
    {"id": "failure_story", "prompt": "Tell me about a time the normal procedure failed."},
    {"id": "scope", "prompt": "Does this apply everywhere, or only to a specific environment?"},
]

TRANSCRIPT_TO_PROMPT = {
    "system": "What system do you know well?",
    "failure": "What usually goes wrong?",
    "never_do": "What should a new engineer NOT do?",
    "first_check": "What do you check first?",
    "escalate": "When should someone escalate?",
    "who": "Who normally handles it?",
    "workaround": "What workaround have you used?",
    "why": "Why does that workaround exist?",
    "failure_story": "Tell me about a time the normal procedure failed.",
    "scope": "Does this apply everywhere, or only to a specific environment?",
}


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


class ExpertInterviewSource(KnowledgeSource):
    source_type = "expert_interview"
    display_name = "Expert interview"

    def __init__(self, interview_id: str = "expert-arun-payment") -> None:
        self.interview_id = interview_id
        self._interview = next(
            (i for i in EXPERT_INTERVIEWS if i["id"] == interview_id), None
        )

    def available(self) -> bool:
        return self._interview is not None

    def transcript_text(self) -> str:
        if not self._interview:
            return ""
        lines: list[str] = [
            f"Expert interview. {self._interview['expert']}, {self._interview['role']}, "
            f"{self._interview['team']}.",
            f"System: {self._interview['system']}. Scope discussed: "
            f"{self._interview['scope']}.",
            "",
        ]
        for speaker, text in self._interview["transcript"]:
            lines.append(f"{speaker}: {text}")
        return "\n".join(lines)

    def documents(self) -> list[SourceDocument]:
        if not self._interview:
            return []
        iv = self._interview
        claims = [
            ExtractedClaim(
                type=MemoryType(lesson["type"]),
                title=lesson["title"],
                content=lesson["content"],
                summary=lesson.get("summary", ""),
                scope=lesson["scope"],
                owner=lesson["owner"],
                domain=lesson["domain"],
                purpose=lesson["purpose"],
                entities=lesson.get("entities", []),
                visibility=Visibility(lesson.get("visibility", "PERSONAL")),
                evidence_refs=lesson.get("evidence", []),
                observed_at=_parse(lesson["observed_at"]) if lesson.get("observed_at") else None,
            )
            for lesson in EXPERT_LESSONS
            if lesson["source"] == iv["id"]
        ]
        return [
            SourceDocument(
                source_type=self.source_type,
                source_id=iv["id"],
                source_name=f"{iv['expert']} expert interview",
                title=iv["title"],
                content=self.transcript_text(),
                context="Senior engineer expert interview",
                document_id=f"doc-{iv['id']}",
                scope=iv["scope"],
                owner=iv["expert"],
                team=iv["team"],
                domain="payments" if iv["system"] == "Payment Platform" else iv["system"].split()[0].lower(),
                purpose="Preserve undocumented operational judgment before it is lost.",
                claims=claims,
                observed_at=_parse(iv["captured_at"]),
                captured_at=_parse(iv["captured_at"]),
                visibility=Visibility.PERSONAL,
                entities=[
                    iv["expert"],
                    iv["system"],
                    iv["scope"],
                    "Payment API",
                    "Payments Operations",
                ],
                tags=["capture", "expert"],
                is_operational=True,
                metadata={"expert": iv["expert"], "role": iv["role"]},
            )
        ]


__all__ = ["CAPTURE_PROMPTS", "ExpertInterviewSource", "TRANSCRIPT_TO_PROMPT"]
