# MemoryOS --- Copilot Final Build & Demo Instructions

## Mission

You are continuing an existing MemoryOS prototype. **Do not restart,
rewrite, or expand it into a different product.** The architecture and
core workflow already exist.

Your job now is:

1.  Verify the existing implementation.
2.  Get **real Hindsight** running.
3.  Keep the clearly-labelled simulated fallback.
4.  Verify the complete learning loop.
5.  Polish the existing product for a strong hackathon demo.
6.  Do not add random integrations or unrelated agents.

Product:

> **MemoryOS --- Knowledge Continuity for Organizations**

Tagline:

> **When experience leaves, memory stays.**

Core statement:

> We don't copy an employee's brain. We preserve what the organization
> would otherwise have to learn again.

North-star question:

> What does an AI agent know because the organization has experienced it
> before --- and can we prove why it knows it?

------------------------------------------------------------------------

# 1. Do not change the architecture

The existing architecture is intentional:

``` text
React + TypeScript
       |
       v
FastAPI
       |
       v
Services / Domain
       |
       +-------------------+
       |                   |
       v                   v
Application SQLite     Hindsight
governance metadata    memory engine
       |                   |
       +-- audit           +-- retain
       +-- permissions     +-- recall
       +-- lifecycle       +-- reflect
       +-- evidence
       +-- contradictions
       +-- outcomes
```

SQLite is application/governance state, NOT a competing memory store.

Keep the existing:

-   Memory Gate
-   permissions
-   lifecycle
-   provenance
-   Memory Lens
-   confidence
-   outcomes
-   contradictions
-   architecture changes
-   audit
-   Knowledge-at-Risk
-   synthetic NovaTech data
-   demo orchestration
-   `HindsightEngine`
-   `SimulatedHindsightEngine`
-   `EngineManager`

------------------------------------------------------------------------

# 2. First inspect, then edit

Before changing anything:

-   Read `README.md`
-   Read `arch.md`
-   Read `flow.md`
-   Read `session.md`
-   Read `requried.md`
-   Inspect backend and frontend
-   Run existing tests
-   Run TypeScript check
-   Run production build
-   Start backend/frontend
-   Check `/api/engine`

Do not assume something is broken. Use the existing code as the source
of truth.

If something already works, leave it alone.

------------------------------------------------------------------------

# 3. Real Hindsight is now P0

Current fallback:

``` text
HINDSIGHT (SIMULATED)
```

is acceptable during development.

Final demo target:

``` text
mode: live
simulated: false
```

The application must use:

``` text
EngineManager
   |
   +-- HindsightEngine
   |
   +-- SimulatedHindsightEngine
```

Never remove the fallback.

Never present simulated results as real Hindsight.

When live Hindsight is unavailable, the UI must clearly say:

``` text
HINDSIGHT (SIMULATED)
```

When live:

``` text
HINDSIGHT
LIVE
```

Verify actual:

-   `retain()`
-   `recall()`
-   `reflect()`

against the live Hindsight server before claiming the final demo is
live.

------------------------------------------------------------------------

# 4. One workflow only

The entire product supports one story.

### Persona

**Maya** --- new DevOps engineer in Payments Operations.

### Experienced engineer

**Arun** --- senior engineer whose operational knowledge is being
transferred.

### System

**Payment Queue v1**

Later:

**Payment Queue v2**

Example tacit knowledge:

> When Payment API shows connection-reset alerts, do not immediately
> restart. Check queue depth first. If it is above 80%, contact Payments
> Operations because a previous restart caused duplicate processing.

The important information is not just the sentence. Memory must
preserve:

-   why the lesson exists
-   historical incidents
-   evidence
-   scope
-   source
-   confirmation
-   recency
-   outcomes
-   whether it still applies

------------------------------------------------------------------------

# 5. Core learning loop

The product must visibly demonstrate:

``` text
EXPERIENCE
   ↓
CAPTURE
   ↓
MEMORY GATE
   ↓
HINDSIGHT RETAIN
   ↓
MEMORY
   ↓
HINDSIGHT RECALL
   ↓
HINDSIGHT REFLECT
   ↓
DECISION
   ↓
OUTCOME
   ↓
NEW EVIDENCE
   ↓
REINFORCE OR CONTRADICT
   ↓
ENVIRONMENT CHANGES
   ↓
OLD MEMORY MAY NO LONGER APPLY
```

Hindsight must be central to the value, not merely a hidden database.

------------------------------------------------------------------------

# 6. Capture experience

The Capture screen should feel like a senior engineer handing over
knowledge.

Capture:

-   what happened
-   what normally happens
-   what to check first
-   what NOT to do
-   why
-   exceptions
-   component/system
-   environment
-   supporting incidents
-   source/date/owner
-   sensitivity
-   scope

