# MEMORYOS — Architecture

This document explains how the system is put together and, more importantly, why
each boundary exists. For runtime behaviour see [`flow.md`](flow.md).

---

## 1. Design position

MemoryOS is not a chatbot, not RAG over documents, and not an offboarding form.
It is an **operational memory system** with a governance model attached. Three
commitments drive every structural decision:

1. **Hindsight is the engine.** Memory lives in the bank. The application stores
   *governance metadata about* memory, never a competing copy of the knowledge.
2. **Nothing is stored before it is authorized.** The Memory Gate runs ahead of
   retention, so the engine can never become a store that outlives policy.
3. **Nothing is silently trusted.** Every answer carries its evidence, its
   confidence breakdown, its reasoning trace, and what it refused to tell you.

---

## 2. Two-store split

```
┌─────────────────────────────────┐        ┌──────────────────────────────┐
│ Application store (SQLite)      │        │ Memory engine (Hindsight)    │
│ backend/data/memoryos.db       │        │ bank: memoryos-novatech     │
│                                 │        │                              │
│ memories      governance meta   │◀──────▶│ retain()  approved claims    │
│ memory_events lifecycle history │ fact_id│ recall()  evidence           │
│ evidence      links             │        │ reflect() synthesis          │
│ contradictions                  │        │                              │
│ audit_events   full trail       │        │ separate store when          │
│ learning_events                 │        │ SIMULATED:                   │
│ incidents / systems / employees │        │ hindsight_sim.db             │
│ conversations metrics           │        │                              │
└─────────────────────────────────┘        └──────────────────────────────┘
```

**Why split.** Hindsight is a memory bank. It deliberately does not carry
application governance: who may read a memory, whether it has been human-verified,
which contradictions are open. Those are MemoryOS concerns, so they live in
SQLite and reference the engine through `hindsight_fact_id` and
`hindsight_document_id`.

**Consequence.** Deleting app metadata does not delete engine content, and
rebuilding the app database does not lose the memory bank. The simulated engine
gets its own database precisely so that "simulated" state is never mistaken for
application state.

---

## 3. Layering

Dependencies point downward only. No module imports a route; no route contains
domain logic.

```
routes / api/          HTTP shape only: parse, delegate, serialise
     │
services layer         orchestration: ingestion, retrieval, reflection,
     │                 governance, agent, contradictions
     │
domain / models        memory schema, lifecycle state machine, permissions,
     │                 confidence, provenance
     │
infrastructure        SQLite database, Hindsight engine manager, config
```

### `api/` — thin by rule

A route validates input, resolves the actor, calls one service method, and
returns `.to_dict()`. Business rules do not live here. The one deliberate
exception is `_lifecycle()` in `api/memories.py`, which is a pure projection of
the state machine for the UI — it reads `LIFECYCLE_TRANSITIONS` rather than
re-declaring rules.

### `memory/` — the domain

| Module | Responsibility |
|---|---|
| `hindsight_client.py` | The `MemoryEngine` interface, `HindsightEngine`, `SimulatedHindsightEngine`, and `EngineManager` which chooses between them |
| `ingestion.py` | The capture pipeline: source -> gate -> retain -> record -> evidence -> audit |
| `retrieval.py` | Recall orchestration, permission filtering, Memory Lens assembly |
| `reflection.py` | Answer construction: sections, conflicts, outdated warnings, confidence |
| `confidence.py` | The six-factor internal confidence heuristic |
| `governance.py` | Review, promote, validate, restrict, expire + auditing |
| `contradiction.py` | Detection of scope drift and invalidation |
| `lifecycle.py` | `apply_transition` — the only legal way to change status |
| `provenance.py` | Source labels, reliability notes, provenance views |

### `models/` — the schema is the contract

`models/memory.py` defines `MemoryType`, `Visibility`, `AccessLevel`,
`Sensitivity`, `MemoryStatus`, `ConfidenceBand`, `MemoryGateDecision` and the
`LIFECYCLE_TRANSITIONS` table. `models/permissions.py` defines `Actor`,
`MemoryPolicy`, the policy table, and `MemoryResolver`.

---

## 4. The memory schema

Every memory is a `MemoryRecord` carrying governance metadata beside its content:

```
id, type, title, content, summary
source_type / source_id / source_name / captured_at / observed_at   ← provenance
scope, owner, team, domain, purpose
visibility (PERSONAL | TEAM | ORGANIZATION)
access_level, sensitivity
status (lifecycle), confidence, evidence_count
excluded_scopes            ← scope restriction
human_confirmed, promoted_by, version, tags
hindsight_fact_id          ← link into the memory bank
gate                       ← the Memory Gate decision that admitted it
```

Eleven memory types exist (`FACT`, `EXPERIENCE`, `LESSON`, `OBSERVATION`,
`DECISION`, `EXCEPTION`, `RELATIONSHIP`, `COMMITMENT`, `HYPOTHESIS`,
`CORRECTION`, `EVENT`). Type drives confidence weighting and display, and is
assigned by the source adapter, not by the route.

---

## 5. The Memory Gate

Runs **before** retention. Implemented in `ingestion.py` with the policy tables
from `models/permissions.py`.

Evaluates, per claim:

- **authorization** — is this actor allowed to have this recorded at all
- **purpose** — is there a stated operational reason
- **scope** — which component/environment it applies to
- **sensitivity** — `INTERNAL` / `CONFIDENTIAL`
- **retention** — a policy-derived expiry
- **secret heuristics** — `SECRET_PATTERNS` refuses obvious credentials
  (passwords, API keys, bearer tokens, PEM headers). This is a prototype
  heuristic, explicitly *not* a DLP product.

Verdict is `STORE` or `REJECT`, always with human-readable reasons, always
audited, and always attached to the memory as `gate`.

**Why before, not after.** If the gate ran after retention you would already have
written content you are not allowed to keep, and you would have to delete it from
a store you do not fully own. The gate running first means the engine can never
become an unauthorised archive.

---

## 6. Permissions and promotion

`MemoryResolver` is the single authority. Three ideas:

**Visibility ranking is explicit, not lexical.**
`PERSONAL < TEAM < ORGANIZATION` is encoded in `VISIBILITY_ORDER` and
`visibility_rank()`. Comparing enum *names* alphabetically would rank
`ORGANIZATION` below `PERSONAL` and silently invert every check.

**Organizational recall never returns personal memory.**
`can_reach(actor, memory)` is applied to every recall, list and detail response.
Withheld items are reported as *withheld with a reason* — never as content. The
UI shows the withheld panel on purpose, because silently omitting them would look
identical to "nothing exists".

**Promotion is an explicit human act.**
`may_promote_to` is role-scoped:

| Transition | Who may do it |
|---|---|
| `PERSONAL -> TEAM` | the owner only |
| `TEAM -> ORGANIZATION` | a Knowledge Steward only |
| anything else | refused with a reason |

A contractor (`outsider`) has `visibility_ceiling = PERSONAL` and therefore
cannot reach organizational memory at all, regardless of what the gate decided.

---

## 7. Knowledge evolution

### Lifecycle state machine

```
CREATED ──> CONFIRMED ──> ACTIVE ──> USED ──> SUPPORTED
   │            │           │         │
   │            │           └──> REVALIDATED / UPDATED / OBSERVED
   │            │           └──> CONTRADICTED / STALE
   │            └──> STALE / ARCHIVED
   └──> REJECTED / ARCHIVED
```

`LIFECYCLE_TRANSITIONS` in `models/memory.py` is the single declaration. An
illegal transition raises `InvalidTransition` and returns `409` with a message
naming the current state.

`apply_transition()` in `memory/lifecycle.py` is the only function permitted to
change a status. That guarantees every change produces a `memory_events` row and
an audit entry — history cannot be skipped.

**The UI is told what is legal.** `GET /api/memories/{id}` returns a `lifecycle`
block listing allowed transitions and, per action, whether it is currently
allowed and why. The Memory Center renders exactly that, so it never offers a
button that the server will reject.

### Contradiction instead of deletion

New evidence does not overwrite old knowledge. `contradiction.py` raises
`REVIEW_REQUIRED` when a memory's scope has drifted relative to the running
environment, or when an architecture change expresses invalidation
(`INVALIDATION_MARKERS`: "no longer", "must not automatically", "replaced", …).

A human then resolves it via one of four actions, all of which preserve the
original text:

| Action | Effect |
|---|---|
| `confirm` | procedure unchanged; -> `REVALIDATED` |
| `restrict` | scope narrowed via `excluded_scopes`; **lifecycle status deliberately unchanged** |
| `update` | new content, prior version preserved |
| `archive` | retired but retained |

