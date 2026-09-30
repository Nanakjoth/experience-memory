# MEMORYOS — Knowledge Continuity for Organizations

> "When experience leaves, memory stays."

**What it is:** an operational-memory service for organizations. It captures what
experienced engineers know, retains it in a [Hindsight](https://hindsight) memory
bank, retrieves it as *evidence*, lets an AI agent reason over it, records the
outcome of acting on that reasoning, and then refuses to apply stale knowledge
when the environment changes.

**Product statement:** We don't copy an employee's brain. We preserve what the
organization would otherwise have to learn again.

**North-star question:** What does an AI agent know because the organization has
experienced it before — and can we prove why it knows it?

> **All data in this repository is synthetic.** Every person, system, incident,
> architecture change and measurement is fictional and exists only to demonstrate
> the product. Any number shown in the UI is labelled `Synthetic prototype metric`.

---

## Documentation map

| Document | Read it when you want to know |
|---|---|
| [`README.md`](README.md) | How to run it, what each screen does, how to verify it |
| [`docs/RUNNING.md`](docs/RUNNING.md) | Every command: quick start, config, Docker, production, troubleshooting |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Structure and the reasoning behind it, with diagrams |
| [`docs/FLOWCHART.md`](docs/FLOWCHART.md) | Step-by-step runtime behaviour, traced from real runs |
| [`docs/PROMPT_CONFIGS.md`](docs/PROMPT_CONFIGS.md) | Every prompt and setting, and what each one actually does |
| [`docs/SUBMISSION.md`](docs/SUBMISSION.md) | Submission checklist evidence, and the gaps stated plainly |
| [`arch.md`](arch.md) | The code is structured the way it is |
| [`flow.md`](flow.md) | What happens at runtime, request by request |
| [`session.md`](session.md) | What was built, in what order, and what is still open |

---

## Quick start

Two terminals. No Docker, no API keys, no external services required.

### 1. Backend

```powershell
cd S:\microsoft_prj
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

- API: <http://127.0.0.1:8000>
- Interactive OpenAPI docs: <http://127.0.0.1:8000/docs>
- Memory engine status: <http://127.0.0.1:8000/api/engine>

On first start you will see a warning that Hindsight is unreachable. **That is
expected and correct.** MemoryOS falls back to a clearly-labelled
`HINDSIGHT (SIMULATED)` engine that implements the identical
`retain` / `recall` / `reflect` contract, so the whole product is fully
exercisable offline.

### 2. Frontend

```powershell
cd S:\microsoft_prj\frontend
npm install     # first time only
npm run dev
```

- UI: <http://localhost:5173> (Vite proxies `/api` to `127.0.0.1:8000`)

### 3. See the whole story in one click

Open <http://localhost:5173/demo> and press **Run full demo**. It executes 13
narrated steps against the live backend and renders the result of each one. The
same sequence is available as `POST /api/demo/run`.

---

## Verify it works

```powershell
# Backend: 37 tests covering the API, permissions, lifecycle and the full demo
cd S:\microsoft_prj
.\.venv\Scripts\python.exe -m pytest backend/tests -q

# Frontend: strict typecheck, then production build
cd S:\microsoft_prj\frontend
npx tsc -b --noEmit
npm run build
```

Expected: `37 passed`, and a clean `tsc` exit code with a successful Vite build.

---

## What the product does

MemoryOS is a closed learning loop, not a document store:

```
EXPERIENCE -> MEMORY -> EVIDENCE -> REASONING -> DECISION -> OUTCOME -> NEW EXPERIENCE
```

| Capability | What it actually does | Where |
|---|---|---|
| **Experience capture** | Interviews, incidents, handovers and outcomes are parsed into typed claims | `/capture`, `POST /api/capture` |
| **Memory Gate** | Every claim is authorized, scoped, classified and retention-checked *before* anything is stored. Rejected text never reaches the engine. | `backend/memory/ingestion.py` |
| **Provenance** | Every memory records its source type, source id, capture time and a reliability note | `backend/memory/provenance.py` |
| **Evidence-backed answers** | `POST /api/ask` returns a headline, separated sections, the exact memories used, and a full reasoning trace | `/ask` |
| **"Why did you say that?"** | The **Memory Lens** shows per memory: why it was recalled, its source, its evidence and its confidence | `backend/memory/retrieval.py` |
| **Internal confidence** | A six-factor heuristic with a visible factor breakdown — never presented as a probability | `backend/memory/confidence.py` |
| **Privacy by construction** | A `PERSONAL` memory is never returned by an organizational question, regardless of semantic similarity | `backend/models/permissions.py` |
| **Explicit promotion** | `PERSONAL -> TEAM -> ORGANIZATION` requires a named human act. `ORGANIZATION` additionally requires a Knowledge Steward. | `POST /api/memories/{id}/promote` |
| **Outcome learning** | The result of following a recommendation is recorded, classified and used to reinforce or correct memory | `/api/outcome` |
| **Contradiction, not deletion** | New contradicting evidence raises `REVIEW_REQUIRED`. A human confirms, restricts, updates or marks stale. Original text is always preserved. | `/governance` |
| **Lifecycle state machine** | Only declared transitions are legal; illegal ones are rejected with `409` and the legal set is published to the UI | `backend/models/memory.py` |
| **Knowledge-at-risk** | Systems whose critical knowledge still depends on one person | `/risk` |
| **Audit** | Every gate decision, promotion, retrieval, contradiction and lifecycle change | `/audit` |
| **Learning curve** | Real counters: memories created, retrieved, used, reinforced, contradicted | `/api/demo/learning-curve` |

---

## The demo story

The seeded company is **NovaTech**, a synthetic mid-size fintech platform. The
persona is **Maya**, a new DevOps engineer on Payments Operations. **Arun**, the
senior engineer she is replacing, is unavailable.

The continuous story, all of it executable:

1. Historical incidents are seeded as evidence (13 of them).
2. Maya asks *"Payment API is showing connection reset alerts. What should I do?"*
   — before any lesson exists, she gets a **generic** answer.
3. Arun's operational lesson is captured through an expert interview. It is
   retained as `PERSONAL`, gated, and **not** organizational yet.
4. A human **explicitly promotes** it to `ORGANIZATION`.
5. Maya asks the same question again and now gets an **evidence-backed** answer
   that cites the memory, its incidents and its provenance.
6. Maya follows the recommendation. The **outcome** is recorded, and the
   memory's confidence rises and its lifecycle moves to `USED`.
7. `Payment Queue v2` is deployed. This is an **architecture change**.
8. Maya asks again. The answer now **refuses to apply the Queue v1 lesson
   blindly** and reports the contradiction instead.
9. Contradictions are detected against the historical memories.
10. A human **restricts** scope: the lesson stays as historical knowledge for
    Queue v1, is marked not-applicable to Queue v2, and its lifecycle status is
    deliberately left unchanged.
11. The final dashboard shows what the organization learned, what it still does
    not know, and what remains single-person-dependent.

Every step is also available individually on `/demo` as a one-call control, so
you can press one step at a time and watch the numbers move.

---

## Screen guide

| Route | Screen | What to look at |
|---|---|---|
| `/` | **Overview** | Enterprise hero dashboard, synthetic metrics, continuity, knowledge-at-risk |
| `/demo` | **Guided Demo** | 13-step narrative, per-step payload inspection, one-click full run, individual controls |
| `/ask` | **Ask MemoryOS** | The central interaction: answer sections, retrieval lens, confidence, trace, withheld memories, warnings |
| `/capture` | **Capture Experience** | Expert interview, Memory Gate verdict, which claims were rejected and why, resulting Hindsight fact ids |
| `/memory` | **Memory Center** | Searchable explorer, provenance, gate decision, evidence, history, contradictions, legal lifecycle actions |
| `/evolution` | **Memory Evolution** | Timeline, memory graph, scope drift, architecture changes, contradiction state |
| `/risk` | **Knowledge at Risk** | Per-system bus-factor, successor readiness, coverage |
| `/governance` | **Governance** | Contradiction review queue, resolution actions, retention policies, promotion and retention rules |
| `/audit` | **Audit** | Every recorded event, filterable by type and actor |

Use the **actor selector** in the header to see the permission boundary change
under you. Selecting `outsider` demonstrates that no organizational memory is
reachable, whatever the Memory Gate decided.

---

## Hindsight

Hindsight is the memory engine, not an optional add-on. The product is built
around exactly three operations:

- `retain` — store approved experience into the bank `memoryos-novatech`
- `recall` — retrieve evidence for a question
- `reflect` — reason across accumulated experience (called only when the request
  is genuinely a reasoning task, not for trivial lookups)

`EngineManager` probes Hindsight on startup. If it is reachable, the live engine
is used and `mode` is `live`. If it is not, the simulated engine is used, the UI
shows an amber `HINDSIGHT (SIMULATED)` banner, and every response carries
`engine_simulated: true` and an explicit warning string. The simulated engine is
never silently presented as real.

To run a live Hindsight bank, start a Hindsight server and point MemoryOS at it:

```powershell
docker compose -f docker-compose.hindsight.yml up -d
# then restart the backend and check:
Invoke-RestMethod http://127.0.0.1:8000/api/engine | Select-Object -ExpandProperty status
# -> mode: live, simulated: false
```

`docker-compose.hindsight.yml` is included. Nothing else in the application
changes when you switch to a live engine.

---

## Configuration

All configuration is environment-driven via `backend/config.py`. No secret is
hard-coded, and `Settings.public_dict()` is the only representation that ever
leaves the process — it exposes `*_api_key_configured` booleans, never key values.

| Variable | Default | Purpose |
|---|---|---|
| `HINDSIGHT_BASE_URL` | `http://localhost:8888` | Hindsight server |
| `HINDSIGHT_API_KEY` | unset | Hindsight auth, if required |
| `HINDSIGHT_BANK_ID` | `memoryos-novatech` | Memory bank |
| `FORCE_SIMULATED_ENGINE` | `false` | Never contact a live server |
| `APP_DB_PATH` | `backend/data/memoryos.db` | Application metadata, audit, governance |
| `SIMULATED_DB_PATH` | `backend/data/hindsight_sim.db` | Simulated engine state |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed frontend origins |
| `DEFAULT_ACTOR` | `maya` | Actor used when none is chosen |
| `RECALL_BUDGET` / `REFLECT_BUDGET` | `mid` / `low` | Retrieval and reflection effort |
| `LLM_PROVIDER` | `none` | Optional answer polishing only |

**Storage split matters:** SQLite holds application metadata, permissions,
lifecycle, audit, governance and demo state. The simulated engine keeps its own
separate database. Application state and engine state are never conflated.

---

## API surface

```
GET    /api/health                                   service + engine status
GET    /api/engine                                   engine health, bank mission, public config
GET    /api/dashboard                                hero dashboard
GET    /api/catalogue                                systems, employees, incidents

POST   /api/capture                                  expert interview -> gated memories
GET    /api/capture/prompts                          interview prompts

POST   /api/ask                                      evidence-backed answer + lens + trace
GET    /api/ask/suggestions                          suggested questions
GET    /api/actors                                   actors and their real capabilities
GET    /api/conversations                            recorded ask/answer turns

GET    /api/memories                                 searchable list, permission filtered
GET    /api/memories/{id}                            detail: provenance, gate, lens, evidence,
                                                     history, contradictions, legal actions
GET    /api/memories/{id}/history                    lifecycle event log
GET    /api/memories/{id}/evidence                   evidence links + incident detail
GET    /api/memories/{id}/lens                       retrieval lens for one memory
POST   /api/memories/{id}/review                     confirm during human review
POST   /api/memories/{id}/reject                     reject, original text preserved
POST   /api/memories/{id}/promote                    explicit visibility promotion
POST   /api/memories/{id}/validate                   mark revalidated
POST   /api/memories/{id}/restrict                   narrow applicable scope
POST   /api/memories/{id}/expire                     expire to stale, never delete

POST   /api/outcome                                  record and classify the outcome
GET    /api/outcomes                                 recorded outcomes

POST   /api/architecture-change                      register a change, raise contradictions
GET    /api/contradictions                           open + resolved, with resolution actions
POST   /api/contradictions/{id}/resolve              human resolution
GET    /api/governance/summary                       distribution + resolution actions
GET    /api/governance/policies                      policies, promotion rule, retention rule
GET    /api/audit                                    filterable audit trail

GET    /api/demo/state                               current demo state
GET    /api/demo/controls                            individual step controls
POST   /api/demo/run                                 the full 13-step story
POST   /api/demo/{step}                              any single step
GET    /api/demo/before-after                        side-by-side comparison
GET    /api/demo/learning-curve                      real event counters
```

Error contract: `400` invalid input, `403` permission denied, `404` not found,
`409` illegal lifecycle transition, `422` validation. `403` details are objects
(`{message, reason}`) so the UI can explain *why* an action was refused.

---

## Tests

`backend/tests/test_api.py` covers, among others:

- every individual demo control endpoint returns `200` and `ok: true`
- the full 13-step demo completes with `status == "ok"`
- `PERSONAL` memory is never returned to another actor
- promotion to `ORGANIZATION` is refused for a non-steward
- owner-only promotion to `TEAM` is enforced
- illegal lifecycle transitions are rejected
- `restrict` preserves history and leaves the lifecycle status unchanged
- outcome classification handles negation ("did not restart" is a success)
- failed outcomes raise contradictions instead of silently reinforcing
- the Memory Gate rejects secret-like content and stores nothing
- confidentiality is never returned by an organizational ask

---

## Project layout

```
S:\microsoft_prj
├─ README.md              this file
├─ arch.md                architecture and design decisions
├─ flow.md                runtime flows, request by request
├─ session.md             build log and current status
├─ requried.md            the original specification
├─ docker-compose.hindsight.yml   optional live Hindsight bank
├─ api.log                backend runtime log
│
├─ backend/
│  ├─ main.py             FastAPI app, routers, exception handlers
│  ├─ config.py           environment-driven settings, public config
│  ├─ services.py         service container (one object graph for app + tests)
│  ├─ actors.py           the synthetic cast
│  ├─ api/                routes only: ask, capture, memories, governance,
│  │                      outcomes, audit, dashboard, demo, schemas, routes
│  ├─ memory/             the domain: hindsight_client, ingestion, retrieval,
│  │                      reflection, confidence, governance, contradiction,
│  │                      lifecycle, provenance
│  ├─ models/             memory schema, lifecycle state machine, permissions
│  ├─ db/database.py      SQLite schema and all queries
│  ├─ sources/            source adapters: incidents, expert_interview,
│  │                      handover, architecture, outcomes
│  ├─ agents/             successor agent
│  ├─ seed/novatech.py    the synthetic company
│  └─ tests/              test suite
│
└─ frontend/
   ├─ vite.config.ts      port 5173, /api proxy
   ├─ tailwind.config.js
   └─ src/
      ├─ App.tsx          routes
      ├─ components/      Layout, ui primitives
      ├─ lib/             api client, types, shared state, formatters
      └─ pages/           Overview, Demo, Ask, Capture, MemoryCenter,
                         Evolution, Risk, Governance, Audit
```

---

## Known limitations

- The memory engine runs **simulated** unless a Hindsight server is reachable.
  The contract is identical, but the results are computed from actually stored
  memories rather than returned by a live Hindsight instance.
- **No LLM is configured, and none is called.** `LLM_PROVIDER=none` means
  answers are assembled deterministically from recalled evidence and bank
  directives — there is no external model in the execution path. See
  [`docs/PROMPT_CONFIGS.md`](docs/PROMPT_CONFIGS.md) §7.
- **No Google Cloud or Gemini integration exists.** The project is
  container-ready (two Dockerfiles, healthchecks, a durable volume) but has no
  cloud deployment and no Gemini API usage. Stated plainly in
  [`docs/SUBMISSION.md`](docs/SUBMISSION.md) §4.1.
- The frontend has **no automated tests**. It is gated on strict TypeScript,
  ESLint and a production build; functional verification is currently manual.
- The SQLite store is single-process and not designed for concurrent writers.
- Authentication is out of scope. The actor selector is a *demonstration* of the
  permission resolver, not an identity system.
- Everything is synthetic and must not be presented as real operational data.
