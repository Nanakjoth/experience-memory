# MemoryOS — Runtime Flowcharts

What actually happens, step by step, at runtime. Companion to
[`ARCHITECTURE.md`](ARCHITECTURE.md) (structure) and
[`RUNNING.md`](RUNNING.md) (commands).

Every timing and step name below was captured from a real `POST /api/demo/run`
against the running application, not written from the source.

> Seeded scenario used throughout: company `NovaTech`, bank `memoryos-novatech`,
> running component `Payment Queue v1`, default actor `maya` (New DevOps
> Engineer).

---

## 1. The 13-step demo at a glance

One call — `POST /api/demo/run` — executes the whole product story. Verified
run: **status `ok`, 100%, 8,210 ms total**, all 13 steps `ok`.

```mermaid
flowchart TD
    S1["1 · reset<br/>800ms"] --> S2
    S2["2 · seed_incidents<br/>1300ms<br/>4 incidents → 5 memories"] --> S3
    S3["3 · capture_arun<br/>1899ms<br/>interview → 6 PERSONAL memories"] --> S4
    S4["4 · ask_without_memory<br/>445ms<br/>generic answer, no lesson"] --> S5
    S5["5 · show_baseline<br/>0ms<br/>runbook-only answer"] --> S6
    S6["6 · promote_lesson<br/>820ms<br/>LESSON → ORGANIZATION"] --> S7
    S7["7 · ask_with_memory<br/>422ms<br/>evidence-backed, 0.78 VERY_HIGH"] --> S8
    S8["8 · record_outcome<br/>653ms<br/>observation reinforces"] --> S9
    S9["9 · queue_v2<br/>1423ms<br/>architecture change lands"] --> S10
    S10["10 · ask_after_change<br/>433ms<br/>refuses stale reuse"] --> S11
    S11["11 · detect_stale<br/>4ms<br/>contradiction raised"] --> S12
    S12["12 · update_scope<br/>227ms<br/>v1 keeps lesson, v2 needs validation"] --> S13
    S13["13 · final_dashboard<br/>13ms<br/>real event counts"]

    style S4 fill:#78350f,color:#fff
    style S5 fill:#78350f,color:#fff
    style S7 fill:#065f46,color:#fff
    style S10 fill:#065f46,color:#fff

    classDef act fill:#0e7490,color:#fff
    class S1,S2,S3,S6,S8,S9,S12 act
```

Steps 4–5 are deliberately the *weak* answer. Without them, step 7 has nothing
to be an improvement against.

---

## 2. Startup

```mermaid
flowchart TD
    A["uvicorn imports backend.main"] --> B["create_app()"]
    B --> C["get_settings()<br/>reads .env, applies defaults"]
    C --> D["Register 8 routers + 2 meta routes"]
    D --> E["lifespan startup"]
    E --> F["settings.ensure_directories()"]
    F --> G["get_services()<br/>builds the object graph, cached"]
    G --> H["engine.probe()"]
    H --> I{"Hindsight<br/>reachable?"}
    I -->|"yes"| J["mode = live"]
    I -->|"no"| K["mode = simulated<br/>WARNING logged with the reason"]
    J --> L["app.state.engine_health set"]
    K --> L
    L --> M["Serving on :8000"]

    style K fill:#78350f,color:#fff
    style J fill:#065f46,color:#fff
```

Degradation is the expected path, not an error path. Probe it any time:

```bash
curl -s http://127.0.0.1:8001/api/engine
```

---

## 3. Flow — Capture experience

`POST /api/capture` · the expert interview ingestion path.

```mermaid
flowchart TD
    IN["Expert interview transcript<br/>10 scripted prompts"] --> SEG["Segment by prompt id<br/>TRANSCRIPT_TO_PROMPT"]
    SEG --> CLASS["Classify each answer (ordered if/elif)<br/>EXCEPTION · RELATIONSHIP<br/>LESSON · EXPERIENCE · FACT"]
    CLASS --> CAND["Build candidate memories<br/>+ provisional evidence links"]
    CAND --> GATE{"Memory Gate<br/>per candidate"}
    GATE -->|"secret"| REJ["Rejected — reason returned to UI"]
    GATE -->|"personal data"| PER["Store as PERSONAL"]
    GATE -->|"future-useful"| STORE["Store + compute confidence"]
    PER --> STORE
    STORE --> RES{"Retain to engine?"}
    RES -->|yes| ENG["engine.retain()<br/>bank memoryos-novatech"]
    RES -->|no| SKIP["App DB only"]
    ENG --> EVT["Append lifecycle event<br/>CREATED → CONFIRMED"]
    EVT --> RESP["Return memories +<br/>gate rejections +<br/>hindsight_fact_ids as proof"]

    style GATE fill:#7f1d1d,color:#fff
    style PER fill:#1e40af,color:#fff
    style REJ fill:#7f1d1d,color:#fff
```