`restrict` leaving the status unchanged is a deliberate design choice: narrowing
scope is not a statement about the *truth* of the memory, only about where it
applies. A separate action expresses judgement about truth.

---

## 8. Hindsight integration

```python
class MemoryEngine(ABC):
    async def retain(...)  async def recall(...)  async def reflect(...)
    async def probe()  async def health()  async def clear_local()
```

Two implementations, one contract:

- `HindsightEngine` — talks to a live server over HTTP.
- `SimulatedHindsightEngine` — local SQLite-backed engine with the same method
  signatures, the same result shapes, and `mode="simulated"` on everything.

`EngineManager` owns the choice:

1. `probe()` on startup and on demand.
2. On `MemoryEngineUnavailable`, count the failure; after
   `live_failure_threshold` consecutive failures, degrade to simulated and
   **record the reason**.
3. `force_simulated_engine` skips the live path entirely (used by tests).

**Why the simulator is not hidden.** A degraded engine that silently returns
plausible numbers is worse than no engine. Every simulated response carries
`engine_simulated: true`, `engine_mode: "simulated"`, a human-readable
`degraded_reason`, and the UI shows an amber banner. The health payload literally
reads `HINDSIGHT (SIMULATED)`.

### Bank configuration

The bank is seeded with a mission, directives and a disposition, and these are
sent to the engine so that *what counts as a useful memory* is engine-level
policy rather than a hard-coded string in a route.

---

## 9. Ask: the central interaction

```
question
   │
   ├─ MemoryResolver.assert_can_read / filter     ← permission boundary
   │
   ├─ Hindsight recall                            ← evidence
   │     └─ build Memory Lens entries (why_relevant, provenance, confidence)
   │
   ├─ Hindsight reflect                           ← synthesis, only when it is
   │     └─ structured sections                   a reasoning task
   │
   └─ response: headline, sections, conflicts,
                outdated warning, scope decision,
                memories used, lens, trace,
                confidence, withheld, warnings
```

Two deliberate constraints:

- **`recall` and `reflect` are not interchangeable.** `recall` is for evidence
  retrieval. `reflect` is reserved for synthesis. Calling `reflect` for a trivial
  lookup would be wasteful and would blur what each operation is for.
- **Inference is never presented as fact.** The section labels are
  `DOCUMENTED FACT`, `HISTORICAL EXPERIENCE`, `CURRENT EVIDENCE`, `INFERENCE`,
  `RECOMMENDATION` — the distinction is structural in the response, not a
  disclaimer paragraph.

The **Memory Lens** is the answer to "why did you say that?". Each entry carries
a generated `why_relevant` string, source type and label, reliability note,
environment-match flag, evidence list, contradiction list, relevance score and a
full confidence breakdown. It is assembled from real stored data.

### Suppression and disclosure

Recall returns a fact set larger than the answer uses. The Memory Gate suppresses
facts that fail visibility, and the response reports:

- `suppressed_fact_count` and the suppressed fact ids
- `withheld[]` — memories the permission boundary blocked, with the reason
- `warnings[]` — including the engine-mode warning

The count is shown rather than hidden, because a reader deciding whether to trust
an answer needs to know what was left out.

---

## 10. Confidence

`confidence.py` computes an **internal** score from six weighted factors, each
with a human-readable explanation:

| Factor | Weight | Source |
|---|---|---|
| `source_reliability` | 0.22 | per source type: outcome .92, architecture .95, incident .88, interview .78, handover .62, agent synthesis .45 |
| `supporting_observations` | 0.24 | linked incidents and outcomes |
| `human_confirmation` | 0.20 | was a human promoted it |
| `recency` | 0.10 | 240-day half-life decay |
| `scope_match` | 0.12 | does the scope match the running environment |
| `outcome_success` | 0.12 | lifecycle and outcome polarity |

Bands: `VERY_HIGH >= .78`, `HIGH >= .60`, `MEDIUM >= .40`, else `LOW`.
An open contradiction applies a penalty.

`CONFIDENCE_DISCLAIMER` is attached to every confidence payload and rendered next
to every number. It states plainly that this is a MemoryOS heuristic over a
synthetic scenario and not a statistical guarantee. The word "internal" is
deliberate: it is not a probability that the memory is true.

---

## 11. Outcome learning

Recording an outcome closes the loop:

```
decision  ->  outcome  ->  classification  ->  reinforcement or contradiction
```

