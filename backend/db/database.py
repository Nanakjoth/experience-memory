"""SQLite storage for application metadata, audit, evidence and demo state.

This is NOT a vector database. Hindsight is the memory engine and the only place
raw experience lives. SQLite stores the governance envelope around it:
metadata, permissions, lifecycle history, audit trail and UI state.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.config import get_settings
from backend.models.audit import AuditEvent, AuditEventType
from backend.models.memory import (
    Contradiction,
    EvidenceLink,
    LearningEvent,
    MemoryEvent,
    MemoryRecord,
    utcnow,
)
from backend.utils import enum_str, enum_value

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id                  TEXT PRIMARY KEY,
    type                TEXT NOT NULL,
    title               TEXT NOT NULL,
    content             TEXT NOT NULL,
    summary             TEXT DEFAULT '',
    source_type         TEXT NOT NULL,
    source_id           TEXT NOT NULL,
    source_name         TEXT NOT NULL,
    captured_at         TEXT NOT NULL,
    observed_at         TEXT,
    scope               TEXT NOT NULL,
    owner               TEXT NOT NULL,
    domain              TEXT NOT NULL,
    purpose             TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    last_validated_at   TEXT,
    expiry_at           TEXT,
    confidence          REAL NOT NULL DEFAULT 0.5,
    evidence_count      INTEGER NOT NULL DEFAULT 0,
    status              TEXT NOT NULL,
    sensitivity         TEXT NOT NULL,
    access_level        TEXT NOT NULL,
    visibility          TEXT NOT NULL,
    related_entities    TEXT NOT NULL DEFAULT '[]',
    related_memories    TEXT NOT NULL DEFAULT '[]',
    hindsight_fact_id   TEXT,
    hindsight_document_id TEXT,
    gate                TEXT,
    human_confirmed     INTEGER NOT NULL DEFAULT 0,
    promoted_by         TEXT,
    version             INTEGER NOT NULL DEFAULT 1,
    tags                TEXT NOT NULL DEFAULT '[]',
    extra               TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_memories_scope     ON memories(scope);
CREATE INDEX IF NOT EXISTS idx_memories_status   ON memories(status);
CREATE INDEX IF NOT EXISTS idx_memories_type     ON memories(type);
CREATE INDEX IF NOT EXISTS idx_memories_visibility ON memories(visibility);
CREATE INDEX IF NOT EXISTS idx_memories_source   ON memories(source_id);
CREATE INDEX IF NOT EXISTS idx_memories_hs       ON memories(hindsight_fact_id);

CREATE TABLE IF NOT EXISTS memory_events (
    id          TEXT PRIMARY KEY,
    memory_id   TEXT NOT NULL,
    at          TEXT NOT NULL,
    from_status TEXT,
    to_status   TEXT NOT NULL,
    action      TEXT NOT NULL,
    actor       TEXT NOT NULL,
    note        TEXT DEFAULT '',
    payload     TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_events_memory ON memory_events(memory_id, at);

CREATE TABLE IF NOT EXISTS evidence (
    memory_id      TEXT NOT NULL,
    evidence_type  TEXT NOT NULL,
    evidence_id    TEXT NOT NULL,
    evidence_label TEXT NOT NULL,
    polarity       TEXT NOT NULL DEFAULT 'supports',
    detail         TEXT DEFAULT '',
    created_at     TEXT NOT NULL,
    PRIMARY KEY (memory_id, evidence_type, evidence_id)
);

CREATE TABLE IF NOT EXISTS contradictions (
    id                      TEXT PRIMARY KEY,
    memory_id               TEXT NOT NULL,
    memory_title            TEXT NOT NULL,
    memory_scope            TEXT NOT NULL,
    conflicting_source_id   TEXT NOT NULL,
    conflicting_source_type TEXT NOT NULL,
    conflicting_content     TEXT NOT NULL,
    current_environment     TEXT NOT NULL,
    detected_at             TEXT NOT NULL,
    reason                  TEXT NOT NULL,
    status                  TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED',
    resolution              TEXT,
    resolved_at             TEXT,
    resolved_by             TEXT
);

CREATE TABLE IF NOT EXISTS audit_events (
    id          TEXT PRIMARY KEY,
    at          TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    actor       TEXT NOT NULL,
    actor_role  TEXT NOT NULL DEFAULT 'system',
    subject     TEXT DEFAULT '',
    memory_id   TEXT,
    request_id  TEXT,
    detail      TEXT DEFAULT '',
    payload     TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_audit_at ON audit_events(at DESC);

CREATE TABLE IF NOT EXISTS learning_events (
    id        TEXT PRIMARY KEY,
    at        TEXT NOT NULL,
    kind      TEXT NOT NULL,
    message   TEXT NOT NULL,
    memory_id TEXT,
    detail    TEXT DEFAULT '',
    synthetic INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_learning_at ON learning_events(at DESC);

CREATE TABLE IF NOT EXISTS incidents (
    id            TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    system        TEXT NOT NULL,
    service       TEXT NOT NULL,
    component     TEXT NOT NULL,
    severity      TEXT NOT NULL,
    status        TEXT NOT NULL,
    opened_at     TEXT NOT NULL,
    resolved_at   TEXT,
    engineer      TEXT NOT NULL,
    queue_depth   REAL,
    action        TEXT NOT NULL,
    outcome       TEXT NOT NULL,
    duplicate_processing INTEGER NOT NULL DEFAULT 0,
    narrative     TEXT NOT NULL,
    metrics       TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS systems_registry (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    owner         TEXT NOT NULL,
    team          TEXT NOT NULL,
    domain        TEXT NOT NULL,
    criticality   TEXT NOT NULL DEFAULT 'medium',
    components    TEXT NOT NULL DEFAULT '[]',
    active_component TEXT,
    knowledge_count INTEGER NOT NULL DEFAULT 0,
    validated_count  INTEGER NOT NULL DEFAULT 0,
    dependency_depth INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS employees (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    role       TEXT NOT NULL,
    team       TEXT NOT NULL,
    systems    TEXT NOT NULL DEFAULT '[]',
    status     TEXT NOT NULL DEFAULT 'active',
    note       TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS architecture_changes (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    system      TEXT NOT NULL,
    component   TEXT NOT NULL,
    effective_at TEXT NOT NULL,
    summary     TEXT NOT NULL,
    invalidates_scope TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings_kv (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS metrics (
    key   TEXT PRIMARY KEY,
    value INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS conversations (
    id         TEXT PRIMARY KEY,
    actor_id   TEXT NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    at         TEXT NOT NULL,
    turn_index INTEGER NOT NULL DEFAULT 0
);
"""


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def _json_loads(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_dt(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


class Database:
    """Thin, explicit SQLite wrapper. Thread-safe via a single lock."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self.migrate()

    # --- plumbing -----------------------------------------------------
    def migrate(self) -> None:
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    @contextmanager
    def cursor(self) -> Iterator[sqlite3.Cursor]:
        with self._lock:
            cur = self._conn.cursor()
            try:
                yield cur
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
            finally:
                cur.close()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def reset(self) -> None:
        """Drop every row. Used by the demo reset control."""
        tables = [
            "memories",
            "memory_events",
            "evidence",
            "contradictions",
            "audit_events",
            "learning_events",
            "incidents",
            "systems_registry",
            "employees",
            "architecture_changes",
            "settings_kv",
            "metrics",
            "conversations",
        ]
        with self.cursor() as cur:
            for t in tables:
                cur.execute(f"DELETE FROM {t}")

    # --- memories -----------------------------------------------------
    def upsert_memory(self, mem: MemoryRecord) -> MemoryRecord:
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO memories (
                    id, type, title, content, summary, source_type, source_id,
                    source_name, captured_at, observed_at, scope, owner, domain,
                    purpose, created_at, last_validated_at, expiry_at, confidence,
                    evidence_count, status, sensitivity, access_level, visibility,
                    related_entities, related_memories, hindsight_fact_id,
                    hindsight_document_id, gate, human_confirmed, promoted_by,
                    version, tags, extra
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    type=excluded.type, title=excluded.title, content=excluded.content,
                    summary=excluded.summary, source_type=excluded.source_type,
                    source_id=excluded.source_id, source_name=excluded.source_name,
                    captured_at=excluded.captured_at, observed_at=excluded.observed_at,
                    scope=excluded.scope, owner=excluded.owner, domain=excluded.domain,
                    purpose=excluded.purpose, created_at=excluded.created_at,
                    last_validated_at=excluded.last_validated_at, expiry_at=excluded.expiry_at,
                    confidence=excluded.confidence, evidence_count=excluded.evidence_count,
                    status=excluded.status, sensitivity=excluded.sensitivity,
                    access_level=excluded.access_level, visibility=excluded.visibility,
                    related_entities=excluded.related_entities,
                    related_memories=excluded.related_memories,
                    hindsight_fact_id=excluded.hindsight_fact_id,
                    hindsight_document_id=excluded.hindsight_document_id,
                    gate=excluded.gate, human_confirmed=excluded.human_confirmed,
                    promoted_by=excluded.promoted_by, version=excluded.version,
                    tags=excluded.tags, extra=excluded.extra
                """,
                (
                    mem.id,
                    enum_str(mem.type),
                    mem.title,
                    mem.content,
                    mem.summary,
                    mem.source_type,
                    mem.source_id,
                    mem.source_name,
                    _iso(mem.captured_at),
                    _iso(mem.observed_at),
                    mem.scope,
                    mem.owner,
                    mem.domain,
                    mem.purpose,
                    _iso(mem.created_at),
                    _iso(mem.last_validated_at),
                    _iso(mem.expiry_at),
                    mem.confidence,
                    mem.evidence_count,
                    enum_str(mem.status),
                    enum_str(mem.sensitivity),
                    enum_str(mem.access_level),
                    enum_str(mem.visibility),
                    json.dumps(mem.related_entities),
                    json.dumps(mem.related_memories),
                    mem.hindsight_fact_id,
                    mem.hindsight_document_id,
                    json.dumps(mem.gate.model_dump(mode="json")) if mem.gate else None,
                    int(mem.human_confirmed),
                    mem.promoted_by,
                    mem.version,
                    json.dumps(mem.tags),
                    json.dumps(mem.extra, default=str),
                ),
            )
        return mem

    @staticmethod
    def _to_memory(row: sqlite3.Row | dict[str, Any]) -> MemoryRecord:
        d = _row_to_dict(row) if isinstance(row, sqlite3.Row) else dict(row)
        gate_raw = _json_loads(d.get("gate"), None)
        return MemoryRecord(
            id=d["id"],
            type=d["type"],
            title=d["title"],
            content=d["content"],
            summary=d.get("summary") or "",
            source_type=d["source_type"],
            source_id=d["source_id"],
            source_name=d["source_name"],
            captured_at=_parse_dt(d["captured_at"]) or utcnow(),
            observed_at=_parse_dt(d.get("observed_at")),
            scope=d["scope"],
            owner=d["owner"],
            domain=d["domain"],
            purpose=d["purpose"],
            created_at=_parse_dt(d["created_at"]) or utcnow(),
            last_validated_at=_parse_dt(d.get("last_validated_at")),
            expiry_at=_parse_dt(d.get("expiry_at")),
            confidence=float(d.get("confidence") or 0.5),
            evidence_count=int(d.get("evidence_count") or 0),
            status=d["status"],
            sensitivity=d["sensitivity"],
            access_level=d["access_level"],
            visibility=d["visibility"],
            related_entities=_json_loads(d.get("related_entities"), []),
            related_memories=_json_loads(d.get("related_memories"), []),
            hindsight_fact_id=d.get("hindsight_fact_id"),
            hindsight_document_id=d.get("hindsight_document_id"),
            gate=gate_raw,
            human_confirmed=bool(d.get("human_confirmed")),
            promoted_by=d.get("promoted_by"),
            version=int(d.get("version") or 1),
            tags=_json_loads(d.get("tags"), []),
            extra=_json_loads(d.get("extra"), {}),
        )

    def get_memory(self, memory_id: str) -> MemoryRecord | None:
        with self.cursor() as cur:
            cur.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
            row = cur.fetchone()
        return self._to_memory(row) if row else None

    def list_memories(
        self,
        *,
        type_: str | None = None,
        scope: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        status: str | None = None,
        visibility: str | None = None,
        owner: str | None = None,
        entity: str | None = None,
        system: str | None = None,
        min_confidence: float | None = None,
        min_evidence: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        search: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> tuple[list[MemoryRecord], int]:
        clauses: list[str] = []
        params: list[Any] = []
        if type_:
            clauses.append("type = ?")
            params.append(type_)
        if scope:
            clauses.append("scope = ?")
            params.append(scope)
        if source_type:
            clauses.append("source_type = ?")
            params.append(source_type)
        if source_id:
            clauses.append("source_id = ?")
            params.append(source_id)
        if status:
            # 'OPEN' means anything that is not archived or rejected.
            if status.upper() == "OPEN":
                clauses.append("status NOT IN ('ARCHIVED','REJECTED')")
            else:
                clauses.append("status = ?")
                params.append(status)
        if visibility:
            clauses.append("visibility = ?")
            params.append(visibility)
        if owner:
            clauses.append("owner = ?")
            params.append(owner)
        if min_confidence is not None:
            clauses.append("confidence >= ?")
            params.append(min_confidence)
        if min_evidence is not None:
            clauses.append("evidence_count >= ?")
            params.append(min_evidence)
        if date_from:
            clauses.append("created_at >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("created_at <= ?")
            params.append(date_to)
        if search:
            clauses.append("(lower(title) LIKE ? OR lower(content) LIKE ? OR lower(summary) LIKE ?)")
            like = f"%{search.lower()}%"
            params.extend([like, like, like])
        if entity:
            clauses.append("lower(related_entities) LIKE ?")
            params.append(f'%"{entity.lower()}"%')
        if system:
            clauses.append("(lower(scope) LIKE ? OR lower(domain) LIKE ?)")
            like = f"%{system.lower()}%"
            params.extend([like, like])

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS n FROM memories {where}", params)
            total = int(cur.fetchone()["n"])
            cur.execute(
                f"SELECT * FROM memories {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [*params, limit, offset],
            )
            rows = cur.fetchall()
        return [self._to_memory(r) for r in rows], total

    def all_memories(self) -> list[MemoryRecord]:
        items, _ = self.list_memories(limit=10_000)
        return items

    def delete_memory(self, memory_id: str) -> None:
        with self.cursor() as cur:
            cur.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            cur.execute("DELETE FROM memory_events WHERE memory_id = ?", (memory_id,))
            cur.execute("DELETE FROM evidence WHERE memory_id = ?", (memory_id,))

    def count_by(self, column: str) -> dict[str, int]:
        allowed = {
            "type",
            "status",
            "visibility",
            "scope",
            "source_type",
            "owner",
            "domain",
        }
        if column not in allowed:
            raise ValueError(f"cannot group by {column}")
        with self.cursor() as cur:
            cur.execute(
                f"SELECT {column} AS k, COUNT(*) AS n FROM memories GROUP BY {column}"
            )
            return {r["k"]: r["n"] for r in cur.fetchall()}

    def confidence_buckets(self) -> dict[str, int]:
        buckets = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "VERY_HIGH": 0}
        for m in self.all_memories():
            from backend.memory.confidence import band_for

            buckets[band_for(m.confidence)] += 1
        return buckets

    # --- memory events / history --------------------------------------
    def add_memory_event(self, event: MemoryEvent) -> MemoryEvent:
        with self.cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO memory_events "
                "(id, memory_id, at, from_status, to_status, action, actor, note, payload)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    event.id,
                    event.memory_id,
                    _iso(event.at),
                    enum_str(event.from_status),
                    enum_str(event.to_status),
                    event.action,
                    event.actor,
                    event.note,
                    json.dumps(event.payload, default=str),
                ),
            )
        return event

    def memory_history(self, memory_id: str) -> list[MemoryEvent]:
        with self.cursor() as cur:
            cur.execute(
                "SELECT * FROM memory_events WHERE memory_id = ? ORDER BY at ASC",
                (memory_id,),
            )
            rows = cur.fetchall()
        out: list[MemoryEvent] = []
        for r in rows:
            d = _row_to_dict(r)
            out.append(
                MemoryEvent(
                    id=d["id"],
                    memory_id=d["memory_id"],
                    at=_parse_dt(d["at"]) or utcnow(),
                    from_status=d["from_status"],
                    to_status=d["to_status"],
                    action=d["action"],
                    actor=d["actor"],
                    note=d["note"] or "",
                    payload=_json_loads(d["payload"], {}),
                )
            )
        return out

    # --- evidence -----------------------------------------------------
    def add_evidence(self, link: EvidenceLink) -> EvidenceLink:
        with self.cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO evidence "
                "(memory_id, evidence_type, evidence_id, evidence_label, polarity, detail, created_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (
                    link.memory_id,
                    link.evidence_type,
                    link.evidence_id,
                    link.evidence_label,
                    link.polarity,
                    link.detail,
                    _iso(link.created_at),
                ),
            )
        return link

    def evidence_for(self, memory_id: str) -> list[EvidenceLink]:
        with self.cursor() as cur:
            cur.execute("SELECT * FROM evidence WHERE memory_id = ?", (memory_id,))
            rows = cur.fetchall()
        return [
            EvidenceLink(
                memory_id=r["memory_id"],
                evidence_type=r["evidence_type"],
                evidence_id=r["evidence_id"],
                evidence_label=r["evidence_label"],
                polarity=r["polarity"],
                detail=r["detail"] or "",
                created_at=_parse_dt(r["created_at"]) or utcnow(),
            )
            for r in rows
        ]

    def evidence_map(self) -> dict[str, list[EvidenceLink]]:
        with self.cursor() as cur:
            cur.execute("SELECT * FROM evidence")
            rows = cur.fetchall()
        out: dict[str, list[EvidenceLink]] = {}
        for r in rows:
            link = EvidenceLink(
                memory_id=r["memory_id"],
                evidence_type=r["evidence_type"],
                evidence_id=r["evidence_id"],
                evidence_label=r["evidence_label"],
                polarity=r["polarity"],
                detail=r["detail"] or "",
                created_at=_parse_dt(r["created_at"]) or utcnow(),
            )
            out.setdefault(link.memory_id, []).append(link)
        return out

    def refresh_evidence_counts(self) -> None:
        counts: dict[str, int] = {}
        for links in self.evidence_map().values():
            counts[links[0].memory_id] = sum(1 for x in links if x.polarity == "supports")
        with self.cursor() as cur:
            for mid, n in counts.items():
                cur.execute("UPDATE memories SET evidence_count = ? WHERE id = ?", (n, mid))

    # --- contradictions ----------------------------------------------
    def add_contradiction(self, c: Contradiction) -> Contradiction:
        with self.cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO contradictions "
                "(id, memory_id, memory_title, memory_scope, conflicting_source_id,"
                " conflicting_source_type, conflicting_content, current_environment,"
                " detected_at, reason, status, resolution, resolved_at, resolved_by)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    c.id,
                    c.memory_id,
                    c.memory_title,
                    c.memory_scope,
                    c.conflicting_source_id,
                    c.conflicting_source_type,
                    c.conflicting_content,
                    c.current_environment,
                    _iso(c.detected_at),
                    c.reason,
                    c.status,
                    c.resolution,
                    _iso(c.resolved_at),
                    c.resolved_by,
                ),
            )
        return c

    def list_contradictions(self, status: str | None = None) -> list[Contradiction]:
        sql = "SELECT * FROM contradictions"
        params: list[Any] = []
        if status:
            sql += " WHERE status = ?"
            params.append(status)
        sql += " ORDER BY detected_at DESC"
        with self.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [
            Contradiction(
                id=r["id"],
                memory_id=r["memory_id"],
                memory_title=r["memory_title"],
                memory_scope=r["memory_scope"],
                conflicting_source_id=r["conflicting_source_id"],
                conflicting_source_type=r["conflicting_source_type"],
                conflicting_content=r["conflicting_content"],
                current_environment=r["current_environment"],
                detected_at=_parse_dt(r["detected_at"]) or utcnow(),
                reason=r["reason"],
                status=r["status"],
                resolution=r["resolution"],
                resolved_at=_parse_dt(r["resolved_at"]),
                resolved_by=r["resolved_by"],
            )
            for r in rows
        ]

    def get_contradiction(self, cid: str) -> Contradiction | None:
        for c in self.list_contradictions():
            if c.id == cid:
                return c
        return None

    # --- audit --------------------------------------------------------
    def add_audit(self, event: AuditEvent) -> AuditEvent:
        with self.cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO audit_events "
                "(id, at, event_type, actor, actor_role, subject, memory_id, request_id, detail, payload)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    event.id,
                    _iso(event.at),
                    enum_str(event.event_type),
                    event.actor,
                    event.actor_role,
                    event.subject,
                    event.memory_id,
                    event.request_id,
                    event.detail,
                    json.dumps(event.payload, default=str),
                ),
            )
        return event

    def list_audit(
        self,
        *,
        event_type: str | None = None,
        actor: str | None = None,
        memory_id: str | None = None,
        limit: int = 200,
    ) -> list[AuditEvent]:
        clauses: list[str] = []
        params: list[Any] = []
        if event_type:
            clauses.append("event_type = ?")
            params.append(event_type)
        if actor:
            clauses.append("actor = ?")
            params.append(actor)
        if memory_id:
            clauses.append("memory_id = ?")
            params.append(memory_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.cursor() as cur:
            cur.execute(
                f"SELECT * FROM audit_events {where} ORDER BY at DESC LIMIT ?",
                [*params, limit],
            )
            rows = cur.fetchall()
        return [
            AuditEvent(
                id=r["id"],
                at=_parse_dt(r["at"]) or utcnow(),
                event_type=r["event_type"],
                actor=r["actor"],
                actor_role=r["actor_role"],
                subject=r["subject"] or "",
                memory_id=r["memory_id"],
                request_id=r["request_id"],
                detail=r["detail"] or "",
                payload=_json_loads(r["payload"], {}),
            )
            for r in rows
        ]

    # --- learning events ----------------------------------------------
    def add_learning_event(self, ev: LearningEvent) -> LearningEvent:
        with self.cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO learning_events "
                "(id, at, kind, message, memory_id, detail, synthetic) VALUES (?,?,?,?,?,?,?)",
                (
                    ev.id,
                    _iso(ev.at),
                    ev.kind,
                    ev.message,
                    ev.memory_id,
                    ev.detail,
                    int(ev.synthetic),
                ),
            )
        return ev

    def list_learning_events(self, limit: int = 25) -> list[LearningEvent]:
        with self.cursor() as cur:
            cur.execute(
                "SELECT * FROM learning_events ORDER BY at DESC LIMIT ?", (limit,)
            )
            rows = cur.fetchall()
        return [
            LearningEvent(
                id=r["id"],
                at=_parse_dt(r["at"]) or utcnow(),
                kind=r["kind"],
                message=r["message"],
                memory_id=r["memory_id"],
                detail=r["detail"] or "",
                synthetic=bool(r["synthetic"]),
            )
            for r in rows
        ]

    # --- domain tables -----------------------------------------------
    def upsert_incident(self, inc: dict[str, Any]) -> None:
        with self.cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO incidents "
                "(id,title,system,service,component,severity,status,opened_at,resolved_at,"
                "engineer,queue_depth,action,outcome,duplicate_processing,narrative,metrics)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    inc["id"],
                    inc["title"],
                    inc["system"],
                    inc["service"],
                    inc["component"],
                    inc["severity"],
                    inc["status"],
                    inc["opened_at"],
                    inc.get("resolved_at"),
                    inc["engineer"],
                    inc.get("queue_depth"),
                    inc["action"],
                    inc["outcome"],
                    int(inc.get("duplicate_processing", 0)),
                    inc["narrative"],
                    json.dumps(inc.get("metrics", {})),
                ),
            )

    def list_incidents(self, system: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM incidents"
        params: list[Any] = []
        if system:
            sql += " WHERE system = ?"
            params.append(system)
        sql += " ORDER BY opened_at ASC"
        with self.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        out = []
        for r in rows:
            d = _row_to_dict(r)
            d["metrics"] = _json_loads(d.get("metrics"), {})
            d["duplicate_processing"] = bool(d["duplicate_processing"])
            out.append(d)
        return out

    def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        for i in self.list_incidents():
            if i["id"] == incident_id:
                return i
        return None

    def upsert_system(self, row: dict[str, Any]) -> None:
        with self.cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO systems_registry "
                "(id,name,owner,team,domain,criticality,components,active_component,"
                "knowledge_count,validated_count,dependency_depth) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    row["id"],
                    row["name"],
                    row["owner"],
                    row["team"],
                    row["domain"],
                    row["criticality"],
                    json.dumps(row.get("components", [])),
                    row.get("active_component"),
                    int(row.get("knowledge_count", 0)),
                    int(row.get("validated_count", 0)),
                    int(row.get("dependency_depth", 1)),
                ),
            )

    def list_systems(self) -> list[dict[str, Any]]:
        with self.cursor() as cur:
            cur.execute("SELECT * FROM systems_registry ORDER BY name")
            rows = cur.fetchall()
        out = []
        for r in rows:
            d = _row_to_dict(r)
            d["components"] = _json_loads(d.get("components"), [])
            out.append(d)
        return out

    def get_system(self, system_id: str) -> dict[str, Any] | None:
        for s in self.list_systems():
            if s["id"] == system_id:
                return s
        return None

    def upsert_employee(self, row: dict[str, Any]) -> None:
        with self.cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO employees (id,name,role,team,systems,status,note)"
                " VALUES (?,?,?,?,?,?,?)",
                (
                    row["id"],
                    row["name"],
                    row["role"],
                    row["team"],
                    json.dumps(row.get("systems", [])),
                    row.get("status", "active"),
                    row.get("note", ""),
                ),
            )

    def list_employees(self) -> list[dict[str, Any]]:
        with self.cursor() as cur:
            cur.execute("SELECT * FROM employees ORDER BY name")
            rows = cur.fetchall()
        out = []
        for r in rows:
            d = _row_to_dict(r)
            d["systems"] = _json_loads(d.get("systems"), [])
            out.append(d)
        return out

    def get_employee(self, employee_id: str) -> dict[str, Any] | None:
        for e in self.list_employees():
            if e["id"] == employee_id:
                return e
        return None

    def upsert_architecture_change(self, row: dict[str, Any]) -> None:
        with self.cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO architecture_changes "
                "(id,title,system,component,effective_at,summary,invalidates_scope,created_at)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (
                    row["id"],
                    row["title"],
                    row["system"],
                    row["component"],
                    row["effective_at"],
                    row["summary"],
                    row.get("invalidates_scope"),
                    row.get("created_at") or utcnow().isoformat(),
                ),
            )

    def list_architecture_changes(self) -> list[dict[str, Any]]:
        with self.cursor() as cur:
            cur.execute("SELECT * FROM architecture_changes ORDER BY effective_at DESC")
            return [_row_to_dict(r) for r in cur.fetchall()]

    # --- kv + metrics -------------------------------------------------
    def set_value(self, key: str, value: Any) -> None:
        with self.cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO settings_kv (key, value) VALUES (?,?)",
                (key, json.dumps(value, default=str)),
            )

    def get_value(self, key: str, default: Any = None) -> Any:
        with self.cursor() as cur:
            cur.execute("SELECT value FROM settings_kv WHERE key = ?", (key,))
            row = cur.fetchone()
        return _json_loads(row["value"], default) if row else default

    def bump_metric(self, key: str, delta: int = 1) -> int:
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO metrics (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = value + ?",
                (key, delta, delta),
            )
            cur.execute("SELECT value FROM metrics WHERE key = ?", (key,))
            row = cur.fetchone()
        return int(row["value"]) if row else 0

    def metrics(self) -> dict[str, int]:
        with self.cursor() as cur:
            cur.execute("SELECT key, value FROM metrics")
            return {r["key"]: r["value"] for r in cur.fetchall()}

    def reset_metrics(self) -> None:
        with self.cursor() as cur:
            cur.execute("DELETE FROM metrics")

    # --- conversations ------------------------------------------------
    def add_conversation_turn(
        self, *, actor_id: str, role: str, content: str, turn_index: int
    ) -> dict[str, Any]:
        from backend.utils import new_id

        row = {
            "id": new_id("conv"),
            "actor_id": actor_id,
            "role": role,
            "content": content,
            "at": utcnow().isoformat(),
            "turn_index": turn_index,
        }
        with self.cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO conversations (id, actor_id, role, content, at, turn_index)"
                " VALUES (?,?,?,?,?,?)",
                (row["id"], row["actor_id"], row["role"], row["content"], row["at"], turn_index),
            )
        return row

    def list_conversation(self, actor_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        sql = "SELECT * FROM conversations"
        params: list[Any] = []
        if actor_id:
            sql += " WHERE actor_id = ?"
            params.append(actor_id)
        sql += " ORDER BY turn_index ASC, at ASC LIMIT ?"
        params.append(limit)
        with self.cursor() as cur:
            cur.execute(sql, params)
            return [_row_to_dict(r) for r in cur.fetchall()]


_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database(get_settings().app_db_path)
    return _db


def reset_db() -> None:
    """Drop and recreate the process-wide database handle (used by tests)."""
    global _db
    if _db is not None:
        _db.close()
    _db = None


__all__ = ["AuditEventType", "Database", "get_db", "reset_db"]
