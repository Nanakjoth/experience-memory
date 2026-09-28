# MEMORYOS — Runtime Flows

What actually happens, in order, at runtime. Companion to
[`arch.md`](arch.md) (structure) and [`README.md`](README.md) (what and how to run).

All examples use the seeded NovaTech scenario:
company `NovaTech`, bank `memoryos-novatech`, running component
`Payment Queue v2`, default actor `maya`.

---

## 0. System diagrams

### 0.1 Component view

```
┌────────────────────────────────────────────────────────────────────┐
│  Browser  http://localhost:5173                                    │
│  React + TypeScript + Tailwind  (9 pages)                          │
└───────────────────────────┬────────────────────────────────────────┘
                            │  fetch /api/*   (Vite dev proxy)
┌───────────────────────────▼────────────────────────────────────────┐
│  FastAPI  http://127.0.0.1:8000                                   │
│                                                                    │
│  api/  ──►  services  ──►  memory/*  ──►  models/*                │
│             (ingestion,     (engine, gate,                          │
│              retrieval,       retrieval,                           │
│              reflection,      confidence,                           │
│              governance,      governance,                          │
│              agent,           contradiction,                        │
│              contradictions)  lifecycle)                           │
│                    │                                    │          │
│                    ▼                                    ▼          │
│              db/database.py                  memory/hindsight_client │
│              SQLite: app metadata            EngineManager         │
│                                             ├─ HindsightEngine      │
│                                             └─ Simulated… (fallback)│
└────────────────────────────────────────────────────────────────────┘
```

### 0.2 Sequence — the core ask

```
Maya   Frontend   API   Resolver   Retrieval   Hindsight   Reflection   DB
 │         │       │       │          │            │           │         │
 │ ask()  │       │       │          │            │           │         │
 │────────▶│──────▶│       │          │            │           │         │
 │         │       │──────▶│ can_reach│            │           │         │
 │         │       │◀──────│ filter   │            │           │         │
 │         │       │──────▶│─────────▶│            │           │         │
 │         │       │       │          │─recall()──▶│           │         │
 │         │       │       │          │◀──facts────│           │         │
 │         │       │       │          │ gate-suppress             │         │
 │         │       │       │          │ build lens entries        │         │
 │         │       │       │          │──────────▶ reflect() ────▶│         │
 │         │       │       │          │◀─────sections───────────│         │
 │         │       │       │          │            │      confidence     │
 │         │       │◀───────────────────────────────┴──────────────────▶│
 │◀────────│       │ answer + lens + trace + confidence + withheld      │
```

---

## 1. Startup

```
uvicorn backend.main:app
   │
   ├─ create_app()
   │    ├─ Settings from env / .env
   │    ├─ CORS middleware (localhost:5173)
   │    └─ include_router x8 under /api
   │
   └─ lifespan startup
        ├─ settings.ensure_directories()      create backend/data/
        ├─ get_services()                    build one object graph
        │    Database, EngineManager, MemoryResolver, ConfidenceEngine,
        │    MemoryIngestionService, RetrievalService, GovernanceService,
        │    SuccessorAgent, ContradictionDetector
        ├─ await services.engine.probe()
        │    ├─ Hindsight reachable?  -> mode "live"
        │    └─ not reachable         -> mode "simulated"
        │         degraded_reason = "Cannot connect to host localhost:8888 …"
        └─ log warning if simulated
```

**Observed on this machine** (Docker not running):

```
INFO memoryos: MemoryOS starting. Memory engine: HINDSIGHT (SIMULATED) (simulated)
WARNING memoryos: Hindsight is unreachable at http://localhost:8888.
        Running the SIMULATED engine. See README -> Hindsight setup.
```

`GET /api/engine` then reports:

```json
{
  "health": { "mode": "simulated", "label": "HINDSIGHT (SIMULATED)",
              "simulated": true, "bank_id": "memoryos-novatech" },
  "status": { "memory_engine": "hindsight", "simulated": true,
              "degraded_reason": "Cannot connect to host localhost:8888 ssl:default [The remote computer refused the network connection]" }
}
```

---

## 2. Flow — Capture experience

`POST /api/capture` — the entry point for everything new.