Example:

``` text
Maya:
What should I know before handling Payment API connection-reset alerts?

Arun:
Don't restart immediately.

Maya:
Why?

Arun:
We had three incidents where restarting made the queue worse.
Check queue depth first. If it is above 80%, contact Payments Ops.
```

Claims can become:

-   EXPERIENCE
-   LESSON
-   EXCEPTION
-   RELATIONSHIP
-   FACT

------------------------------------------------------------------------

# 7. Memory Gate

The Memory Gate must run **before** Hindsight `retain()`.

Check:

-   authorization
-   purpose
-   scope
-   sensitivity
-   retention
-   obvious secrets/credentials

Rejected content must never reach Hindsight.

Show the decision clearly:

``` text
MEMORY GATE

✓ Authorized
✓ Purpose valid
✓ Scope identified
✓ Sensitivity: INTERNAL
✓ Retention compliant

STORE
```

For rejected content:

``` text
REJECTED BEFORE RETENTION

Credential-like content detected.

Nothing was written to Hindsight.
```

------------------------------------------------------------------------

# 8. Memory lifecycle and promotion

Keep the lifecycle and governance model.

Conceptually:

``` text
CREATED
 ↓
CONFIRMED
 ↓
ACTIVE
 ↓
USED / SUPPORTED / REVALIDATED / UPDATED
                    \
                     → CONTRADICTED / STALE
```

Never silently overwrite old knowledge.

Captured knowledge starts:

``` text
PERSONAL
```

Then:

``` text
PERSONAL → TEAM → ORGANIZATION
```

Promotion must be an explicit human action and must remain enforced by
backend permissions.

------------------------------------------------------------------------

# 9. Ask is the central screen

Question:

> Payment API is showing connection reset alerts. What should I do?

Flow:

``` text
Question
 ↓
Hindsight recall
 ↓
Permission filtering
 ↓
Memory Lens
 ↓
Hindsight reflect
 ↓
Scope evaluation
 ↓
Confidence
 ↓
Evidence-backed answer
```

Answer sections should distinguish:

-   DOCUMENTED FACT
-   HISTORICAL EXPERIENCE
-   CURRENT EVIDENCE
-   INFERENCE
-   RECOMMENDATION

Never present inference as fact.

------------------------------------------------------------------------

# 10. Memory Lens --- make this a hero feature

Every important answer should support:

> **Why did you say that?**

Show:

``` text
WHY THIS MEMORY WAS USED

Memory:
"Do not restart above 80% queue depth"

Why relevant:
Same component family
Same alert pattern
Same operational condition

Evidence:
3 historical incidents

Outcome history:
2 successful resolutions

Confirmed by:
Knowledge Steward

Validated:
11 days ago

Scope:
Payment Queue v1

Current environment:
MATCH

Hindsight:
recall → reflect

Confidence:
HIGH
```

Also allow:

-   What evidence supports this?
-   Who confirmed it?
-   When was it validated?
-   When does it expire?
-   Who can access it?

This should feel like an investigation panel, not a generic chatbot
citation list.

------------------------------------------------------------------------

# 11. Outcome learning

After Maya follows the recommendation:

``` text
Action:
Checked queue depth.
Did NOT restart.
Contacted Payments Ops.

Result:
Incident resolved.
```

Record the outcome.

Show:

``` text
MEMORY USED

Confidence:
0.74 → 0.82

Evidence:
+1 supporting outcome

Lifecycle:
ACTIVE → USED
```

If it fails:

``` text
MEMORY CONTRADICTION

The recommendation was followed,
but the result was unsuccessful.

Do not reinforce the memory.
Review required.
```

The outcome must change the memory state/evidence, not merely create a
log.

------------------------------------------------------------------------

# 12. Killer moment: environment change

This is the most important demo.

Introduce:

``` text
ARCHITECTURE CHANGE

Payment Queue v2 deployed.

Previous Queue v1 procedure may no longer apply.
```

Ask the exact same question.

The agent must NOT blindly repeat the old lesson.

It should say something like:

``` text
⚠ HISTORICAL KNOWLEDGE MAY BE OUTDATED

Relevant memory:
Do not restart above 80%.

Memory scope:
Payment Queue v1

Current environment:
Payment Queue v2

Architecture change:
Queue v2 deployed

Recommendation:
Do not automatically apply the historical procedure.

REVIEW REQUIRED
```

This is the central innovation.

The system remembers the lesson AND its context.

------------------------------------------------------------------------

# 13. Contradiction UI

Make this visually obvious:

``` text
MEMORY EVOLUTION

2026-09-10
Arun teaches:
"Do not restart above 80%."

        ↓

2026-09-15
Maya follows lesson.
Incident resolved.

        ↓

2026-09-29
Payment Queue v2 deployed.

        ↓

⚠ CONTRADICTION DETECTED

Old scope:
Queue v1

Current scope:
Queue v2

        ↓

REVIEW REQUIRED
```

Actions:

-   Confirm
-   Restrict
-   Update
-   Archive

Never silently delete historical knowledge.

------------------------------------------------------------------------

# 14. Knowledge at Risk

Keep this screen focused on organizational dependency:

``` text
KNOWLEDGE AT RISK

Payment Queue
Critical knowledge: 14
Captured: 11
Validated: 9
Single-person dependent: 3
```

The point is:

``` text
employee dependency
       ↓
captured experience
       ↓
validated organizational memory
       ↓
less single-person dependency
```

All numbers are synthetic prototype metrics.

------------------------------------------------------------------------

# 15. Dashboard

Do not overload it.

Primary cards:

``` text
ORGANIZATIONAL MEMORIES
128

ACTIVE
94

KNOWLEDGE AT RISK
3

STALE MEMORIES
7

CONTRADICTIONS
2

MEMORIES USED
41
```

Label prototype numbers:

> Synthetic prototype metric

Hero:

> **YOUR ORGANIZATION HAS A MEMORY**

Visual:

``` text
Experience
   ↓
Memory
   ↓
Evidence
   ↓
Learning
   ↓
Better decisions
```

------------------------------------------------------------------------

# 16. Judge Mode

Keep the existing detailed 13-step demo for development.

Create/maintain a compact **Judge Mode** that tells the entire story in
about 90 seconds.

### 1. Before memory

Maya asks.

Show:

``` text
GENERIC RESPONSE
```

### 2. Capture

Arun teaches the lesson.

Show:

``` text
HINDSIGHT RETAIN
```

### 3. Promote

Show:

``` text
ORGANIZATION MEMORY
```

### 4. Ask again

Show:

``` text
EVIDENCE-BACKED RESPONSE
```

### 5. Outcome

Show:

``` text
MEMORY REINFORCED
```

### 6. Environment change

Show:

``` text
QUEUE V2 DEPLOYED
```

### 7. Ask again

Show:

``` text
MEMORY MAY BE STALE
CONTRADICTION DETECTED
```

### 8. Closing

``` text
The organization learned.

Not because the AI remembered everything.

Because it remembered:
what happened,
why it mattered,
where it applied,
and when it stopped applying.
```

------------------------------------------------------------------------

# 17. Before/after must be obvious

Show side-by-side.

## BEFORE

``` text
Maya:
Payment API connection reset.
What should I do?

AI:
Check service health.
Consider restarting.
```

## AFTER

``` text
Maya:
Payment API connection reset.
What should I do?

MemoryOS:
DO NOT RESTART YET.

3 historical incidents
2 successful resolutions
Scope matches
Validated 11 days ago
Confidence HIGH
```

Then after Queue v2:

``` text
MemoryOS:
The historical lesson is relevant,
but the environment no longer matches.

Do not blindly apply it.

REVIEW REQUIRED.
```

------------------------------------------------------------------------

# 18. Hindsight visibility

The judge must be able to see that Hindsight is actually used.

Show a compact trace:

``` text
MEMORY TRACE

1. HINDSIGHT RECALL
   8 candidate memories

2. PERMISSION FILTER
   5 available
   3 withheld

3. MEMORY LENS
   3 relevant memories

4. HINDSIGHT REFLECT
   historical synthesis

5. RESPONSE
   recommendation

6. OUTCOME
   memory reinforced
```

Where technically possible, display:

``` text
retain()
recall()
reflect()
```

Do not just display a badge saying "Powered by Hindsight."

------------------------------------------------------------------------

# 19. UI direction

Make the product look like a serious enterprise operations product.

Prefer:

-   light background
-   white cards
-   dark navy typography
-   one restrained accent
-   subtle borders
-   compact information density
-   strong typography hierarchy
-   professional charts
-   restrained animation

Avoid:

-   generic purple AI gradients
-   robot graphics
-   excessive glass effects
-   childish chatbot styling
-   huge decorative AI animations
-   feature overload

The visual identity should be:

``` text
Enterprise operations console
+
AI reasoning interface
+
Memory investigation system
```

------------------------------------------------------------------------

# 20. Do NOT build

Do not add unless required to fix a blocker:

-   ServiceNow integration
-   Jira integration
-   Slack integration
-   Teams integration
-   email ingestion
-   Kubernetes integration
-   real enterprise SSO
-   billing
-   multi-tenant SaaS
-   customer portal
-   many unrelated agents
-   graph database
-   healthcare workflow
-   sales workflow
-   AP workflow
-   support workflow
-   complex analytics
-   unnecessary deployment infrastructure

