"""Hindsight integration.

MemoryOS treats Hindsight as *the* memory engine. This module is the only place
that talks to it.

Two implementations are provided behind one interface:

``HindsightEngine``
    The real engine. Uses ``hindsight_client.Hindsight`` async methods
    (``aretain`` / ``arecall`` / ``areflect``) against the dedicated bank
    ``memoryos-novatech``.

``SimulatedHindsightEngine``
    A dependency-free stand-in with the same contract, used when no Hindsight
    server is reachable. It is **always** reported as ``mode="simulated"`` and
    the UI labels every result produced by it as SIMULATED. It exists so the
    product can be demonstrated on a laptop with no Docker and no LLM key; it is
    not a replacement for Hindsight and never pretends to be one.

``get_engine()`` returns the live engine when Hindsight answers, and otherwise
degrades to the simulated engine while recording the reason.
"""

from __future__ import annotations

import asyncio
import json
import math
import re
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import Settings, get_settings
from backend.utils import content_tokens, new_id, stable_id, truncate, utcnow

BANK_MISSION = (
    "You are the operational memory of NovaTech, an engineering organization. "
    "You preserve what the organization learned by doing things, not merely what "
    "was written down. You value: operational experience, lessons learned, "
    "exceptions to documented procedures, escalation knowledge, incident outcomes, "
    "historical context, evidence, uncertainty, and change over time."
)

BANK_DIRECTIVES = [
    "Never present a historical experience as an absolute rule.",
    "Always distinguish documented fact from historical experience and inference.",
    "Always state the scope a piece of knowledge applies to.",
    "Cite the incidents or outcomes that support a recommendation.",
    "If new evidence may have invalidated older knowledge, say so explicitly "
    "instead of applying the older knowledge blindly.",
    "Prefer careful reasoning over pattern matching.",
    "Never reveal private (PERSONAL) memory through an organizational question.",
    "Never invent incident identifiers, dates or measurements.",
]

BANK_DISPOSITION = {
    "skepticism": 4,
    "literalism": 4,
    "empathy": 2,
}


@dataclass
class EngineFact:
    """A Hindsight fact, normalized."""

    id: str
    text: str
    type: str = "world"  # world | experience | observation
    context: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    occurred_start: str | None = None
    mentioned_at: str | None = None
    document_id: str | None = None
    chunk_id: str | None = None
    scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "type": self.type,
            "context": self.context,
            "metadata": self.metadata,
            "tags": self.tags,
            "entities": self.entities,
            "occurred_start": self.occurred_start,
            "mentioned_at": self.mentioned_at,
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "scores": self.scores,
        }


@dataclass
class EngineRecallResult:
    facts: list[EngineFact]
    latency_ms: int
    query: str
    bank_id: str
    mode: str
    trace: dict[str, Any] = field(default_factory=dict)
    strategy_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class EngineReflectResult:
    text: str
    based_on: list[EngineFact]
    latency_ms: int
    query: str
    bank_id: str
    mode: str
    trace: dict[str, Any] = field(default_factory=dict)


@dataclass
class EngineHealth:
    available: bool
    mode: str
    label: str
    bank_id: str
    detail: str = ""
    version: str | None = None
    simulated: bool = False
    degraded_reason: str | None = None


class MemoryEngineError(RuntimeError):
    """Raised when the engine cannot complete a request."""


class MemoryEngineUnavailable(MemoryEngineError):
    """Raised when the live engine is unreachable and simulation is disabled."""