**Verified behaviour** (demo step 3): one interview produces six memories —
`EXPERIENCE`, `LESSON`, `EXCEPTION`, `RELATIONSHIP` and `FACT` types — **all at
`visibility: PERSONAL`, `status: CREATED`**. They stay personal because the
system does not promote knowledge on its own.

---

## 4. Flow — Ask (the central interaction)

`POST /api/ask` · `SuccessorAgent.ask()`.

```mermaid
flowchart TD
    Q["question + actor"] --> DEF{"Empty?"}
    DEF -->|yes| D1["Use DEFAULT_QUESTION"]
    DEF -->|no| SC["current_scope from environment<br/>'Payment Queue v1'"]
    D1 --> SC
    SC --> PERM["MemoryResolver<br/>what can this actor reach?"]
    PERM --> REC["engine.recall(question)<br/>candidate facts"]
    REC --> SUP{"Gate suppression<br/>facts whose owning memory<br/>is now unreachable"}
    SUP -->|"dropped, ids recorded"| SCORE
    SUP -->|"survives"| SCORE["Score + rank"]
    SCORE --> LENS["Build Memory Lens<br/>per memory: provenance,<br/>evidence, confidence,<br/>environment match, why relevant"]
    LENS --> TRIG{"needs_reflection?"}
    TRIG -->|"no — lookup"| ASM["Assemble from facts"]
    TRIG -->|"yes — reasoning"| REF["engine.reflect()<br/>synthesis over experience"]
    REF --> SPLIT["Split into labelled sections:<br/>DOCUMENTED FACT · HISTORICAL EXPERIENCE<br/>CURRENT EVIDENCE · INFERENCE · RECOMMENDATION"]
    SPLIT --> ASM
    ASM --> MARK["Mark cited memories USED<br/>(strict=False)"]
    MARK --> AUD["Audit event<br/>+ learning event"]
    AUD --> OUT["Response payload"]

    style SUP fill:#7f1d1d,color:#fff
    style SPLIT fill:#155e75,color:#fff
    style OUT fill:#065f46,color:#fff
```

### `needs_reflection` — when synthesis is skipped

15 triggers (`backend/memory/reflection.py:34`), plus a 12-character minimum.
Verified:

| Question | Reflects? | Why |
|---|---|---|
| `Payment API is showing connection reset alerts. What should I do?` | **yes** | `what should i` |
| `Tell me about the outage` | **yes** | `tell me` |
| `Explain the queue` | **yes** | `explain` |
| `Who owns payments?` | no | no trigger |
| `What is the retry limit?` | no | no trigger |
| `what is 2+2` | no | under 12 chars |

### What the answer looks like — before vs. after promotion

**Step 4 (before the lesson exists)** — generic, no organizational evidence:

> reflect_mode `simulated` · 5 memories · 10 facts, 0 suppressed · confidence
> **0.788 / VERY_HIGH** · `outdated: true`

**Step 7 (after promotion)** — the headline inverts the runbook:

> *"Follow the recorded organizational experience before the documented
> runbook."*
>
> `DOCUMENTED FACT` — Payment API depends on Payment Queue v1; connection-reset
> alerts are frequently caused by the queue rather than the API process.
> `HISTORICAL EXPERIENCE` — INC-1042, INC-1088 … each with the action taken and
> its measured result.

**Step 10 (after the architecture change)** — refuses to reuse stale knowledge:

> *"Do NOT reuse the historical procedure — it may be outdated."*

That refusal is the entire thesis of the product, and it is produced by the
scope check rather than by a prompt instruction.

---

## 5. Flow — Explicit promotion

`POST /api/memories/{id}/promote` · nothing is promoted automatically.