One workflow, one persona, one value proposition.

------------------------------------------------------------------------

# 21. Verification

Run:

``` text
pytest
```

Then:

``` text
npx tsc -b --noEmit
npm run build
```

Browser-test:

-   Overview
-   Demo
-   Ask
-   Capture
-   Memory Center
-   Evolution
-   Risk
-   Governance
-   Audit

Also verify:

-   actor switching
-   permissions
-   Memory Gate rejection
-   lifecycle transitions
-   promotion
-   outcome success
-   outcome failure
-   contradiction
-   stale knowledge
-   live Hindsight
-   simulated fallback

------------------------------------------------------------------------

# 22. No fabrication

Never:

-   claim simulated Hindsight is live
-   fabricate Hindsight responses
-   claim synthetic metrics are real
-   expose credentials
-   store secrets
-   use real employee/customer information
-   silently overwrite contradictions
-   present internal confidence as calibrated probability
-   claim real-world adoption without evidence

All demo data is synthetic.

------------------------------------------------------------------------

# 23. Priority order

Work in this order:

## P0 --- REAL HINDSIGHT

Get the live Hindsight engine working.

## P1 --- VERIFY LEARNING LOOP

Verify:

``` text
retain
→ recall
→ reflect
→ outcome
→ reinforcement
→ architecture change
→ contradiction
```

## P2 --- JUDGE MODE

Create the 90-second story.

## P3 --- MEMORY LENS

Make "Why did you say that?" excellent.

## P4 --- CONTRADICTION

Make Queue v1 → Queue v2 the strongest visual moment.

## P5 --- UI POLISH

Make the existing product look professional.

## P6 --- TEST

Backend + frontend + browser.

## P7 --- PRESENTATION

Prepare final screenshots/demo.

------------------------------------------------------------------------

# 24. Decision rule

If choosing between:

``` text
another feature
```

and:

``` text
make existing memory behavior more visible and believable
```

choose the second.

If choosing between:

``` text
more pages
```

and:

``` text
better Hindsight retain/recall/reflect demonstration
```

choose the second.

If choosing between:

``` text
more architecture
```

and:

``` text
better before/after learning curve
```

choose the second.

------------------------------------------------------------------------

# 25. Final judge story

Use this narrative:

> Companies don't only lose employees.
>
> They lose the experience those employees accumulated.
>
> Maya is replacing Arun on Payments Operations.
>
> Arun knows a subtle operational lesson that never made it into the
> runbook.
>
> MemoryOS captures the lesson and stores it in Hindsight.
>
> Maya asks the same question later.
>
> The agent doesn't just answer --- it shows the historical evidence
> behind the answer.
>
> Maya follows the recommendation and the outcome becomes new evidence.
>
> Then the environment changes.
>
> Payment Queue v2 replaces Queue v1.
>
> The agent remembers the old lesson --- but refuses to blindly trust
> it.
>
> It detects that the environment changed and asks for review.
>
> That is organizational memory.
>
> Not remembering everything.
>
> Remembering what happened, why it mattered, where it applied, and when
> it stopped applying.

------------------------------------------------------------------------

# 26. Completion checklist

Do not declare the project finished merely because the frontend builds.

Complete means:

-   [ ] Real Hindsight works
-   [ ] Simulated fallback works
-   [ ] `retain()` is verified live
-   [ ] `recall()` is verified live
-   [ ] `reflect()` is verified live
-   [ ] experience capture works
-   [ ] Memory Gate runs before retention
-   [ ] permissions work
-   [ ] promotion works
-   [ ] outcome changes memory evidence/state
-   [ ] contradiction is detected
-   [ ] stale knowledge is not blindly applied
-   [ ] Memory Lens explains why memory was used
-   [ ] Knowledge-at-Risk is visible
-   [ ] audit trail is visible
-   [ ] before/after learning is obvious
-   [ ] Judge Mode works in approximately 90 seconds
-   [ ] all tests pass
-   [ ] frontend builds
-   [ ] simulated data is clearly labelled
-   [ ] no simulated result is presented as live

------------------------------------------------------------------------

# 27. Copilot operating rule

Do not make large speculative changes.

For each phase:

1.  Inspect.
2.  State what is actually missing.
3.  Make the smallest necessary change.
4.  Run tests.
5.  Verify behavior.
6.  Continue only after verification.

If something already satisfies the requirement, **do not rewrite it**.

If a requirement conflicts with the existing architecture, stop and
explain the conflict before changing architecture.

The goal is not maximum code.

The goal is the most convincing demonstration that an AI agent can
acquire organizational experience, use it, learn from outcomes, and
recognize when old experience no longer applies.

# END