class MemoryEngine(ABC):
    """The contract MemoryOS depends on. Deliberately small."""

    mode: str = "unknown"
    simulated: bool = False

    def __init__(self, bank_id: str) -> None:
        self.bank_id = bank_id

    @abstractmethod
    async def aretain(
        self,
        content: str,
        *,
        context: str | None = None,
        document_id: str | None = None,
        metadata: dict[str, str] | None = None,
        tags: list[str] | None = None,
        timestamp: datetime | None = None,
        retain_async: bool = False,
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def arecall(
        self,
        query: str,
        *,
        max_tokens: int = 4096,
        budget: str = "mid",
        types: list[str] | None = None,
        include_entities: bool = False,
    ) -> EngineRecallResult: ...

    @abstractmethod
    async def areflect(
        self,
        query: str,
        *,
        budget: str = "low",
        context: str | None = None,
        max_tokens: int | None = None,
        include_facts: bool = True,
    ) -> EngineReflectResult: ...

    @abstractmethod
    async def health(self) -> EngineHealth: ...

    @abstractmethod
    async def ensure_bank(self) -> dict[str, Any]: ...

    async def alist_memories(self, limit: int = 500) -> list[EngineFact]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Real Hindsight
# ---------------------------------------------------------------------------


class HindsightEngine(MemoryEngine):
    """Real Hindsight client.

    All calls are the async variants (``aretain`` / ``arecall`` / ``areflect``)
    so nothing blocks the FastAPI event loop.
    """

    mode = "live"
    simulated = False

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings.hindsight_bank_id)
        self._settings = settings
        self._client: Any = None
        self._lock = threading.Lock()
        self._version: str | None = None

    # --- client -------------------------------------------------------
    def _get_client(self) -> Any:
        if self._client is None:
            with self._lock:
                if self._client is None:
                    from hindsight_client import Hindsight  # imported lazily

                    self._client = Hindsight(
                        base_url=self._settings.hindsight_base_url,
                        api_key=self._settings.hindsight_api_key,
                        timeout=self._settings.hindsight_timeout,
                    )
        return self._client

    def _coerce(self, obj: Any) -> Any:
        if obj is None:
            return None
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            try:
                return obj.dict()
            except Exception:  # pragma: no cover - defensive
                pass
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "__dict__"):
            return dict(vars(obj))
        return obj

    @staticmethod
    def _fact_from_dict(d: dict[str, Any]) -> EngineFact:
        return EngineFact(
            id=str(d.get("id") or new_id("fact")),
            text=str(d.get("text") or ""),
            type=str(d.get("type") or "world"),
            context=d.get("context"),
            metadata={k: str(v) for k, v in (d.get("metadata") or {}).items()},
            tags=list(d.get("tags") or []),
            entities=[str(e) for e in (d.get("entities") or [])],
            occurred_start=d.get("occurred_start"),
            mentioned_at=d.get("mentioned_at"),
            document_id=d.get("document_id"),
            chunk_id=d.get("chunk_id"),
            scores={k: float(v) for k, v in (d.get("scores") or {}).items()},
        )

    # --- operations ---------------------------------------------------
    async def aretain(
        self,
        content: str,
        *,
        context: str | None = None,
        document_id: str | None = None,
        metadata: dict[str, str] | None = None,
        tags: list[str] | None = None,
        timestamp: datetime | None = None,
        retain_async: bool = False,
    ) -> dict[str, Any]:
        client = self._get_client()
        try:
            resp = await client.aretain(
                bank_id=self.bank_id,
                content=content,
                context=context,
                document_id=document_id,
                metadata=metadata or {},
                tags=tags or [],
                timestamp=timestamp,
                retain_async=retain_async,
            )
        except Exception as exc:  # noqa: BLE001 - surfaced to the API layer
            raise MemoryEngineUnavailable(
                f"Hindsight retain failed: {exc}"
            ) from exc
        return self._coerce(resp) or {"success": True}

    async def arecall(
        self,
        query: str,
        *,
        max_tokens: int = 4096,
        budget: str = "mid",
        types: list[str] | None = None,
        include_entities: bool = False,
    ) -> EngineRecallResult:
        client = self._get_client()
        started = time.perf_counter()
        try:
            resp = await client.arecall(
                bank_id=self.bank_id,
                query=query,
                max_tokens=max_tokens,
                budget=budget,
                types=types,
                include_entities=include_entities,
            )
        except Exception as exc:  # noqa: BLE001
            raise MemoryEngineUnavailable(
                f"Hindsight recall failed: {exc}"
            ) from exc
        elapsed = int((time.perf_counter() - started) * 1000)
        data = self._coerce(resp) or {}
        facts = [self._fact_from_dict(r) for r in (data.get("results") or [])]
        facts = [f for f in facts if f.text]
        return EngineRecallResult(
            facts=facts,
            latency_ms=elapsed,
            query=query,
            bank_id=self.bank_id,
            mode=self.mode,
            trace={
                "operation": "recall",
                "raw_result_count": len(data.get("results") or []),
                "hindsight_trace": data.get("trace"),
                "engine": "hindsight",
            },
            strategy_counts={"tempr": len(facts)},
        )

    async def areflect(
        self,
        query: str,
        *,
        budget: str = "low",
        context: str | None = None,
        max_tokens: int | None = None,
        include_facts: bool = True,
    ) -> EngineReflectResult:
        client = self._get_client()
        started = time.perf_counter()
        try:
            resp = await client.areflect(
                bank_id=self.bank_id,
                query=query,
                budget=budget,
                context=context,
                max_tokens=max_tokens,
                include_facts=include_facts,
            )
        except Exception as exc:  # noqa: BLE001
            raise MemoryEngineUnavailable(
                f"Hindsight reflect failed: {exc}"
            ) from exc
        elapsed = int((time.perf_counter() - started) * 1000)
        data = self._coerce(resp) or {}
        based_on_raw = (data.get("based_on") or {}) or {}
        memories = based_on_raw.get("memories") or []
        based_on = [
            self._fact_from_dict(
                {
                    "id": m.get("id"),
                    "text": m.get("text"),
                    "type": m.get("type"),
                    "context": m.get("context"),
                    "occurred_start": m.get("occurred_start"),
                }
            )
            for m in memories
        ]
        return EngineReflectResult(
            text=str(data.get("text") or ""),
            based_on=based_on,
            latency_ms=elapsed,
            query=query,
            bank_id=self.bank_id,
            mode=self.mode,
            trace={
                "operation": "reflect",
                "based_on_count": len(based_on),
                "usage": data.get("usage"),
                "engine": "hindsight",
            },
        )

    async def alist_memories(self, limit: int = 500) -> list[EngineFact]:
        client = self._get_client()
        try:
            resp = await client.alist_memories(
                bank_id=self.bank_id, limit=limit, offset=0
            )
        except Exception as exc:  # noqa: BLE001
            raise MemoryEngineUnavailable(
                f"Hindsight list_memories failed: {exc}"
            ) from exc
        data = self._coerce(resp) or {}
        raw = data.get("memories") or data.get("items") or data.get("results") or []
        return [self._fact_from_dict(r) for r in raw]

    async def ensure_bank(self) -> dict[str, Any]:
        """Create the dedicated bank and apply mission / directives / disposition."""
        client = self._get_client()
        result: dict[str, Any] = {"created": False, "configured": False}
        try:
            await client.acreate_bank(
                bank_id=self.bank_id,
                name="MemoryOS - NovaTech",
                mission=BANK_MISSION,
                disposition=BANK_DISPOSITION,
            )
            result["created"] = True
        except Exception as exc:  # noqa: BLE001
            result["create_error"] = str(exc)

        for directive in BANK_DIRECTIVES:
            try:
                await client.acreate_directive(bank_id=self.bank_id, text=directive)
                result["configured"] = True
            except Exception as exc:  # noqa: BLE001
                result.setdefault("directive_errors", []).append(str(exc))
        try:
            result["config"] = self._coerce(
                await client.aget_bank_config(bank_id=self.bank_id)
            )
        except Exception as exc:  # noqa: BLE001
            result["config_error"] = str(exc)
        return result

    async def health(self) -> EngineHealth:
        try:
            version = await self._get_client().aget_version()
            data = self._coerce(version) or {}
            self._version = str(
                data.get("version") or data.get("hindsight_version") or "unknown"
            )
            await self.ensure_bank()
            return EngineHealth(
                available=True,
                mode=self.mode,
                label="HINDSIGHT (LIVE)",
                bank_id=self.bank_id,
                detail=f"Connected to {self._settings.hindsight_base_url}",
                version=self._version,
            )
        except Exception as exc:  # noqa: BLE001
            return EngineHealth(
                available=False,
                mode=self.mode,
                label="HINDSIGHT (unreachable)",
                bank_id=self.bank_id,
                detail=str(exc),
            )