```
request { expert, scope, system, turns: [{prompt, answer}] }
   │
   ├─ Source adapter: sources/expert_interview.py
   │    SourceDocument  +  [ExtractedClaim…]
   │    claims typed: EXPERIENCE, LESSON, EXCEPTION, RELATIONSHIP, FACT
   │
   ├─ FOR EACH claim -> Memory Gate
   │    ├─ authorization:   may this actor have this recorded
   │    ├─ purpose:         is there an operational reason
   │    ├─ scope:           which component it applies to
   │    ├─ sensitivity:     INTERNAL / CONFIDENTIAL
   │    ├─ retention:       policy-derived expiry
   │    └─ secret scan:     SECRET_PATTERNS -> refuse credentials
   │         │
   │         ├─ REJECT -> record reason, DO NOT retain  ◀── nothing reaches the engine
   │         └─ STORE  -> continue
   │
   ├─ engine.retain(claim)              ◀── only approved claims get here
   │     -> hindsight_fact_id
   │
   ├─ DB: MemoryRecord                 governance metadata + gate decision
   ├─ DB: MemoryEvent                  lifecycle entry
   ├─ DB: AuditEvent                   memory_captured + hindsight_retain
   ├─ DB: LearningEvent                what the organization learned
   └─ response { retained, memories[], rejected[], hindsight_fact_ids[], duration_ms }
```

**Key property.** The gate is *before* `retain()`. Rejected text is never written
anywhere. This is what makes "the Memory Gate runs first" a structural claim
rather than a slogan.

**Initial visibility is `PERSONAL`.** A captured lesson is not organizational
knowledge yet. It must be promoted explicitly (flow 6).

---

## 3. Flow — Ask (the central interaction)

`POST /api/ask { question, actor }`

```
├─ 1. Question
│     default: "Payment API is showing connection reset alerts. What should I do?"
│
├─ 2. Recall  (evidence)
│     engine.recall(question)
│       -> EngineRecallResult{ facts[], latency_ms, strategy_counts, … }
│       simulated: hybrid semantic + keyword scoring over stored memories
│
├─ 3. Permission filter
│     MemoryResolver.can_reach(actor, memory) for every candidate
│     -> readable[]  +  withheld[] (id, title, visibility, reason)
│
├─ 4. Build Memory Lens entries
│     per memory: why_relevant (generated from real overlap + evidence counts),
│                 provenance, reliability note, environment_match,
│                 evidence[], contradictions[], relevance_score, confidence
│
├─ 5. Memory Gate — fact suppression
│     facts failing visibility are suppressed, not silently dropped
│     -> suppressed_fact_ids[], suppressed_fact_count
│
├─ 6. Reflect  (synthesis — only for genuine reasoning tasks)
│     engine.reflect(question, context)
│     -> sections in fixed order:
│          DOCUMENTED FACT
│          HISTORICAL EXPERIENCE
│          CURRENT EVIDENCE
│          INFERENCE
│          RECOMMENDATION
│
├─ 7. Scope decision
│     current_environment vs each memory's scope
│     -> in_scope[] / out_of_scope[], outdated_warning
│
├─ 8. Confidence
│     six weighted factors + contradiction penalty
│     + CONFIDENCE_DISCLAIMER attached
│
└─ 9. response
      question, asked_by, at,
      answer{headline, sections[], conflicts[], outdated_warning,
             reflect_text, confidence, scope, trace, call_count},
      lens[], memories_used[], hindsight_facts[],
      withheld[], suppressed counts, trace{steps[], recall{}, reflect[]},
      confidence, warnings[], privacy_notice, duration_ms,
      engine_mode, engine_simulated, request_id
```

### Real trace from a full demo run

```
Question              Payment API is showing connection reset alerts. What should I do?
Recall                simulated / budget=mid
Memories found        20
Permission filter     12 readable, 4 withheld
Relevant evidence     18 linked evidence items
Fact visibility       10 shown, 10 suppressed by the Memory Gate
```

The trace is generated, not narrated. `Permission filter: 12 readable, 4 withheld`
means four memories really were blocked for this actor.

### What the answer looked like

Headline:

> **Do NOT reuse the historical procedure — it may be outdated.**

with an out-of-scope warning (`9 active memories are scoped to a previous
environment`), the recommendation section naming each open contradiction, and the
inference explicitly labelled `INFERENCE` rather than presented as fact.

---

## 4. Flow — Outcome learning

`POST /api/outcome`

