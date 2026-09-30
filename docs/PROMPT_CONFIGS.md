# MemoryOS — Prompt & Configuration Reference

Every piece of prompt-like configuration in the project, where it lives, and —
importantly — **what actually happens with it**. This document exists to be
auditable: if a claim here cannot be checked against the code, it should not be
in here.

---

## 1. Inventory

| # | Config | Location | Applied to | Live effect? |
|---|---|---|---|---|
| 1 | `BANK_MISSION` | `backend/memory/hindsight_client.py:43` | Memory engine bank | Yes, on `ensure_bank()` |
| 2 | `BANK_DIRECTIVES` (8) | `backend/memory/hindsight_client.py:51` | Memory engine bank | Yes, on `ensure_bank()` |
| 3 | `BANK_DISPOSITION` | `backend/memory/hindsight_client.py:63` | Memory engine bank | Yes, on `ensure_bank()` |
| 4 | `CAPTURE_PROMPTS` (10) | `backend/sources/expert_interview.py:17` | UI + ingestion | Yes |
| 5 | `TRANSCRIPT_TO_PROMPT` | `backend/sources/expert_interview.py:30` | Segmentation | Yes |
| 6 | `REASONING_TRIGGERS` (15) | `backend/memory/reflection.py:34` | Reflect gating | Yes |
| 7 | Answer section labels | `backend/memory/reflection.py` | Answer structure | Yes |
| 8 | `CONFIDENCE_DISCLAIMER` | `backend/memory/confidence.py` | Confidence output | Yes |
| 9 | Engine budgets | `hindsight_client.py:870` + `.env` | Recall/reflect depth | Yes |
| 10 | `LLM_PROVIDER` / `LLM_MODEL` | `backend/config.py:65` | — | **No — see §7** |

---

## 2. Bank mission

The identity instruction applied to the memory engine's bank.

**Location:** `backend/memory/hindsight_client.py:43`

```python
BANK_MISSION = (
    "You are the operational memory of NovaTech, an engineering organization. "
    "You preserve what the organization learned by doing things, not merely what "
    "was written down. You value: operational experience, lessons learned, "
    "exceptions to documented procedures, escalation knowledge, incident outcomes, "
    "historical context, evidence, uncertainty, and change over time."
)
```

Applied in `HindsightEngine.ensure_bank()` via `acreate_bank(mission=...)`
(`hindsight_client.py:411`).

The phrase doing the most work is *"not merely what was written down"*. It is
the reason the product distinguishes documented fact from accumulated
experience in every answer section.

---

## 3. Bank directives

Eight standing instructions. Each maps to a specific, observable behaviour in
the product — that mapping is the point of this table.

**Location:** `backend/memory/hindsight_client.py:51`

| # | Directive | Enforced by |
|---|---|---|
| 1 | Never present a historical experience as an absolute rule. | Answer sections split EXPERIENCE from RECOMMENDATION; headline says "may be outdated" when scope changed |
| 2 | Always distinguish documented fact from historical experience and inference. | `AnswerSection.kind` — `fact` / `experience` / `evidence` / `inference` / `recommendation` |
| 3 | Always state the scope a piece of knowledge applies to. | `AnswerScope`, `LensEntry.environment_match`, `excluded_scopes` |
| 4 | Cite the incidents or outcomes that support a recommendation. | `LensEntry.evidence`, `EvidenceLink.polarity` |
| 5 | If new evidence may have invalidated older knowledge, say so explicitly. | `ContradictionDetector`, `outdated_warning`, step 10's refusal |
| 6 | Prefer careful reasoning over pattern matching. | `needs_reflection()` gating on reasoning triggers |
| 7 | **Never reveal private (PERSONAL) memory through an organizational question.** | `MemoryResolver` + post-recall gate suppression — **code, not prompt** |
| 8 | Never invent incident identifiers, dates or measurements. | Every cited ID traces to a stored fact; the demo asserts real IDs (`INC-1042` …) |

Directive 7 is the important one to understand correctly: **it is defence in
depth, not the primary control.** The permission boundary is enforced in code
before and after the engine call. If the engine ignored this directive
entirely, the boundary would still hold — the resolver filters memories before
recall, and facts whose owning memory is unreachable are suppressed afterward.
A prompt is not a security boundary.

---

## 4. Disposition

**Location:** `backend/memory/hindsight_client.py:63`

```python
BANK_DISPOSITION = {
    "skepticism": 4,
    "literalism": 4,
    "empathy": 2,
}
```

High skepticism and high literalism, low empathy — a deliberate fit for an
engineering memory bank. It should doubt a confident claim, follow the recorded
procedure exactly, and not soften a negative finding about a system.

---

## 5. Capture prompts

Ten scripted prompts driving expert-interview ingestion. These are **user-facing
UI copy and input contract simultaneously** — the same list segments a submitted
transcript and renders the buttons on the Capture page.

**Location:** `backend/sources/expert_interview.py:17`

| id | Prompt | What it is designed to extract |
|---|---|---|
| `system` | What system do you know well? | Scoping anchor |
| `failure` | What usually goes wrong? | Recurring failure modes |
| `never_do` | What should a new engineer NOT do? | Prohibitions — the highest-value knowledge |
| `first_check` | What do you check first? | Deterministic first step |
| `escalate` | When should someone escalate? | Escalation knowledge |
| `who` | Who normally handles it? | Ownership / bus factor |
| `workaround` | What workaround have you used? | Undocumented practice |
| `why` | Why does that workaround exist? | Reasoning behind an exception |
| `failure_story` | Tell me about a time the normal procedure failed. | A concrete incident narrative |
| `scope` | Does this apply everywhere, or only to a specific environment? | Scope boundary — directly feeds directive 3 |

