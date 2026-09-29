# MEMORYOS — Session Log

Chronological record of what was built, what was found broken, and what is still
open. Written so the next session does not have to rediscover any of this.

**Project root:** `S:\microsoft_prj`
**Spec:** [`requried.md`](requried.md)
**Companion docs:** [`README.md`](README.md) · [`arch.md`](arch.md) · [`flow.md`](flow.md)

---

## Current status

| Area | State |
|---|---|
| Backend API | Complete — 46 endpoints under `/api` |
| Backend test suite | **37 passed** |
| Frontend | Complete — 9 pages, strict typecheck clean, production build clean |
| Browser interaction pass | All 9 pages exercised, no console or page errors |
| Full 13-step demo | `status: "ok"`, 13 steps, ~7.9s |
| Memory engine | **SIMULATED** — no Hindsight server reachable (Docker not running) |
| Documentation | This file, `README.md`, `arch.md`, `flow.md` |

Both servers run: backend on `127.0.0.1:8000`, frontend on `localhost:5173`.

---

## Phase 1 — Backend foundation

Built the service layer before any UI, because the UI is worthless if the
contracts underneath it are invented.

- `config.py` — environment-driven `Settings`, `public_dict()` that never leaks a
  key value, two separate database paths for app vs simulated state.
- `services.py` — one object graph (`Services.build()`) shared by routes and
  tests, so tests exercise the real system.
- `db/database.py` — SQLite schema: `memories`, `memory_events`, `evidence`,
  `contradictions`, `audit_events`, `learning_events`, `incidents`,
  `systems_registry`, `employees`, `architecture_changes`, `settings_kv`,
  `metrics`, `conversations`, plus indexes.
- `models/memory.py` — the schema and the `LIFECYCLE_TRANSITIONS` state machine.
- `models/permissions.py` — `Actor`, `MemoryPolicy`, `MemoryResolver`.
- `memory/hindsight_client.py` — the `MemoryEngine` interface, the live
  `HindsightEngine`, the `SimulatedHindsightEngine`, and `EngineManager` which
  probes, degrades after `live_failure_threshold` consecutive failures, and
  records why.
- `seed/novatech.py` — the synthetic company: systems, employees, 13 incidents.

**Decision that shaped everything after:** the simulated engine is never hidden.
Every simulated response carries `engine_simulated: true` and the UI shows
`HINDSIGHT (SIMULATED)`. A degraded engine that returns plausible numbers is
worse than no engine.

---

## Phase 2 — Domain logic

- `memory/ingestion.py` — the capture pipeline, with the **Memory Gate ahead of
  `retain()`** so rejected text is never written anywhere.
- `memory/retrieval.py` — recall orchestration, permission filtering, and the
  **Memory Lens** (`why_relevant`, provenance, evidence, confidence per memory).
- `memory/reflection.py` — structured answer sections
  (`DOCUMENTED FACT` / `HISTORICAL EXPERIENCE` / `CURRENT EVIDENCE` /
  `INFERENCE` / `RECOMMENDATION`), conflicts, outdated warnings.
- `memory/confidence.py` — six weighted factors, bands, and a disclaimer that is
  attached to every confidence payload.
- `memory/governance.py` — review, promote, validate, restrict, expire, all
  audited, all through `apply_transition`.
- `memory/contradiction.py` — scope-family drift detection, `INVALIDATION_MARKERS`.
- `agents/successor_agent.py` — question → resolver → recall → reflect → answer +
  lens + trace.
- `sources/` — incidents, expert interview, handover, architecture change,
  outcomes.

---

## Phase 3 — API

46 endpoints. Demo action endpoints return a uniform `{ok, message, payload}`
envelope. `/api/demo/run` returns per-step status so a partial failure is visible
rather than collapsed into a single boolean.

---

## Phase 4 — Frontend

React 18 + TypeScript + Vite + Tailwind, built by hand (no scaffolding) so the
structure matched the spec rather than a generator's defaults.

Pages: `Overview`, `Demo`, `Ask`, `Capture`, `MemoryCenter`, `Evolution`,
`Risk`, `Governance`, `Audit`. Plus `Layout` (nav, actor selector, engine
banner), `ui.tsx` primitives, and `lib/` (api client, types, shared state,
formatters).

First build: typecheck clean, production build clean.

---

## Phase 5 — Backend test failures fixed

`pytest` went from **26 passed / 9 failed** to green. Each failure was a real
defect, not a bad assertion:

1. **Missing imports in `reflection.py`** — `ConfidenceBand` and
   `CONFIDENCE_DISCLAIMER` were used but never imported. `NameError` at runtime.