```mermaid
flowchart LR
    A["Memory at PERSONAL"] -->|"human action only"| B{"Actor allowed to<br/>promote to this level?"}
    B -->|no| DENY["403 permission_denied"]
    B -->|yes| C["Validate transition<br/>InvalidTransition if illegal"]
    C --> D["Set visibility + confirm"]
    D --> E["Append lifecycle event<br/>actor, note, timestamp"]
    E --> F["Re-check related memories<br/>for promotion candidates"]
    F --> G["Recompute confidence"]
    G --> H["Audit event"]

    style DENY fill:#7f1d1d,color:#fff
    style H fill:#065f46,color:#fff
```

Verified (step 6): `LESSON` *"Check queue depth before restarting the Payment
API"* moves `PERSONAL → ORGANIZATION`, lands on `status: ACTIVE`, confidence
**0.7545**, and keeps its 3 evidence links.

---

## 6. Flow — Outcome learning

`POST /api/outcome` · a real observation strengthens or weakens memory.

```mermaid
flowchart TD
    O["Outcome recorded<br/>what was done · result"] --> F{"Does the outcome<br/>agree with the memory?"}
    F -->|"yes"| SUP["SUPPORTED<br/>confidence increases"]
    F -->|"no"| CON["CONTRADICTED<br/>confidence decreases<br/>+ contradiction raised"]
    F -->|"neutral"| OBS["OBSERVED<br/>recorded, no change"]
    SUP --> EV["Evidence link appended"]
    CON --> EV
    OBS --> EV
    EV --> RET["retain to engine<br/>so future recall sees it"]
    RET --> AUD["Audit + learning event"]

    style CON fill:#7f1d1d,color:#fff
    style SUP fill:#065f46,color:#fff
```

---

## 7. Flow — Architecture change → contradiction → resolution

This is the resilience path. Change invalidates knowledge; the system surfaces
that instead of silently applying stale advice.

```mermaid
flowchart TD
    A["Architecture change recorded<br/>'Payment Queue v2 deployed,<br/>replacing Payment Queue v1'"] --> B["Change stored as EVENT memory<br/>scope = Payment Queue v2"]
    B --> C{"Does it invalidate a<br/>memory scoped to v1?"}
    C -->|no| Z["No effect"]
    C -->|"yes"| D["Contradiction raised<br/>status = REVIEW_REQUIRED"]
    D --> E["Affected memory NOT auto-resolved"]
    E --> F["Next ask re-checks scope"]
    F --> G{"Asked scope matches<br/>memory scope?"}
    G -->|"yes — v1"| H["Lesson still applies"]
    G -->|"no — v2"| I["Refuse + flag<br/>'may be outdated'"]
    H --> J["Human restricts scope<br/>POST /memories/id/restrict"]
    I --> J
    J --> K["Memory → RESTRICTED / STALE<br/>v2 requires revalidation"]
    K --> L["Resolution recorded:<br/>actor · action · note · timestamp"]

    style D fill:#78350f,color:#fff
    style E fill:#78350f,color:#fff
    style I fill:#7f1d1d,color:#fff
    style L fill:#065f46,color:#fff
```

Governance drives resolution from the server, not the client
(`GET /api/governance/summary` returns `resolution_actions`; the UI renders
exactly those buttons).

---

## 8. Flow — Privacy boundary

The demo's central claim: **personal memory is never returned through an
organizational question.**

```mermaid
flowchart TD
    Q["Organizational question"] --> R["MemoryResolver<br/>per-actor reachability"]
    R --> F["Filter memories"]
    F --> E["engine.recall() returns<br/>facts for ALL memories"]
    E --> S{"Gate suppression:<br/>fact's owning memory<br/>not reachable?"}
    S -->|"yes"| SUP["Suppress fact<br/>record suppressed_fact_ids"]
    S -->|"no"| KEEP["Keep"]
    SUP --> R2["Response"]
    KEEP --> R2
    R2 --> UI["UI shows TWO things:<br/>the memories used<br/>AND what was withheld + why"]

    style S fill:#7f1d1d,color:#fff
    style SUP fill:#7f1d1d,color:#fff
    style UI fill:#065f46,color:#fff
```

Two independent checks — resolver filters before recall, suppression filters
after. If either were removed the boundary could still leak.

The `withheld` array is returned rather than hidden, and
`successor_agent.py:141` emits an explicit warning. A privacy boundary you
cannot audit is not a boundary.

Verified actors and their visibility ceilings:

| Actor | Role | Ceiling |
|---|---|---|
| `arun` | Senior DevOps Engineer | ORGANIZATION |
| `maya` | New DevOps Engineer | ORGANIZATION |
| `priya` | Staff Identity Engineer | ORGANIZATION |
| `ravi` | Network Reliability Engineer | ORGANIZATION |
| `steward` | Knowledge Steward | ORGANIZATION |
| `outsider` | Contractor | **PERSONAL** |
| `system` | System | ORGANIZATION |

Switch to `outsider` in the header to watch the answer contract.

---

## 9. Flow — Frontend request lifecycle

```mermaid
flowchart TD
    U["User action"] --> P["Page sets busy=true, error=null"]
    P --> A["api.get/post()"]
    A --> Q["qs() drops undefined,<br/>null and empty string"]
    Q --> F["fetch(BASE + path)"]
    F --> R{"HTTP response"}
    R -->|"ok"| J["text() → JSON.parse<br/>(falls back to raw text)"]
    R -->|"error"| N["Normalise all four<br/>FastAPI detail shapes"]
    N --> E["ApiError {status, payload}"]
    E --> C["Page catches → error state"]
    C --> RN["ErrorNote renders it"]
    J --> S["Page sets state → re-renders"]
    S --> SH["refreshShell() re-fetches<br/>/api/actors + /api/engine"]

    style N fill:#78350f,color:#fff
    style S fill:#065f46,color:#fff
```

`refreshShell()` re-runs after every mutation so the actor list and engine
badge never drift from server state.

---

## 10. Error paths

```mermaid
flowchart TD
    E["Any request"] --> S{"Outcome"}
    S -->|"ValueError"| E1["400 invalid_input<br/>detail = message"]
    S -->|"PermissionDenied"| E2["403 permission_denied"]
    S -->|"InvalidTransition"| E3["400 · illegal lifecycle jump"]
    S -->|"Pydantic validation"| E4["422 · detail[] array<br/>client joins msgs"]
    S -->|"404"| E5["Unknown route"]
    S -->|"Engine unreachable"| E6["Degrade to SIMULATED<br/>mode recorded, warning emitted"]
    S -->|"API down"| E7["Shell stays navigable<br/>appState swallows, pages show ErrorNote"]

    style E1 fill:#78350f,color:#fff
    style E2 fill:#7f1d1d,color:#fff
    style E3 fill:#78350f,color:#fff
    style E6 fill:#78350f,color:#fff
    style E7 fill:#78350f,color:#fff
```

Every one of these is visible in the UI. The app never fails silently.

---

## 11. Verification flows

The commands to prove each claim above.

```bash
# Engine mode + bank config
curl -s http://127.0.0.1:8001/api/engine

# Full 13-step story — expect status "ok", 13 steps, progress_percent 100
curl -s -X POST http://127.0.0.1:8001/api/demo/run \
     -H "Content-Type: application/json" -d '{}'

# Permission boundary — compare visibility counts per actor
curl -s "http://127.0.0.1:8001/api/memories?actor=maya&limit=200"
curl -s "http://127.0.0.1:8001/api/memories?actor=outsider&limit=200"

# Withheld + suppression counters on a single ask
curl -s -X POST http://127.0.0.1:8001/api/ask \
     -H "Content-Type: application/json" \
     -d '{"question":"Payment API is showing connection reset alerts. What should I do?","actor":"outsider"}'

# Backend suite — expect 37 passed
.venv/Scripts/python.exe -m pytest backend/tests -q

# Frontend — expect clean exits
cd frontend && npm run lint && npm run typecheck && npm run build
```

---

## 12. Reading the traces

Every ask response carries its own execution trace, which is why the demo can
be audited rather than just watched:

```json
{
  "trace": {
    "steps": ["permission filter", "recall", "gate suppression", "lens", "reflect"],
    "recall":      { "operation": "recall", "simulated": true, "candidates_scored": 10 },
    "reflect":     [ /* per-step reflection trace */ ],
    "latency_ms":  422,
    "reflect_mode": "simulated",
    "engine_mode": "simulated",
    "engine_simulated": true,
    "fact_ids":            ["fact-…"],
    "suppressed_fact_ids": []
  }
}
```

The Ask page renders this directly, which is how a reviewer can confirm the
privacy boundary actually ran rather than taking the claim on trust.