Note that `scope` is the last prompt deliberately. By the time it is asked, the
interview has enough context for the expert to answer precisely.

Classification is keyword-based per turn (`backend/api/capture.py:143`):

```
"not do" in prompt | "never"/"do not" in first 40 chars  → EXCEPTION
"who" or "escalate" in prompt                          → RELATIONSHIP
"check first" | "what should" | "procedure" in prompt  → LESSON
"failed" | "went wrong" in prompt | "incident" in text → EXPERIENCE
otherwise                                              → FACT
```

Note the rule is a single ordered `if/elif` chain: the first match wins, so the
order is load-bearing. `first_check` yields `LESSON`, and a turn matching
neither a prompt keyword nor a text keyword falls through to `FACT`.

Verified end-to-end: one interview yields `EXPERIENCE`, `LESSON`, `EXCEPTION`,
`RELATIONSHIP` and `FACT` memories — all `PERSONAL`, all `CREATED`.

---

## 6. Reasoning triggers

Whether the system pays for synthesis or just retrieves. Fifteen substrings
plus a 12-character minimum.

**Location:** `backend/memory/reflection.py:34`

```
what should i · should i · what do i · what did · why did · why do
how do · how should · what happens · is it safe · can i · should we
tell me · recommend · explain
```

Verified behaviour:

| Question | Reflects? |
|---|---|
| `Payment API is showing connection reset alerts. What should I do?` | **yes** |
| `Tell me about the outage` | **yes** |
| `Explain the queue` | **yes** |
| `Who owns payments?` | no |
| `What is the retry limit?` | no |
| `what is 2+2` | no (under 12 chars) |

Every response reports `reflect_mode` (`not_called` / `simulated` / `live`) and
`call_count`, so the decision is auditable rather than implicit.

---

## 7. LLM configuration — and why it is inert

**This section exists to prevent a false claim.**

`backend/config.py:65` defines:

```python
llm_provider: str = "none"
llm_api_key: str | None = None
llm_model: str = "gpt-4o-mini"
```

and `public_dict()` reports them at `GET /api/engine` as
`"llm_provider": "none"`, `"llm_api_key_configured": false`.

**These values are never read by any execution path.** A repository-wide search
for `llm_provider` outside `config.py` and its own test assertion returns
nothing. There is no `google-genai`, `openai`, `anthropic` or `vertexai` import
anywhere in `backend/` or `frontend/src/`.

So, precisely:

- **No external LLM is called at any point in the running application.**
- Answer text is composed deterministically from recalled facts by
  `ReflectionService`, not generated by a language model.
- `llm_model`'s default (`gpt-4o-mini`) is a placeholder that predates any
  integration and should not be read as a statement about the stack.
- The `_SIMULATED` label on engine output refers to the **Hindsight memory
  engine**, not to a language model.

If someone adds Gemini or any other model later, the honest place to wire it is
`ReflectionService.reflect()` — and at that point `llm_provider` becomes
meaningful rather than decorative.

---

## 8. Engine budgets

**Location:** `backend/memory/hindsight_client.py:870`, overridable in `.env`

```python
def budget_limit(budget: str) -> int:
    return {"low": 8, "mid": 20, "high": 50}.get(budget, 20)
```

| Setting | Default | Effect |
|---|---|---|
| `RECALL_BUDGET` | `mid` → 20 | Candidate facts retrieved per query |
| `REFLECT_BUDGET` | `low` → 8 | Depth of synthesis when reflection runs |
| `RECALL_MAX_TOKENS` | 4096 | Token ceiling mirroring Hindsight's `max_tokens` |
| `HINDSIGHT_TIMEOUT` | 60s | Per-call timeout before degrading |

Both the live and simulated engines honour these, so behaviour is comparable
across modes.

---

## 9. Confidence disclaimer

**Location:** `backend/memory/confidence.py`

Every confidence score the UI displays ships with this text, and the Stat
component marks it as a *synthetic prototype metric*. A number offered without
its limits attached is a marketing claim, not a measurement.

Confidence is computed from named factors — each with a `weight`, a `value`, a
`contribution` and a human `explanation` — plus explicit `penalties`. The Ask
page renders the factor breakdown rather than only the total, so a reviewer can
see *why* something is rated 0.79 instead of trusting the figure.

---

## 10. Answer section taxonomy

The structural half of directive 2. Every answer is split into these kinds:

| Kind | Label shown | Meaning |
|---|---|---|
| `fact` | DOCUMENTED FACT | From a document or the system itself |
| `experience` | HISTORICAL EXPERIENCE | What happened in a past incident |
| `evidence` | CURRENT EVIDENCE | What the environment shows now |
| `inference` | INFERENCE | Reasoning — explicitly *not* fact |
| `recommendation` | RECOMMENDATION | The actionable conclusion |

The separation is structural: the UI renders each kind in its own section, so
an inference cannot visually blend into a fact.

---

## 11. Changing a prompt safely

| Change | File | Also update | Verify with |
|---|---|---|---|
| Bank mission / directives | `hindsight_client.py:43-67` | `ensure_bank()` re-applies on every health check | `curl /api/engine` → `bank.directives` |
| Capture prompts | `expert_interview.py:17` | `TRANSCRIPT_TO_PROMPT` at `:30` | `GET /api/capture/prompts`; `npm run typecheck` |
| Reasoning triggers | `reflection.py:34` | Nothing | `reflect_mode` in an ask response |
| Budgets | `.env` | Nothing | `GET /api/engine` → `config` |

`BANK_DIRECTIVES` and `TRANSCRIPT_TO_PROMPT` are two lists that must stay in
sync — adding a capture prompt without adding its transcript mapping silently
breaks segmentation for that turn.