2. **Outcome response was too thin** — the UI could not explain an outcome. Added
   `reinforced`, `confidence_before`, `confidence_delta`, `linked_detail`,
   `verdict`.
3. **Outcome classification was naive** — "did *not* restart" scored as failure.
   Replaced with negation-aware cue matching and an explicit verdict carrying the
   cues used.
4. **Recommendation targeting was indiscriminate** — every scoped memory got
   linked. Now uses content overlap so only memories actually about the
   acted-on recommendation are touched.
5. **Visibility ranking was lexical** — `PERSONAL`, `TEAM`, `ORGANIZATION`
   compared by enum *name* ranked `ORGANIZATION` below `PERSONAL`, silently
   inverting every permission check. Added explicit `VISIBILITY_ORDER` and
   `visibility_rank()`.
6. **Promotion authorization was not role-scoped** — added `may_promote_to`:
   owner-only to `TEAM`, Knowledge Steward only to `ORGANIZATION`.
7. **`PermissionDenied` escaped as a 500** — added a global handler returning
   `403` with `error: "permission_denied"`.
8. **Contradiction listing lacked `count`** and static `RESOLUTION_ACTIONS`.
9. **Failed-outcome detection missed memories** — the title was not being
   matched. Now considers title and scope.
10. **`restrict` was changing lifecycle status** — scope narrowing is not a claim
    about truth. Status is now left unchanged and the result reports
    `resulting_status: "unchanged"`.
11. **Demo response envelope was inconsistent** — some controls returned a bare
    dict, so the `DemoActionResponse` model rejected them with `400`.
12. **Memory cards omitted `excluded_scopes` and `tags`** — the Memory Center
    could not show that a lesson no longer applies to an environment.
13. **Test premises were wrong** in several places (actor used for a permission
    check, assumed status after `restrict`). Corrected the tests rather than
    weakening the assertions.

Two new tests were added at this stage: negation handling in outcome
classification, and the individual demo control endpoints.

**37 passed.**

---

## Phase 6 — `/api/demo/outcome` returns 400

The single remaining smoke failure, and a good example of why the full run is not
sufficient coverage.

```
POST /api/demo/outcome   {}
-> 400 {"detail": "1 validation error for DemoActionResponse: ok Field required"}
```

**Cause.** `DemoOrchestrator.record_outcome()` returned the raw
`record_outcome()` result — a dict with no `ok` key — while every other control
returned the `{ok, message, payload}` envelope. The `DemoActionResponse` model
then rejected it.

`POST /api/demo/run` passed anyway, because the runner does not go through the
per-control route. A full-run-only test would have missed this forever.

**Fix.** Wrapped the return in the standard envelope. While fixing it, an
accidental edit collapsed the `introduce_queue_v2` method into a comment, which
`AttributeError`'d on the next control — caught immediately by the new
per-control test and repaired.

**Test added:** `test_every_demo_control_endpoint_works` asserts all eleven
control endpoints return `200` with `ok: true`. All pass.

---

## Phase 7 — `duration_ms` silently dropped

`/api/demo/run` returned `id, mode, status, started_at, finished_at, steps,
progress_percent`. The orchestrator *did* compute `duration_ms`, but
`DemoRunResponse` did not declare it, so pydantic discarded it. The UI would have
rendered `undefined ms`.

**Fix.** Added `duration_ms: int = 0` to the response model, and an assertion
(`body["duration_ms"] >= 0`) to the full-demo test.

---

## Phase 8 — Browser interaction pass

Installed Playwright, drove all nine pages, clicked every interactive control,
and captured screenshots and console/page errors. This is where the frontend's
real problems appeared.

### 8.1 The Ask page crashed on submit

```
PAGEERROR: Cannot read properties of undefined (reading 'length')
  at Ask (src/pages/Ask.tsx:26)
```

**Cause — the most important defect in the project.** `Ask.tsx` and `types.ts`
had been written against an *invented* response shape:
`sections[].heading` / `.body`, `answer.recommended_actions`, `answer.caveats`,
`citations[]`, `suppressed_facts[]`, `ask_id`, `open_contradictions`,
`scope_applied`. The backend actually returns:

```
answer.sections[].label / .points[]   answer.conflicts[]   answer.scope{}   (object)
answer.confidence{ factors[{key,label,score,band}] }
lens[]            memories_used[]   hindsight_facts[]   withheld[]
trace{ steps[], recall{}, reflect[] }   privacy_notice{}   (object, not string)
```

Every one of those assumed fields did not exist. TypeScript could not catch it,
because the invented type was internally consistent.