```
{ question, recommendation, actual_action, result, notes, queue_depth, scope }
   │
   ├─ classify_outcome()
   │    negation-aware cue matching over `result` and `notes`
   │    "checked depth, did NOT restart, resolved"  -> SUCCESS
   │    (naive keyword matching gets this exactly backwards)
   │    -> verdict{ successful, source, rationale, cues[] }
   │
   ├─ target selection
   │    content-overlap between the recommendation and each memory
   │    only memories actually about the acted-on recommendation
   │
   ├─ SUCCESS
   │    ├─ link outcome as evidence (polarity "supports")
   │    ├─ confidence_before / confidence_after / confidence_delta
   │    ├─ lifecycle -> USED  (or SUPPORTED)
   │    ├─ audit: outcome_recorded + memory_used_by_agent
   │    └─ metric: memories_used
   │
   ├─ FAILURE
   │    ├─ evidence polarity "contradicts"
   │    ├─ raise Contradiction  (REVIEW_REQUIRED)
   │    ├─ do NOT reinforce
   │    └─ audit: memory_contradicted
   │
   └─ UNKNOWN  (not classifiable)
        ├─ no reinforcement, no contradiction
        └─ verdict explains why it could not classify
```

**Design note.** `successful` may be supplied explicitly by the caller to bypass
inference. When inference is used, the verdict carries the cues it matched so a
human can check the classification.

---

## 5. Flow — Architecture change and contradiction

`POST /api/architecture-change`

```
{ id, title, system, component, summary, invalidates_scope, effective_at }
   │
   ├─ DB: architecture_changes row
   ├─ DB: AuditEvent architecture_change
   ├─ for each memory with scope == invalidates_scope:
   │    ├─ expresses_invalidation(summary)?   (INVALIDATION_MARKERS)
   │    ├─ component_family(scope) matches?   "Payment Queue v1" -> "payment queue"
   │    └─ raise Contradiction
   │         status REVIEW_REQUIRED
   │         reason explains the drift and cites the running component
   ├─ for each actor -> re-ask
   │    lifecycle -> CONTRADICTED where applicable
   ├─ AuditEvent memory_contradicted
   ├─ LearningEvent  environment changed
   └─ response { contradiction_count, contradictions[], learning_event }
```

Detection is scope-family based, not hard-coded to Payments, so a new domain
works by supplying its own scopes.

---

## 6. Flow — Explicit promotion

`POST /api/memories/{id}/promote { actor, target }`

```
├─ MemoryResolver.can_promote(actor, memory, target)
│     PERSONAL -> TEAM        owner only
│     TEAM -> ORGANIZATION    Knowledge Steward only
│     already at target        refused
│     contractor ceiling      refused
│
├─ REFUSED -> 403 { detail: { message, reason: "promotion_not_allowed" } }
│            UI shows the reason, e.g.
│            "Only a Knowledge Steward may promote memory to ORGANIZATION."
│
└─ ALLOWED
      ├─ visibility   = target
      ├─ access_level = policy.default_access_level
      ├─ sensitivity  = policy.default_sensitivity
      ├─ expiry_at    = policy retention
      ├─ promoted_by  = actor.id
      ├─ apply_transition -> ACTIVE
      ├─ human_confirmed = true
      ├─ AuditEvent memory_promoted
      └─ metric memories_promoted
```

Rejected example, verbatim from a live run:

```
403 {"detail": {"message": "Only a Knowledge Steward may promote memory to ORGANIZATION.",
                 "reason": "promotion_not_allowed"}}
```

---

## 7. Flow — Human review and lifecycle actions

```
POST /api/memories/{id}/review     -> CONFIRMED
POST /api/memories/{id}/reject     -> REJECTED      (original text preserved)
POST /api/memories/{id}/validate   -> REVALIDATED
POST /api/memories/{id}/restrict   -> scope narrowed, status UNCHANGED
POST /api/memories/{id}/expire     -> STALE         (preserved, not deleted)
```

Every one of these goes through `apply_transition`, so each produces a
`memory_events` row plus an audit entry. There is no code path that changes status
without history.

**Illegal transition** returns `409` with a state-naming message:

```
409 {"detail": "Cannot move memory from CREATED to REVALIDATED."}
```

To stop the UI from offering impossible actions, the detail endpoint publishes
the legal set:

```json
"lifecycle": {
  "status": "CREATED",
  "allowed_transitions": ["ACTIVE", "ARCHIVED", "CONFIRMED", "REJECTED"],
  "actions": [
    { "action": "review",  "target": "CONFIRMED",   "allowed": true,  "reason": "CREATED → CONFIRMED is a legal transition." },
    { "action": "validate","target": "REVALIDATED", "allowed": false,
      "reason": "CREATED → REVALIDATED is not a legal transition. Allowed from CREATED: ACTIVE, ARCHIVED, CONFIRMED, REJECTED" },
    { "action": "restrict","target": null,          "allowed": true,  "reason": "Narrows the applicable scope. History is kept." }
  ]
}
```

The Memory Center renders exactly these, so a click never produces a `409`.

---

## 8. Flow — Contradiction resolution

`POST /api/contradictions/{id}/resolve { actor, action, note }`

```
open contradiction (REVIEW_REQUIRED)
   │
   ├─ confirm   -> memory REVALIDATED, contradiction RESOLVED/CONFIRMED
   ├─ restrict  -> excluded_scopes += current_environment
   │               contradiction RESOLVED/RESTRICTED
   │               lifecycle status deliberately UNCHANGED
   ├─ update    -> new content, previous_versions keeps the old one
   └─ archive   -> memory ARCHIVED, still queryable in history
   │
   ├─ DB: contradictions row updated (resolution, resolved_by, resolved_at)
   ├─ DB: AuditEvent
   ├─ LearningEvent
   └─ response { contradiction, memory, action, detail }
```

**`restrict` in detail** — the most interesting resolution:

```
before: scope "Payment Queue v1", status USED, visibility ORGANIZATION
after:  excluded_scopes ["Payment Queue v2"], status USED  (unchanged)
        contradiction RESOLVED
```

The lesson stays queryable as historical knowledge and is no longer applied to
Queue v2. Because the status is untouched, the answer engine keeps surfacing the
contradiction context rather than treating the lesson as disproven. This was a
deliberate change: narrowing applicability is not a claim about truth.

---

## 9. Flow — The 13-step demo

`POST /api/demo/run` — the whole story, executable.

| # | Key | What happens | What you should observe |
|---|---|---|---|
| 1 | `reset` | clean slate | counters drop to zero |
| 2 | `seed_incidents` | 13 incidents retained | memories grow; incident memories linked as evidence |
| 3 | `capture_arun` | Arun's lesson captured | created `PERSONAL`, gate `STORE`, not yet organizational |
| 4 | `ask_without_memory` | Maya asks first | **generic** answer, no lesson cited |
| 5 | `show_baseline` | baseline recommendation | the "before" snapshot |
| 6 | `promote_lesson` | steward promotes to `ORGANIZATION` | `promoted_by` set, status `ACTIVE` |
| 7 | `ask_with_memory` | Maya asks again | **evidence-backed** answer, memory cited, lens populated |
| 8 | `record_outcome` | outcome recorded | confidence up, status `USED`, `memories_used` metric +1 |
| 9 | `queue_v2` | architecture change | contradictions raised, environment becomes `Payment Queue v2` |
| 10 | `ask_after_change` | Maya asks again | **refuses to apply blindly**, reports the contradiction |
| 11 | `detect_stale` | contradiction detection | `REVIEW_REQUIRED` items listed |
| 12 | `update_scope` | restrict scope | `excluded_scopes` set, status unchanged, history kept |
| 13 | `final_dashboard` | final state | continuity, risk, learning counters |

Response:

```json
{ "id": "demo-…", "mode": "simulated", "status": "ok",
  "steps": [ { "index": 1, "key": "reset", "status": "ok", "ms": … }, … ],
  "progress_percent": 100, "duration_ms": 7911 }
```

Each step is also individually callable (`POST /api/demo/{key}`) returning
`{ok, message, payload}`. The test suite asserts **all eleven** control endpoints
individually, not just the full run — the full run had been masking a
`/api/demo/outcome` envelope bug that only appeared when the control was pressed
on its own.

### Before / after

`GET /api/demo/before-after` — the same question answered from the generic
baseline versus the evidence-backed answer, side by side. This is the single
clearest demonstration of the product's value.

---

## 10. Flow — Privacy demonstration

Switch the header actor to `outsider`, or call any endpoint with `actor=outsider`.