# ---------------------------------------------------------------------------
# Simulated Hindsight
# ---------------------------------------------------------------------------

SIM_SCHEMA = """
CREATE TABLE IF NOT EXISTS sim_facts (
    id            TEXT PRIMARY KEY,
    bank_id       TEXT NOT NULL,
    text          TEXT NOT NULL,
    type          TEXT NOT NULL,
    context       TEXT,
    metadata      TEXT NOT NULL DEFAULT '{}',
    tags          TEXT NOT NULL DEFAULT '[]',
    entities      TEXT NOT NULL DEFAULT '[]',
    occurred_start TEXT,
    mentioned_at  TEXT NOT NULL,
    document_id   TEXT,
    chunk_id      TEXT,
    source        TEXT NOT NULL DEFAULT 'simulated'
);
CREATE INDEX IF NOT EXISTS idx_sim_bank ON sim_facts(bank_id);
CREATE TABLE IF NOT EXISTS sim_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class SimulatedHindsightEngine(MemoryEngine):
    """A dependency-free stand-in for the Hindsight API contract.

    It stores facts, ranks them with a hybrid lexical/temporal/entity scorer
    (mimicking Hindsight's four retrieval arms) and produces a rule-based
    synthesis for ``reflect``. Everything it returns is tagged ``mode="simulated"``.
    """

    mode = "simulated"
    simulated = True

    _SENTENCE_SPLIT = ".!?;\n"

    def __init__(self, settings: Settings, path: Path | None = None) -> None:
        super().__init__(settings.hindsight_bank_id)
        self._settings = settings
        self._path = Path(path or settings.simulated_db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SIM_SCHEMA)
        self._conn.commit()

    # --- helpers ------------------------------------------------------
    def _split(self, content: str) -> list[str]:
        parts: list[str] = []
        buf = ""
        for ch in content:
            buf += ch
            if ch in self._SENTENCE_SPLIT:
                if len(buf.strip()) > 3:
                    parts.append(buf.strip())
                buf = ""
        if len(buf.strip()) > 3:
            parts.append(buf.strip())
        return [re.sub(r"^[-*\s]+", "", p) for p in parts if p.strip()]

    def _guess_type(self, text: str, metadata: dict[str, str]) -> str:
        hint = (metadata.get("memory_type") or "").upper()
        if hint in {"EXPERIENCE", "EVENT", "OUTCOME", "INCIDENT"}:
            return "experience"
        if hint in {"LESSON", "OBSERVATION", "DECISION", "CORRECTION", "HYPOTHESIS"}:
            return "observation"
        if hint in {"FACT", "RELATIONSHIP", "EXCEPTION", "COMMITMENT"}:
            return "world"
        return "world"

    def _entities(self, text: str, metadata: dict[str, str]) -> list[str]:
        found = {e for e in (metadata.get("entities") or "").split(",") if e.strip()}
        for token in content_tokens(text):
            if token.isupper() or (
                token.startswith("inc-") or token.startswith("arch-")
            ):
                found.add(token.strip())
        return sorted(found)

    # --- operations ---------------------------------------------------
    async def aretain(
        self,
        content: str,
        *,
        context: str | None = None,
        document_id: str | None = None,
        metadata: dict[str, str] | None = None,
        tags: list[str] | None = None,
        timestamp: datetime | None = None,
        retain_async: bool = False,
    ) -> dict[str, Any]:
        metadata = {k: str(v) for k, v in (metadata or {}).items()}
        sentences = self._split(content) or [content]
        rows: list[sqlite3.Row] = []
        now_iso = (timestamp or utcnow()).isoformat()
        with self._lock:
            for idx, sentence in enumerate(sentences):
                fact_id = stable_id(
                    "hfact",
                    self.bank_id,
                    document_id or content[:40],
                    str(idx),
                    sentence[:120],
                )
                fact_type = self._guess_type(sentence, metadata)
                self._conn.execute(
                    "INSERT OR REPLACE INTO sim_facts "
                    "(id, bank_id, text, type, context, metadata, tags, entities,"
                    " occurred_start, mentioned_at, document_id, chunk_id, source)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        fact_id,
                        self.bank_id,
                        sentence,
                        fact_type,
                        context,
                        json.dumps(metadata),
                        json.dumps(tags or []),
                        json.dumps(self._entities(sentence, metadata)),
                        now_iso,
                        now_iso,
                        document_id,
                        f"{document_id or 'doc'}:{idx}",
                        "simulated",
                    ),
                )
            self._conn.commit()
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM sim_facts WHERE document_id = ? AND bank_id = ?",
                (document_id, self.bank_id),
            )
            rows = cur.fetchall()
        return {
            "success": True,
            "bank_id": self.bank_id,
            "items_count": len(sentences),
            "simulated": True,
            "fact_ids": [r["id"] for r in rows],
        }

    def _all_facts(self) -> list[sqlite3.Row]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM sim_facts WHERE bank_id = ?", (self.bank_id,)
            )
            return cur.fetchall()

    @staticmethod
    def _row_to_fact(row: sqlite3.Row, score: float | None = None) -> EngineFact:
        return EngineFact(
            id=row["id"],
            text=row["text"],
            type=row["type"],
            context=row["context"],
            metadata=json.loads(row["metadata"] or "{}"),
            tags=json.loads(row["tags"] or "[]"),
            entities=json.loads(row["entities"] or "[]"),
            occurred_start=row["occurred_start"],
            mentioned_at=row["mentioned_at"],
            document_id=row["document_id"],
            chunk_id=row["chunk_id"],
            scores={"hybrid": round(score, 4)} if score is not None else {},
        )

    async def arecall(
        self,
        query: str,
        *,
        max_tokens: int = 4096,
        budget: str = "mid",
        types: list[str] | None = None,
        include_entities: bool = False,
    ) -> EngineRecallResult:
        started = time.perf_counter()
        rows = self._all_facts()
        q_tokens = content_tokens(query)
        q_set = set(q_tokens)
        docs = [content_tokens(r["text"]) for r in rows]
        n_docs = max(1, len(docs))
        df = Counter()
        for d in docs:
            df.update(set(d))
        avg_len = sum(len(d) for d in docs) / n_docs if docs else 1.0

        scored: list[tuple[float, sqlite3.Row, dict[str, float]]] = []
        for row, doc in zip(rows, docs):
            text_lower = row["text"].lower()
            # keyword arm (BM25-ish)
            bm25 = 0.0
            tf = Counter(doc)
            for term in q_set:
                if tf[term] == 0:
                    continue
                idf = math.log(1 + (n_docs - df[term] + 0.5) / (df[term] + 0.5))
                denom = tf[term] + 1.5 * (
                    1 - 0.75 + 0.75 * len(doc) / (avg_len or 1)
                )
                bm25 += idf * (tf[term] * 2.5) / (denom or 1)
            # semantic-ish arm: token overlap
            overlap = len(q_set & set(doc)) / (len(q_set) or 1)
            # entity arm
            row_entities = set(json.loads(row["entities"] or "[]"))
            ent_hits = len({e.lower() for e in row_entities} & q_set)
            entity = min(1.0, ent_hits / 2) if row_entities else 0.0
            # temporal arm: newer memories rank slightly higher
            recency = 0.0
            if row["mentioned_at"]:
                recency = 0.15
            hybrid = 0.5 * bm25 + 1.4 * overlap + 1.0 * entity + recency
            if bm25 == 0 and overlap == 0 and ent_hits == 0:
                hybrid = 0.0
            if hybrid > 0:
                scored.append(
                    (
                        hybrid,
                        row,
                        {
                            "keyword": round(bm25, 4),
                            "semantic": round(overlap, 4),
                            "graph": round(entity, 4),
                            "temporal": round(recency, 4),
                        },
                    )
                )
        scored.sort(key=lambda x: x[0], reverse=True)
        if types:
            scored = [s for s in scored if s[1]["type"] in types]

        # token budget, mirroring Hindsight's max_tokens semantics
        facts: list[EngineFact] = []
        used = 0
        limit = max(8, budget_limit(budget))
        for score, row, parts in scored:
            approx_tokens = max(1, len(row["text"]) // 4)
            if used + approx_tokens > max_tokens or len(facts) >= limit:
                break
            fact = self._row_to_fact(row, score)
            fact.scores = {**parts, "hybrid": round(score, 4)}
            if not include_entities:
                fact.entities = []
            facts.append(fact)
            used += approx_tokens

        elapsed = int((time.perf_counter() - started) * 1000)
        return EngineRecallResult(
            facts=facts,
            latency_ms=elapsed,
            query=query,
            bank_id=self.bank_id,
            mode=self.mode,
            trace={
                "operation": "recall",
                "simulated": True,
                "facts_stored": len(rows),
                "candidates_scored": len(scored),
                "engine": "simulated_hindsight",
            },
            strategy_counts={
                "semantic": sum(1 for f in facts if f.scores.get("semantic", 0) > 0),
                "keyword": sum(1 for f in facts if f.scores.get("keyword", 0) > 0),
                "graph": sum(1 for f in facts if f.scores.get("graph", 0) > 0),
            },
        )

    async def areflect(
        self,
        query: str,
        *,
        budget: str = "low",
        context: str | None = None,
        max_tokens: int | None = None,
        include_facts: bool = True,
    ) -> EngineReflectResult:
        recall = await self.arecall(query, max_tokens=max_tokens or 2048, budget=budget)
        facts = recall.facts
        started = time.perf_counter()
        lines: list[str] = []
        if context:
            lines.append(f"Context: {context}")
        if not facts:
            lines.append(
                "No stored experience matches this question. The bank holds no "
                "memories relevant to the query, so there is no organizational "
                "experience to reason from."
            )
        else:
            lines.append(
                f"Reasoning over {len(facts)} recalled memories from bank "
                f"{self.bank_id}:"
            )
            experiences = [f for f in facts if f.type == "experience"]
            observations = [f for f in facts if f.type == "observation"]
            worlds = [f for f in facts if f.type == "world"]
            if worlds:
                lines.append("Documented/structural facts:")
                lines.extend(f"- {truncate(f.text, 220)}" for f in worlds[:6])
            if experiences:
                lines.append("Historical experience:")
                lines.extend(f"- {truncate(f.text, 220)}" for f in experiences[:6])
            if observations:
                lines.append("Consolidated lessons and observations:")
                lines.extend(f"- {truncate(f.text, 220)}" for f in observations[:6])
            lines.append(
                "Synthesis: the memories above describe what the organization "
                "experienced before. They are historical evidence, not an absolute "
                "rule; the scope recorded with each memory decides whether it still "
                "applies to the current environment."
            )
        elapsed = int((time.perf_counter() - started) * 1000) + recall.latency_ms
        return EngineReflectResult(
            text="\n".join(lines),
            based_on=facts if include_facts else [],
            latency_ms=elapsed,
            query=query,
            bank_id=self.bank_id,
            mode=self.mode,
            trace={
                "operation": "reflect",
                "simulated": True,
                "based_on_count": len(facts),
                "engine": "simulated_hindsight",
                "note": "Rule-based synthesis. Not an LLM.",
            },
        )

    async def alist_memories(self, limit: int = 500) -> list[EngineFact]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM sim_facts WHERE bank_id = ? LIMIT ?",
                (self.bank_id, limit),
            )
            return [self._row_to_fact(r) for r in cur.fetchall()]

    async def ensure_bank(self) -> dict[str, Any]:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO sim_meta (key, value) VALUES (?,?)",
                ("mission", BANK_MISSION),
            )
            self._conn.execute(
                "INSERT OR REPLACE INTO sim_meta (key, value) VALUES (?,?)",
                ("directives", json.dumps(BANK_DIRECTIVES)),
            )
            self._conn.execute(
                "INSERT OR REPLACE INTO sim_meta (key, value) VALUES (?,?)",
                ("disposition", json.dumps(BANK_DISPOSITION)),
            )
            self._conn.commit()
        return {
            "created": True,
            "configured": True,
            "mission": BANK_MISSION,
            "directives": BANK_DIRECTIVES,
            "disposition": BANK_DISPOSITION,
            "simulated": True,
        }

    async def health(self) -> EngineHealth:
        count = self.fact_count()
        return EngineHealth(
            available=True,
            mode=self.mode,
            label="HINDSIGHT (SIMULATED)",
            bank_id=self.bank_id,
            detail=(
                "No Hindsight server reachable. Running the SIMULATED engine with "
                "the same retain/recall/reflect contract. Start Hindsight (see "
                "docker-compose.hindsight.yml) to switch to the real engine."
            ),
            version="simulated",
            simulated=True,
        )

    def reset(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM sim_facts")
            self._conn.execute("DELETE FROM sim_meta")
            self._conn.commit()

    def clear_local(self) -> None:
        """Clear locally-held engine state.

        Only the SIMULATED engine has local state. When Hindsight is live its bank
        is the system of record and is deliberately left intact, so a reset never
        destroys real organizational history.
        """
        self.reset()

    def fact_count(self) -> int:
        with self._lock:
            cur = self._conn.execute(
                "SELECT COUNT(*) AS n FROM sim_facts WHERE bank_id = ?", (self.bank_id,)
            )
            row = cur.fetchone()
        return int(row["n"]) if row else 0


def budget_limit(budget: str) -> int:
    return {"low": 8, "mid": 20, "high": 50}.get(budget, 20)


# ---------------------------------------------------------------------------
# Selection with graceful degradation
# ---------------------------------------------------------------------------


@dataclass
class EngineStatus:
    mode: str
    simulated: bool
    live_available: bool
    reason: str | None
    bank_id: str
    checked_at: str


class EngineManager:
    """Chooses between the live and simulated engines and remembers failures."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._live = HindsightEngine(self._settings)
        self._sim = SimulatedHindsightEngine(self._settings)
        self._active: MemoryEngine = self._sim
        self._failures = 0
        self._degraded_reason: str | None = None
        self._last_probe: str | None = None

    @property
    def active(self) -> MemoryEngine:
        return self._active

    @property
    def live(self) -> HindsightEngine:
        return self._live

    @property
    def simulated(self) -> SimulatedHindsightEngine:
        return self._sim

    @property
    def bank_id(self) -> str:
        return self._settings.hindsight_bank_id

    @property
    def degraded_reason(self) -> str | None:
        return self._degraded_reason

    def status(self) -> EngineStatus:
        return EngineStatus(
            mode=self._active.mode,
            simulated=self._active.simulated,
            live_available=self._live.simulated is False and self._failures == 0,
            reason=self._degraded_reason,
            bank_id=self.bank_id,
            checked_at=self._last_probe or utcnow().isoformat(),
        )

    async def probe(self) -> EngineHealth:
        """Try the live engine; fall back to SIMULATED with a recorded reason."""
        self._last_probe = utcnow().isoformat()
        if self._settings.force_simulated_engine:
            self._active = self._sim
            self._degraded_reason = "MEMORYOS_FORCE_SIMULATED=1"
            return await self._sim.health()
        health = await self._live.health()
        if health.available:
            self._active = self._live
            self._failures = 0
            self._degraded_reason = None
            return health
        self._failures += 1
        self._degraded_reason = truncate(health.detail, 300)
        self._active = self._sim
        return await self._sim.health()

    def _on_success(self) -> None:
        self._failures = 0
        self._degraded_reason = None

    def _on_failure(self, exc: Exception) -> None:
        self._failures += 1
        self._degraded_reason = truncate(str(exc), 300)
        if self._failures >= self._settings.live_failure_threshold:
            self._active = self._sim

    async def aretain(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            out = await self._active.aretain(*args, **kwargs)
            self._on_success()
            return out
        except MemoryEngineUnavailable as exc:
            self._on_failure(exc)
            if isinstance(self._active, SimulatedHindsightEngine):
                raise
            return await self._sim.aretain(*args, **kwargs)

    async def arecall(self, *args: Any, **kwargs: Any) -> EngineRecallResult:
        try:
            out = await self._active.arecall(*args, **kwargs)
            self._on_success()
            return out
        except MemoryEngineUnavailable as exc:
            self._on_failure(exc)
            if isinstance(self._active, SimulatedHindsightEngine):
                raise
            return await self._sim.arecall(*args, **kwargs)

    async def areflect(self, *args: Any, **kwargs: Any) -> EngineReflectResult:
        try:
            out = await self._active.areflect(*args, **kwargs)
            self._on_success()
            return out
        except MemoryEngineUnavailable as exc:
            self._on_failure(exc)
            if isinstance(self._active, SimulatedHindsightEngine):
                raise
            return await self._sim.areflect(*args, **kwargs)

    async def ensure_bank(self) -> dict[str, Any]:
        return await self._active.ensure_bank()

    async def health(self) -> EngineHealth:
        return await self.probe()

    async def aclose(self) -> None:
        """Release the live HTTP client, if one was ever created."""
        client = self._live._client
        if client is not None:
            try:
                await client.aclose()
            except Exception:  # noqa: BLE001 - best effort on shutdown
                pass
            self._live._client = None

    def reset_for_tests(self) -> None:
        self._active = self._sim
        self._failures = 0
        self._degraded_reason = None

    def clear_local(self) -> None:
        """Clear locally-held engine state.

        Only the SIMULATED engine keeps state on disk. When Hindsight is live its
        bank is the system of record, so a reset must not destroy real
        organizational history.
        """
        self._sim.clear_local()


_manager: EngineManager | None = None
_manager_lock = asyncio.Lock()


def get_engine_manager() -> EngineManager:
    global _manager
    if _manager is None:
        _manager = EngineManager()
    return _manager


def reset_engine_manager() -> None:
    global _manager
    _manager = None


__all__ = [
    "BANK_DIRECTIVES",
    "BANK_DISPOSITION",
    "BANK_MISSION",
    "EngineFact",
    "EngineHealth",
    "EngineManager",
    "EngineRecallResult",
    "EngineReflectResult",
    "EngineStatus",
    "HindsightEngine",
    "MemoryEngine",
    "MemoryEngineError",
    "MemoryEngineUnavailable",
    "SimulatedHindsightEngine",
    "get_engine_manager",
    "reset_engine_manager",
]