**Fix.** Dumped the real response, modelled it exactly in `types.ts`
(`AskResponse`, `Answer`, `AnswerSection`, `AskConfidence`, `AnswerScope`,
`LensItem`, `LensSource`, `MemoryUsed`, `HindsightFact`, `AskTrace`,
`AskRecallStats`, `PrivacyNotice`, `WithheldMemory`, `TraceStep`), and rewrote
`Ask.tsx` against it — headline, sections, conflicts, scope decision, memories
used, retrieval lens, confidence, the reasoning trace, the Memory Gate
suppression panel, withheld-by-permission, warnings, run metadata.

**Lesson applied everywhere after:** the type must mirror the response. I dumped
the real payload for every endpoint the frontend consumes before trusting any of
them.

### 8.2 `Demo.tsx` step payloads

`StepPayload` also assumed `sections[].heading` / `.body`. Fixed to
`label` / `points[]`, and added the `outdated_warning` display.

### 8.3 `MemoryCenter.tsx` rendered a blank provenance block

```tsx
detail.provenance?.summary ?? ""     // provenance has no `summary` key
```

`provenance_view()` returns `source_type, source_type_label, source_id,
source_name, captured_at, observed_at, reliability_note, hindsight_fact_id,
hindsight_document_id, version` — no `summary`. The "Why this exists" block was
therefore **always** empty. Replaced with a real provenance panel plus a recall
lens block, and removed the now-dead `useMemo`.

### 8.4 `api.ts` swallowed structured 403 reasons

Promotion refusals return `detail` as an **object**:
`{"message": "Only a Knowledge Steward may promote…", "reason": "promotion_not_allowed"}`.
The client only handled string and array details, so the UI showed a generic
`Request failed (403)`. Added object handling.

### 8.5 Actor selection reset itself

`refreshShell()` ran `setActor(actorsBody.default)` on every refresh. Since
`refreshShell()` is called after every mutation, choosing an actor and then
clicking anything snapped you back to `maya` — silently defeating the privacy
demonstration. Fixed with a `chosen` ref so the default is only applied until the
user picks an actor. Verified: select `steward` → open a memory → still
`steward`.

### 8.6 The UI offered actions the lifecycle would reject

Clicking "Mark validated" on a `CREATED` memory returned
`409 Cannot move memory from CREATED to REVALIDATED.` The buttons were hard-coded
regardless of state.

**Fix (backend).** `GET /api/memories/{id}` now returns a `lifecycle` block:

```json
{ "status": "CREATED",
  "allowed_transitions": ["ACTIVE","ARCHIVED","CONFIRMED","REJECTED"],
  "actions": [ { "action": "validate", "allowed": false, "reason": "…" }, … ] }
```

derived from `LIFECYCLE_TRANSITIONS` — a projection of the state machine, not a
second copy of the rules.

**Fix (frontend).** The Actions block renders exactly those actions, disabling
the illegal ones and showing each reason, rather than three hard-coded buttons.

Found incidentally: `MemoryStatus.EXPIRED` does not exist — expiry transitions to
`STALE`. The frontend `MemoryStatus` type had listed `EXPIRED` and
`RESTRICTED`, neither of which is a real status. Corrected to the actual twelve.

### 8.7 Missing governance content

`GovernanceSummary.promotion_rule` and `retention_rule` are `null` in
`/api/governance/summary`; they live in `/api/governance/policies`, which the
page never called. The page therefore showed no promotion or retention rule at
all — the two rules that matter most on a governance page. Now fetched and
rendered above the policy list.

### 8.8 Capture prompts ignored the backend's own framing

`/api/capture/prompts` returns `heading`, `note` and `visibility_note`
alongside the prompts. The page hard-coded its own title and discarded the rest.
Now uses the server's heading and note, and surfaces the visibility warning
("Captured knowledge starts PERSONAL…").

### 8.9 Verified working

- Ask, with and without suggestions — full answer, lens, confidence, trace,
  withheld panel, warnings
- Memory Center — detail, gate, evidence, history, lifecycle actions
- Capture — sample interview, memories created, Hindsight fact ids, rejected
  text
- Governance — contradiction queue, resolution actions, policies
- Demo — all 11 individual controls, full run, step payload expansion
- Actor switch — `steward` persists, `outsider` sees the withheld notice
- Overview, Risk, Evolution, Audit — clean at both default and `steward`

No `undefined`, `NaN` or `[object Object]` anywhere in the rendered output.

---

## Phase 9 — Documentation

`README.md` (run, verify, capabilities, screens, API surface, configuration),
`arch.md` (layering, storage split, gate, permissions, lifecycle, engine
abstraction, confidence, frontend), `flow.md` (startup, capture, ask, outcome,
architecture change, promotion, lifecycle, contradiction resolution, the 13-step
demo, privacy, audit, error paths, verification), and this file.