```
actor = external-contractor, visibility_ceiling = PERSONAL
   │
   ├─ GET /api/memories            -> only own PERSONAL memory
   │                                 withheld[] names what was blocked and why
   ├─ POST /api/ask                -> "No organizational memory was used."
   │                                 withheld[] lists the blocked ids + reasons
   ├─ POST promote                 -> 403, contractor has no organizational standing
   └─ response always includes privacy_notice{ withheld_count, items[] }
```

Verified behaviour: the withheld panel appears on both Memory Center and Ask,
and the count is reported rather than hidden.

**Rule.** A `PERSONAL` memory is never returned by an organizational question,
no matter how semantically similar it is. Withheld items are disclosed as
*withheld with a reason*, never as content.

---

## 11. Flow — Audit and metrics

```
every governed action -> audit_events
  memory_captured, memory_reviewed, memory_promoted, memory_retrieved,
  memory_used_by_agent, memory_contradicted, memory_updated, memory_restricted,
  memory_expired, memory_revalidated, memory_archived, memory_rejected,
  outcome_recorded, architecture_change, memory_recalled,
  hindsight_retain, hindsight_recall, hindsight_reflect,
  permission_denied, environment_change, demo_step
```

`GET /api/audit` returns events, total count, the list of event types and a
label map for the UI.

Metrics are **real counters incremented by real application events**, not static
numbers:

```json
{ "memories_created": 17, "memories_retrieved": 27, "memories_used": 27,
  "memories_updated": 6, "outcomes_recorded": 1,
  "memories_revalidated": 3, "contradictions_detected": 14 }
```

`GET /api/demo/learning-curve` visualises these. Every such figure is rendered
with the label `Synthetic prototype metric`, because the underlying scenario is
synthetic even though the counting is real.

---

## 12. Flow — Frontend request lifecycle

```
user action
   │
   ├─ page calls api.get/api.post (lib/api.ts)
   │     ├─ fetch with JSON headers
   │     ├─ non-2xx -> extract detail
   │     │     string            -> use it
   │     │     array             -> join validation msgs
   │     │     {message, reason} -> use .message      ◀── 403 case
   │     └─ throw ApiError{ status, message, payload }
   │
   ├─ page state: setBusy / setError / setData
   ├─ ErrorNote renders the extracted message
   │
   └─ after mutations: refreshShell()
         re-fetch /api/actors + /api/engine
         environment and capabilities stay current
         selected actor is preserved, not reset
```

Vite proxies `/api` → `http://127.0.0.1:8000`, so the browser makes same-origin
requests in development and CORS never bites.

---

## 13. Error paths

| Situation | Code | Payload | UI |
|---|---|---|---|
| Illegal lifecycle move | `409` | `"Cannot move memory from X to Y."` | `ErrorNote` in the Actions block |
| Unauthorized promotion | `403` | `{"message": …, "reason": "promotion_not_allowed"}` | extracted `.message` |
| Reading a forbidden memory | `403` | `error: "permission_denied"` | withheld panel |
| Bad input | `400` | `{"detail": …, "error": "invalid_input"}` | `ErrorNote` |
| Unknown memory | `404` | `"Memory X not found."` | `ErrorNote` |
| Engine unreachable | `200` | `engine_simulated: true` + warning | amber banner + warning list |
| Backend down | — | network error | shell stays usable, error shown |

The engine being degraded is deliberately **not** an error status. The system
keeps working; it just refuses to pretend the output is real.

---

## 14. Verification flows

```powershell
# Backend suite — API, permissions, lifecycle, demo surface
.\.venv\Scripts\python.exe -m pytest backend/tests -q
# -> 37 passed

# Frontend contract + build
npx tsc -b --noEmit
npm run build
# -> clean

# Engine status
Invoke-RestMethod http://127.0.0.1:8000/api/engine

# Every demo control, individually
POST /api/demo/reset, seed, seed-incidents, capture, promote, ask,
     outcome, queue-v2, evolution, privacy, resolve-contradictions
# -> 200 + { ok: true }

# The full story
POST /api/demo/run
# -> status "ok", 13 steps, progress_percent 100
```

The backend suite is what caught the `duration_ms` field being silently dropped
by the response model — invisible to the API consumer, visible in the UI, and now
covered by an assertion.
