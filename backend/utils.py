"""Small shared helpers."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.models.memory import utcnow

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def new_id(prefix: str = "id") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"


def stable_id(prefix: str, *parts: str) -> str:
    """Deterministic id so re-seeding does not duplicate rows."""
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{digest.upper()}"


def slug(text: str) -> str:
    return _SLUG_RE.sub("-", text.lower()).strip("-")


def truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 1]


STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "to", "of", "in", "on", "for",
    "and", "or", "it", "this", "that", "with", "as", "at", "by", "from", "do", "does",
    "did", "what", "should", "i", "we", "you", "my", "our", "your", "can", "if", "so",
}


def content_tokens(text: str) -> list[str]:
    return [t for t in tokenize(text) if t not in STOPWORDS]


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def now() -> datetime:
    return utcnow()


def enum_value(value: Any) -> Any:
    """Return the stored form of an enum.

    ``str(Enum.MEMBER)`` is ``"Enum.MEMBER"`` on modern Python, and pydantic's
    ``use_enum_values`` means a field may hold either the raw value or the enum
    member depending on how it was assigned. Both must serialise identically.
    """
    if value is None:
        return None
    return getattr(value, "value", value)


def enum_str(value: Any) -> str | None:
    v = enum_value(value)
    return None if v is None else str(v)


__all__ = [
    "STOPWORDS",
    "content_tokens",
    "enum_str",
    "enum_value",
    "iso",
    "new_id",
    "now",
    "parse_iso",
    "slug",
    "stable_id",
    "tokenize",
    "truncate",
]