`outcomes.py` performs negation-aware classification: *"checked queue depth, did
not restart, resolved"* is a **success**, and naive keyword matching gets this
backwards. The classifier returns an explicit verdict with the cues it used, so
the decision is inspectable.

When the memory matches the acted-upon recommendation, the outcome is linked as
evidence, confidence rises, and lifecycle moves to `USED`. When the outcome is a
failure, a contradiction is raised instead of reinforcing the wrong lesson.
Recommendation targeting uses content overlap so that only memories actually
about the acted-on recommendation are touched.

---

## 12. Frontend

React 18 + TypeScript + Vite + Tailwind. Router-based, one page per capability.

```
src/
├─ App.tsx             route table
├─ components/
│  ├─ Layout.tsx       nav, actor selector, engine banner
│  └─ ui.tsx           Panel, Chip, Bar, Empty, Spinner, ErrorNote
├─ lib/
│  ├─ api.ts           typed fetch client, ApiError
│  ├─ types.ts         response types mirroring the API
│  ├─ appState.tsx     shared actor / engine / environment
│  └─ format.ts        percent, tone, time formatters
└─ pages/              9 pages
```

Decisions:

- **Types mirror the real response, not an assumed one.** An early version of
  `Ask.tsx` was written against an invented shape and crashed on submit. The fix
  was to dump the actual response and model it exactly. `types.ts` is expected to
  track the API.
- **`api.ts` never swallows a server explanation.** It extracts `detail` whether
  it is a string, a validation array, or the `{message, reason}` object used by
  `403`, so the UI can tell the user *why* an action was refused.
- **Actor selection persists.** `appState` tracks whether the user has chosen an
  actor; refreshing shell data no longer resets it to the default.
- **Degraded engine is always visible** in the layout, not just on one page.
- **Per-response synthetic labelling.** Every metric renders
  `Synthetic prototype metric`; confidence renders its disclaimer.

---

## 13. API shape

All routes are under `/api` (46 endpoints). Consistent error contract:

| Code | Meaning |
|---|---|
| `400` | `ValueError` — invalid input, with `error: "invalid_input"` |
| `403` | `PermissionDenied` — global handler, `error: "permission_denied"` |
| `404` | unknown memory / contradiction |
| `409` | `InvalidTransition` — illegal lifecycle move |
| `422` | request validation |

Demo action endpoints return a uniform envelope `{ok, message, payload}` so the
UI can treat every control identically. Run endpoints return
`{id, mode, status, started_at, finished_at, duration_ms, steps[], progress_percent}`
with per-step `status: "ok" | "error"`.

---

## 14. Testing strategy

- **In-process `TestClient`** against the real app object graph, so tests exercise
  routing, serialization, permissions and the lifecycle together rather than
  mocking them away.
- **Engine forced to simulated** in tests, so results are deterministic.
- **Contract tests for the demo surface** — every individual control endpoint is
  asserted, not just the full run. This is what caught the
  `/api/demo/outcome` envelope bug that the full run had masked.
- **Negative tests matter most**: privacy leakage, unauthorized promotion,
  illegal transitions, gate rejection, negation handling, confidentiality.
- **Frontend**: strict `tsc`, production build, plus an interaction pass that
  drives every page in a real browser and fails on console or page errors.

---

## 15. Extensibility

The demo is deliberately narrow (one company, one incident class) but the seams
are real:

- **New source type** — add a `sources/` adapter emitting `SourceDocument` +
  `ExtractedClaim`; the gate, retention, confidence and lens are unchanged.
- **New memory type** — add to `MemoryType` and give it a `SOURCE_RELIABILITY`
  or confidence treatment.
- **New domain** — `MemoryRecord.domain` and `scope` are free-form; the
  contradiction detector is scope-family based, not payments-specific.
- **Live Hindsight** — no code change, only configuration.
- **Real LLM** — `llm_provider` exists for optional answer polishing; the
  evidence, confidence and trace are produced independently of it.

---

## 16. What is deliberately absent

- **No authentication.** The actor selector demonstrates the resolver; it is not
  an identity system. Shipping this without real auth would be a security
  failure, and the README says so.
- **No multi-tenancy.** One bank, one company.
- **No vector store of our own.** That is the point: Hindsight is the engine.
- **No document ingestion / RAG pipeline.** The product captures *experience*,
  not documents.
- **No automatic promotion, ever.** The single most important rule in the system
  is that machine systems do not decide what becomes organizational knowledge.