---

## Defects found and fixed — index

| # | Defect | Where | Symptom |
|---|---|---|---|
| 1 | Missing `ConfidenceBand` / `CONFIDENCE_DISCLAIMER` imports | `reflection.py` | `NameError` |
| 2 | Thin outcome response | `outcomes.py` | UI could not explain an outcome |
| 3 | Negation-blind outcome classification | `outcomes.py` | "did not restart" read as failure |
| 4 | Indiscriminate recommendation linking | `outcomes.py` | unrelated memories reinforced |
| 5 | Lexical visibility ranking | `permissions.py` | permission checks inverted |
| 6 | No role scoping on promotion | `permissions.py` | non-steward could reach `ORGANIZATION` |
| 7 | `PermissionDenied` → 500 | `main.py` | refusals looked like server faults |
| 8 | Missing `count` / `RESOLUTION_ACTIONS` | `contradictions` route | incomplete UI contract |
| 9 | Failed-outcome detection missed titles | `contradiction.py` | failures not detected |
| 10 | `restrict` changed lifecycle status | `governance.py` | scope ≠ truth |
| 11 | Inconsistent demo envelope | `demo.py` | `400` on `/api/demo/outcome` |
| 12 | Cards missing `excluded_scopes` / `tags` | `memories.py` | scope restriction invisible |
| 13 | `duration_ms` dropped by response model | `schemas.py` | UI showed `undefined ms` |
| 14 | `Ask.tsx` modelled a nonexistent response | `Ask.tsx`, `types.ts` | **page crash on submit** |
| 15 | `Demo.tsx` step payload wrong shape | `Demo.tsx` | sections rendered blank |
| 16 | Blank provenance block | `MemoryCenter.tsx` | provenance never displayed |
| 17 | Structured 403 reason discarded | `api.ts` | generic error instead of reason |
| 18 | Actor reset on every refresh | `appState.tsx` | privacy demo defeated itself |
| 19 | Illegal lifecycle actions offered | `MemoryCenter.tsx` | `409` on valid-looking clicks |
| 20 | `MemoryStatus.EXPIRED` / `RESTRICTED` do not exist | `types.ts` | wrong status vocabulary |
| 21 | Missing promotion/retention rules on page | `Governance.tsx` | most important rules invisible |
| 22 | Capture prompts ignored server framing | `Capture.tsx` | gate visibility note hidden |

---

## Open items

**Known deviation from the build instructions (deliberate, owner decision)**

- **Bank id and current-scope lines removed from the sidebar engine card.** The
  live/simulated indicator itself is kept, so section 3 is satisfied: the UI
  shows `HINDSIGHT (LIVE)` with an emerald dot when connected and
  `HINDSIGHT (SIMULATED)` with an amber dot when not. The removed lines were
  `NovaTech - Bank memoryos-novatech` and `Current: <scope>`. The data is still
  available from `GET /api/engine` (`status.bank_id`) and `/api/actors`
  (`current_environment`) if it is ever needed in the UI.

**Blocked**

- **Live Hindsight** — no server on `http://localhost:8888`; Docker daemon is not
  running. The product runs fully on the simulated engine; the `retain` /
  `recall` / `reflect` contract is identical, but results are computed from
  stored memories rather than returned by a live instance. Verification of the
  live path is not possible until a Hindsight server is up.
- **LLM** — none configured (`LLM_PROVIDER=none`). Answers are assembled
  deterministically from recalled evidence. This is by design; polishing is
  optional.

**Not done**

- `.env.example` — settings are documented in `README.md`; an example file would
  make first-run configuration obvious.
- Frontend automated tests — coverage is currently a manual Playwright pass.
  Worth converting into a committed suite.
- Authentication — out of scope by the spec, and the README states the actor
  selector is a demonstration of the resolver, not an identity system.

**Known scope limits**

- SQLite is single-process, not built for concurrent writers.
- One bank, one company, no multi-tenancy.
- No document ingestion. The product captures *experience*, not documents.

---

## Verification snapshot

```
$ .\.venv\Scripts\python.exe -m pytest backend/tests -q
37 passed, 2 warnings in 13.64s

$ npx tsc -b --noEmit
(exit 0)

$ npm run build
✓ built

$ POST /api/demo/run
status=ok  steps=13  duration_ms=7911  progress_percent=100

$ POST /api/demo/{reset,seed,seed-incidents,capture,promote,ask,
                 outcome,queue-v2,evolution,privacy,resolve-contradictions}
all 200, ok: true

$ Playwright pass, 9 pages, all controls clicked
no console errors, no page errors
```

The two warnings from pytest are unrelated informational warnings.
