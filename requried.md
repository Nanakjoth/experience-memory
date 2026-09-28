You are the lead engineer, product designer, AI architect, and hackathon technical lead for this project.

BUILD THE COMPLETE APPLICATION.

Do not merely explain how to build it.
Do not give me pseudocode.
Do not create a static mockup.
Actually create the project files, code, data, UI, API routes, tests, README, configuration, and demo flow.

You have autonomy to create and modify files in the repository.

============================================================
PROJECT
============================================================

Product name:

MEMORYOS

Subtitle:

Knowledge Continuity for Organizations

Core tagline:

"When experience leaves, memory stays."

Core product statement:

"We don't copy an employee's brain.
We preserve what the organization would otherwise have to learn again."

North-star question:

"What does an AI agent know because the organization has experienced it before — and can we prove why it knows it?"

============================================================
IMPORTANT COMPETITION CONTEXT
============================================================

This is an AI-agent memory competition using Hindsight.

The project must demonstrate that Hindsight is CENTRAL to the product.

Do NOT build a generic chatbot with a vector database.

Do NOT build a generic RAG application.

Do NOT build a simple employee offboarding form.

Do NOT build a document search engine.

Do NOT build a fake AI dashboard with static numbers.

The product must demonstrate:

EXPERIENCE
    ↓
MEMORY
    ↓
EVIDENCE
    ↓
REASONING
    ↓
DECISION
    ↓
OUTCOME
    ↓
NEW EXPERIENCE
    ↓
MEMORY EVOLUTION

The system must visibly become more useful as it accumulates experience.

============================================================
THE PROBLEM
============================================================

Organizations do not only lose employees.

They lose:

- operational judgment
- undocumented workarounds
- lessons from incidents
- knowledge of what NOT to do
- escalation knowledge
- relationships
- exception handling
- historical reasoning
- knowledge of why a process exists
- knowledge of when a documented procedure should NOT be followed
- knowledge of when old knowledge is no longer valid

Documentation normally answers:

"What should I do?"

MemoryOS should answer:

"What did experienced people learn when they actually did this before?"

Example:

A runbook says:

"Restart Payment API."

An experienced engineer knows:

"Do NOT restart immediately if the payment queue is saturated because a previous restart caused duplicate processing."

That second piece is the valuable knowledge.

============================================================
CORE DIFFERENTIATION
============================================================

Traditional AI:

Question → Answer

RAG:

Question → Retrieve documents → Answer

MemoryOS:

Experience
→ Memory
→ Evidence
→ Context
→ Reasoning
→ Outcome
→ Learning
→ Governed future use

The product must make this difference visually obvious.

============================================================
PRIMARY USE CASE
============================================================

Initial commercial wedge:

ORGANIZATIONAL KNOWLEDGE CONTINUITY

Concrete scenario:

A senior DevOps engineer leaves or becomes unavailable.

The organization must not lose the engineer's operational judgment.

However, this is NOT just an "employee offboarding" product.

Employee departure is the stress test.

The actual product is:

CONTINUOUS INSTITUTIONAL MEMORY.

Knowledge should be captured while employees are working, not only on their last day.

============================================================
PRIMARY DEMO PERSONA
============================================================

Synthetic fictional company:

NovaTech

Synthetic employee:

Arun

Role:

Senior DevOps Engineer

System:

Payment Platform

Service:

Payment API

Queue:

Payment Queue v1

The entire demo must use synthetic data.

Never use real company secrets.
Never use real credentials.
Never use real employee information.
Never use real customer data.

Clearly display:

"SYNTHETIC DEMO DATA"

============================================================
THE HERO STORY
============================================================

The demo must tell one continuous story.

PART 1 — EXPERT KNOWLEDGE

Arun teaches MemoryOS:

"When Payment API starts showing connection-reset alerts, don't immediately restart it.

First check Payment Queue depth.

If queue depth is above 80%, contact Payments Operations before restarting.

We previously restarted during this condition and caused duplicate payment processing.

This procedure applies to Payment Queue v1."

MemoryOS processes this using Hindsight.

Hindsight must extract useful memories.

Examples:

EXPERIENCE:
Restarting Payment API during queue saturation caused duplicate processing.

LESSON:
Check queue depth before restarting.

EXCEPTION:
The rule applies to Payment Queue v1.

RELATIONSHIP:
Payments Operations handles queue-related escalation.

FACT:
Payment API depends on Payment Queue v1.

============================================================
PART 2 — HISTORICAL EVIDENCE
============================================================

Create synthetic historical incidents.

INC-1042:

Payment API
Connection reset
Queue = 91%

Action:
Restarted immediately

Outcome:
Duplicate payment processing

Engineer:
Arun


INC-1088:

Payment API
Connection reset
Queue = 87%

Action:
Checked queue
Contacted Payments Operations
Did not restart

Outcome:
Resolved without duplicate processing


INC-1104:

Payment API
Connection reset
Queue = 84%

Action:
Checked queue
Followed Payments Operations procedure

Outcome:
Resolved without restart

These incidents are NOT just fake UI cards.

They must actually be retained into Hindsight.

============================================================
PART 3 — SUCCESSOR
============================================================

Introduce:

Maya

Role:

New DevOps Engineer

Maya asks:

"Payment API is showing connection reset alerts. What should I do?"

The application must use Hindsight.

The agent should:

1. Understand the question.
2. Recall relevant memories.
3. Consider historical experiences.
4. Reflect over the evidence.
5. Produce an answer.
6. Show the evidence behind the answer.
7. Clearly distinguish historical facts from recommendations.
8. Avoid pretending historical experience is an absolute rule.

Expected response:

"Do not restart immediately.

First check Payment Queue depth.

Historical organizational experience indicates that restarting during queue saturation caused duplicate processing.

Current historical evidence:
- INC-1042: 91% queue → restart → duplicate processing
- INC-1088: 87% queue → no restart → resolved
- INC-1104: 84% queue → no restart → resolved

For Payment Queue v1:
1. Check queue depth.
2. If above 80%, contact Payments Operations.
3. Understand/drain the queue as instructed.
4. Restart only after the condition is understood."

The exact wording may differ.

The important requirement is that the answer must be grounded in Hindsight memories.

============================================================
PART 4 — WHY DID YOU SAY THAT?
============================================================

Every important AI recommendation must have:

[ WHY DID I SAY THIS? ]

Clicking it opens:

MEMORY LENS

Show:

- memories used
- source
- memory type
- supporting incidents
- dates
- scope
- validation status
- confidence indicator
- current environment match
- contradictions
- why the memory was considered relevant

Example:

WHY THIS RECOMMENDATION?

Memory:
"Do not restart during queue saturation."

Source:
Arun expert interview

Supporting evidence:
INC-1042
INC-1088
INC-1104

Supporting observations:
3

Scope:
Payment Queue v1

Last validated:
synthetic date

Current environment:
Payment Queue v1

Status:
ACTIVE

This is critical.

The product must answer:

"Why does the AI know this?"

============================================================
PART 5 — OUTCOME LEARNING
============================================================

After Maya follows the recommendation, provide:

[ RECORD OUTCOME ]

Fields:

Question

Recommendation

Actual action

Result

Notes

Example:

Queue:
88%

Action:
Contacted Payments Operations

Result:
Resolved without restart

Notes:
Queue drained automatically after four minutes.

When the user submits the outcome:

RETAIN it into Hindsight.

The system must treat the outcome as a new observation/experience.

This creates:

OLD EXPERIENCE
+
NEW OUTCOME
=
STRONGER ORGANIZATIONAL MEMORY

============================================================
PART 6 — THE BIG DIFFERENTIATOR
============================================================

Now introduce new evidence.

Payment Queue v2 has been deployed.

New architecture:

Payment Queue v2

The previous Payment Queue v1 procedure is no longer automatically valid.

Add this to Hindsight:

"Payment Queue v2 was deployed.

The restart procedure has changed.

The historical Payment Queue v1 lesson must not automatically be applied to Queue v2.

Validate the new operational procedure with Payments Operations."

Now ask the SAME question:

"Payment API is showing connection reset alerts. What should I do?"

The system MUST NOT blindly repeat:

"Never restart above 80%."

Instead, it should recognize that the historical memory has a scope:

Payment Queue v1

and current environment is:

Payment Queue v2

The system should surface:

⚠ KNOWLEDGE MAY BE OUTDATED

Historical memory:
Do not restart above 80%.

Scope:
Payment Queue v1

Current environment:
Payment Queue v2

New evidence:
Restart procedure changed.

Recommended action:
Validate the new procedure before applying the historical lesson.

============================================================
CONTRADICTION EXPERIENCE
============================================================

Create a dedicated UI:

MEMORY EVOLUTION

Show:

OLD KNOWLEDGE

Queue >80%
↓
Do not restart


NEW EVIDENCE

Payment Queue v2
↓
Restart procedure changed


SYSTEM

⚠ POTENTIAL CONTRADICTION


Do not silently overwrite the old memory.

Instead:

OLD MEMORY
+
NEW EVIDENCE
=
REVIEW REQUIRED

Possible actions:

[ Confirm old memory ]
[ Restrict scope ]
[ Update memory ]
[ Mark stale ]

When updated:

Payment Queue v1:
Do not restart above 80%

Payment Queue v2:
Procedure requires validation

The historical lesson remains preserved.

This is important.

Never destroy history simply because newer information arrived.

============================================================
HINDSIGHT REQUIREMENTS
============================================================

Use the real Hindsight integration.

Do NOT simulate Hindsight in the main flow.

Use Hindsight as the actual memory engine.

Primary operations:

retain
recall
reflect

Current Hindsight behavior:

retain:
Stores raw information and extracts facts/entities/relationships.

recall:
Retrieves relevant memories.

reflect:
Reasons over relevant memories and produces a synthesized response.

Use async Hindsight methods inside FastAPI.

Prefer:

aretain
arecall
areflect

over synchronous calls inside async endpoints.

============================================================
HINDSIGHT MEMORY BANK
============================================================

Create a dedicated bank:

memoryos-novatech

Do not mix demo data with unrelated memory.

Use bank-level isolation.

Configure the bank mission/disposition so that Hindsight prioritizes:

- operational experience
- lessons learned
- exceptions
- outcomes
- historical context
- evidence
- uncertainty
- changes over time

The system should favor careful reasoning over blindly following historical patterns.

============================================================
MEMORY TYPES
============================================================

Create an application-level memory schema.

Support:

FACT
EXPERIENCE
LESSON
OBSERVATION
DECISION
EXCEPTION
RELATIONSHIP
COMMITMENT
HYPOTHESIS
CORRECTION
EVENT

Every application memory should contain, where applicable:

id
type
content
source
source_id
scope
owner
domain
purpose
created_at
observed_at
last_validated_at
expiry_at
confidence
evidence_count
status
sensitivity
access_level
related_entities
related_memories

Do not assume Hindsight will return every application field automatically.

Store important application metadata alongside Hindsight references.

============================================================
MEMORY VISIBILITY
============================================================

Support:

PERSONAL
TEAM
ORGANIZATION

Never automatically promote:

PERSONAL → TEAM

or:

TEAM → ORGANIZATION

Promotion must be explicit.

For the hackathon MVP, demonstrate:

Arun personal expert input

→ reviewed

→ promoted to organizational operational knowledge

Show this transition in the UI.

============================================================
MEMORY GATE
============================================================

Before storing a memory, the system should conceptually evaluate:

1. Is this useful in the future?
2. Does it need persistent memory?
3. Is it sensitive?
4. What is its purpose?
5. What is its scope?
6. Who should access it?
7. How long should it remain valid?
8. Is authorization required?

Do not store secrets.

Do not store credentials.

Do not store unnecessary personal information.

For the prototype, expose a small:

MEMORY GATE

panel showing:

Purpose
Scope
Sensitivity
Retention
Authorization

============================================================
CONFIDENCE
============================================================

Implement an application-level INTERNAL confidence indicator.

Do not pretend it is a scientifically calibrated probability.

Use factors such as:

- source reliability
- number of supporting incidents
- human confirmation
- recency
- contradiction
- scope match
- outcome success

Example:

Initial expert lesson:
Confidence: Medium

After human confirmation:
Confidence: High

After 3 supporting incidents:
Confidence: Very High

After contradiction:
Confidence decreases

After becoming stale:
Confidence decreases / status changes

Label it:

"Internal confidence"

NOT:

"Probability that this is true"

============================================================
KNOWLEDGE EVOLUTION
============================================================

Implement:

Created
↓
Confirmed
↓
Used
↓
Observed
↓
Supported / Contradicted
↓
Updated
↓
Revalidated
↓
Active / Stale / Archived

Show this visually.

============================================================
DATA COLLECTION
============================================================

The product should eventually support multiple input sources.

For the hackathon prototype implement adapters/interfaces for:

1. Expert interview
2. Incident records
3. Handover documents
4. Outcome feedback
5. Architecture/change records

Do not build real enterprise integrations unless trivial.

Use synthetic adapters.

Create an interface like:

KnowledgeSource

with implementations:

ExpertInterviewSource
IncidentSource
HandoverDocumentSource
OutcomeSource
ArchitectureChangeSource

This makes the prototype production-extensible.

============================================================
EXPERT CAPTURE UI
============================================================

Build:

CAPTURE EXPERIENCE

Heading:

"Capture what never made it into the documentation."

Conversation prompts:

"What system do you know well?"

"What usually goes wrong?"

"What should a new engineer NOT do?"

"What do you check first?"

"When should someone escalate?"

"Who normally handles it?"

"What workaround have you used?"

"Why does that workaround exist?"

"Tell me about a time the normal procedure failed."

The user can answer naturally.

Do not force a giant form.

Use conversational capture.

After capture:

Hindsight Processing

Show extracted memory cards:

EXPERIENCE
LESSON
EXCEPTION
RELATIONSHIP
FACT

Allow:

[ Review ]
[ Approve ]
[ Reject ]
[ Promote to Team ]
[ Promote to Organization ]

============================================================
HANDOVER VIEW
============================================================

Create:

KNOWLEDGE CONTINUITY

Employee:

Arun

Role:

Senior DevOps Engineer

Knowledge captured:

11

Validated:

8

Pending review:

2

Stale:

1

Single-person dependencies:

14 → 3

IMPORTANT:

These are synthetic demo numbers.

Clearly label:

"Synthetic prototype metric"

Do not present them as real enterprise statistics.

============================================================
KNOWLEDGE RISK
============================================================

Create a view:

KNOWLEDGE AT RISK

Rows:

Payment Platform
Owner: Arun
Risk: High
Knowledge: 14 items
Validated: 8
Replacement coverage: Partial

Identity Platform
Owner: Priya

Network Operations
Owner: Ravi

The UI should communicate:

"Which critical knowledge still depends on one person?"

============================================================
MAIN DASHBOARD
============================================================

The first screen must feel like an enterprise product.

Not a student dashboard.

Not a generic AI dashboard.

Not purple robot graphics.

Use:

- light neutral background
- white cards
- dark navy text
- restrained blue/green accent
- subtle borders
- strong typography
- generous spacing
- professional enterprise design
- responsive layout
- polished empty states
- loading states
- error states
- tooltips where necessary

Use a consistent design system.

============================================================
HERO DASHBOARD
============================================================

Header:

MemoryOS

Knowledge Continuity

Top statement:

"Your organization has a memory."

Metrics:

Critical knowledge dependencies
Captured knowledge
Validated memories
Stale memories
Contradictions
Recent learning events

Recent Intelligence:

"An operational lesson was strengthened by a new incident."

"One historical assumption became outdated."

"One expert lesson was promoted to organizational knowledge."

"One successor resolved an incident using historical experience."

============================================================
NAVIGATION
============================================================

Use:

Overview
Capture Experience
Memory Center
Ask MemoryOS
Knowledge Risk
Memory Evolution
Evidence
Governance
Audit

Do NOT create ten fake modules.

Only expose working functionality.

If a future module is shown, label it:

"Coming later"

============================================================
MEMORY CENTER
============================================================

Create a searchable memory explorer.

Filters:

Memory type
Scope
Source
Status
Confidence
Date
Entity
System

Each memory card shows:

Title
Type
Summary
Source
Scope
Evidence count
Confidence
Last validated
Status

Actions:

View
Why used
Evidence
History
Validate
Restrict
Expire

============================================================
MEMORY TIMELINE
============================================================

For Payment Platform show:

INC-1042
↓
Expert lesson captured
↓
INC-1088
↓
INC-1104
↓
Successor recommendation
↓
Outcome
↓
Payment Queue v2
↓
Potential contradiction
↓
Memory scope updated

This is one of the strongest visual demonstrations.

============================================================
MEMORY GRAPH
============================================================

Create a small interactive graph.

Nodes:

Arun
Payment API
Payment Queue v1
INC-1042
INC-1088
INC-1104
Payments Operations
Operational Lesson

Relationships:

Arun → knows → Payment API

Payment API → depends_on → Payment Queue v1

INC-1042 → demonstrates → failure

INC-1088 → supports → lesson

INC-1104 → supports → lesson

Lesson → escalates_to → Payments Operations

The graph should be generated from application data.

Do not build a complicated graph database.

A lightweight UI graph is enough.

============================================================
ASK MEMORYOS
============================================================

This is the central interaction.

Layout:

LEFT:

Conversation

RIGHT:

Memory Lens

When the agent answers, display:

ANSWER

Historical Evidence

Memories Used

Current Context

Potential Conflicts

Confidence

Scope

Then:

[ WHY DID YOU SAY THIS? ]

============================================================
ANSWER FORMAT
============================================================

The agent must distinguish:

DOCUMENTED FACT

HISTORICAL EXPERIENCE

CURRENT EVIDENCE

INFERENCE

RECOMMENDATION

Example:

FACT:
Payment Queue v1 is the queue used by Payment API.

HISTORICAL EXPERIENCE:
Three incidents show problems after immediate restart during saturation.

CURRENT EVIDENCE:
Current queue depth is 87%.

RECOMMENDATION:
Check with Payments Operations before restarting.

Do not present inference as fact.

============================================================
PRIVACY DEMO
============================================================

Implement a small permissions demonstration.

Create:

Arun private memory:

"Arun prefers to work early mornings."

This should NOT be retrievable as organizational operational knowledge.

Then create:

Arun organizational memory:

"Arun documented that Payment Queue v1 requires escalation to Payments Operations above 80%."

This can be retrieved by authorized successors.

Demonstrate:

PRIVATE MEMORY
→ ACCESS DENIED

ORGANIZATIONAL MEMORY
→ ACCESS GRANTED

This demonstrates that organizational memory is not simply employee surveillance.

============================================================
AUDIT
============================================================

Create an audit page.

Events:

Memory captured
Memory reviewed
Memory promoted
Memory retrieved
Memory used by agent
Outcome recorded
Memory contradicted
Memory updated
Memory restricted
Memory expired

Example:

09:42
Memory M-1042 retrieved

09:43
Used by Successor Agent

09:49
Outcome recorded

10:01
Architecture change detected

10:02
Memory scope restricted

============================================================
DEMO METRICS
============================================================

Track actual application events.

Metrics:

memories_created
memories_retrieved
memories_used
outcomes_recorded
contradictions_detected
memories_updated
memories_revalidated
knowledge_dependencies

Do not fabricate runtime metrics.

If synthetic baseline numbers are shown, label them as synthetic.

============================================================
LEARNING CURVE
============================================================

Create a simple visualization.

Test the same type of question at:

0 memories
1 memory
3 memories
5 memories
10 memories

Measure application-defined metrics such as:

Evidence coverage
Relevant memory retrieval
Correct historical context
Outcome-supported recommendations

Do NOT claim these are scientific benchmarks.

Label:

"Prototype learning evaluation"

The key visual:

BEFORE MEMORY

Generic recommendation

AFTER EXPERIENCE

Evidence-backed contextual recommendation

AFTER MORE EXPERIENCE

Context-aware recommendation + historical evidence + outcome

============================================================
IMPORTANT HINDSIGHT USAGE
============================================================

Hindsight must be used in meaningful places.

Use:

RETAIN

when durable experience, incident outcomes, expert lessons, decisions, or architecture changes are learned.

Use:

RECALL

when the application needs relevant raw memories/evidence.

Use:

REFLECT

when the application needs Hindsight to reason across accumulated experience.

Do NOT call reflect for every trivial request.

Use recall for evidence retrieval.

Use reflect for nuanced synthesis.

The UI should make this visible in developer/demo mode.

============================================================
HINDSIGHT TRACE
============================================================

Create a developer/demo drawer:

HINDSIGHT TRACE

Question
↓
Recall
↓
Memories found
↓
Relevant evidence
↓
Reflect
↓
Response

Show:

Recall latency
Number of memories considered
Memory IDs
Fact types
Evidence count

Do not expose secrets/API keys.

============================================================
SOURCE PROVENANCE
============================================================

Every important memory should have:

source_type
source_id
source_name
captured_at
observed_at

Examples:

source_type:
expert_interview

source_id:
expert-arun-payment

source_type:
incident

source_id:
INC-1088

source_type:
architecture_change

source_id:
ARCH-2026-09-28

============================================================
TECH STACK
============================================================

Use a simple, maintainable architecture.

Recommended:

Frontend:
React + TypeScript

Styling:
Tailwind CSS

Icons:
Lucide

Charts:
Recharts

Backend:
Python

API:
FastAPI

Validation:
Pydantic

Memory:
Hindsight

Database:
SQLite for application metadata/audit/demo state

Do NOT create a second vector database.

Hindsight is the memory engine.

SQLite stores application metadata, permissions, audit events, UI state, and references.

============================================================
ARCHITECTURE
============================================================

Frontend
    ↓
FastAPI
    ↓
MemoryOS Agent Orchestrator
    ↓
Memory Gate
    ↓
Hindsight
    ↓
Application Metadata / Audit DB

Sources:

Expert Interview
Incident Records
Handover Documents
Outcome Feedback
Architecture Changes

All source adapters eventually feed:

Memory Ingestion Service

============================================================
BACKEND MODULES
============================================================

Create clean modules:

backend/
    main.py
    config.py

    api/
        capture.py
        ask.py
        outcomes.py
        memories.py
        governance.py
        audit.py
        demo.py

    memory/
        hindsight_client.py
        ingestion.py
        retrieval.py
        reflection.py
        confidence.py
        contradiction.py
        lifecycle.py
        provenance.py

    agents/
        successor_agent.py

    sources/
        base.py
        expert_interview.py
        incidents.py
        handover.py
        outcomes.py
        architecture.py

    models/
        memory.py
        audit.py
        permissions.py

    db/
        database.py

============================================================
FRONTEND MODULES
============================================================

Create:

frontend/

components/
    Dashboard
    MemoryCard
    MemoryLens
    EvidencePanel
    ConfidenceBadge
    Timeline
    KnowledgeRisk
    CaptureConversation
    AskMemoryOS
    HindsightTrace
    ContradictionPanel
    GovernancePanel
    AuditTimeline

pages/
    Overview
    Capture
    MemoryCenter
    Ask
    KnowledgeRisk
    Evolution
    Governance
    Audit

============================================================
API
============================================================

Implement at minimum:

GET /api/health

POST /api/demo/seed

POST /api/capture

POST /api/ask

POST /api/outcome

POST /api/architecture-change

GET /api/memories

GET /api/memories/{id}

GET /api/memories/{id}/history

GET /api/memories/{id}/evidence

POST /api/memories/{id}/validate

POST /api/memories/{id}/restrict

POST /api/memories/{id}/expire

GET /api/audit

GET /api/dashboard

============================================================
DEMO CONTROLS
============================================================

Add a visible:

DEMO MODE

button.

Demo Mode provides:

[ 1. Seed Arun's Knowledge ]

[ 2. Ask as Maya ]

[ 3. Record Successful Outcome ]

[ 4. Introduce Queue v2 ]

[ 5. Ask Same Question Again ]

[ 6. Show Memory Evolution ]

[ 7. Show Privacy Boundary ]

[ 8. Reset Demo ]

Each button must actually execute the underlying functionality.

No fake buttons.

============================================================
ONE-CLICK DEMO
============================================================

Also provide:

[ RUN FULL DEMO ]

It should sequentially:

1. Reset demo
2. Seed incidents
3. Capture Arun lesson
4. Ask question without accumulated memory
5. Show baseline
6. Add expert memory
7. Ask again
8. Show evidence-backed response
9. Record outcome
10. Add architecture change
11. Ask again
12. Detect stale/contradictory knowledge
13. Update memory scope
14. Show final dashboard

Do not make the UI wait unnecessarily.

Show progress.

============================================================
BEFORE / AFTER
============================================================

Create a dedicated comparison.

BEFORE MEMORYOS

Question:
"Payment API has connection resets."

Answer:
Generic troubleshooting.

AFTER MEMORYOS

Answer:
Uses historical organizational experience.

Show:

Evidence
Experience
Outcome
Scope
Confidence

This is essential for the presentation.

============================================================
VISUAL DESIGN
============================================================

Design for a major enterprise technology competition.

The UI should feel closer to:

enterprise operations console
+
modern AI reasoning interface
+
knowledge intelligence system

Avoid:

- cartoon robots
- excessive gradients
- purple AI clichés
- giant "AI" text
- fake futuristic dashboards
- unnecessary animations
- stock images

Use:

- strong typography
- subtle motion
- clean cards
- timeline
- evidence visualization
- memory graph
- status indicators
- excellent spacing
- polished responsive layout

Use dark text on light backgrounds by default.

============================================================
MOBILE / RESPONSIVE
============================================================

The primary demo is desktop.

But the interface must remain usable on tablet/mobile.

============================================================
ERROR HANDLING
============================================================

Implement:

Hindsight unavailable
LLM unavailable
invalid input
permission denied
memory not found
contradiction detected
stale memory
timeout
rate limit

The UI must explain errors clearly.

============================================================
SECURITY
============================================================

Never expose:

API keys
credentials
environment secrets
tokens

Use environment variables.

Do not hard-code API keys.

Validate authorization before memory retrieval.

Never retrieve personal memories through organization queries.

============================================================
TESTS
============================================================

Create tests for:

1. Hindsight client initialization
2. Capture
3. Recall
4. Reflect
5. Outcome retention
6. Permission boundary
7. Memory scope
8. Contradiction detection
9. Staleness
10. Audit logging
11. Demo seed
12. API health

Mock Hindsight in unit tests.

Provide at least one integration test that can run when Hindsight is configured.

============================================================
SYNTHETIC DATA
============================================================

Create realistic but fictional data.

Include:

NovaTech

Employees:
Arun
Maya
Priya
Ravi

Systems:
Payment Platform
Identity Platform
Network Platform

Teams:
Payments Operations
Identity Operations
Network Operations

Incidents:
at least 10

Expert lessons:
at least 8

Architecture changes:
at least 3

Use the Payment Platform story as the primary demo.

Other data exists to make the Memory Center feel real.

============================================================
DO NOT OVERBUILD
============================================================

This is critical.

Do NOT implement:

healthcare
retail
customer CRM
negotiation
marketplace
sales
procurement
complex enterprise SSO
real ServiceNow integration
real Jira integration
real Teams integration
real email ingestion
real employee surveillance
complex graph database
Kubernetes deployment
microservices
multi-region infrastructure
billing
real enterprise identity management

Those are future roadmap items.

The hackathon prototype must remain focused.

============================================================
FUTURE EXTENSIBILITY
============================================================

Although the demo is narrow, architecture should allow future domains.

Create interfaces:

MemorySource
MemoryPolicy
MemoryScope
MemoryAgent
MemoryResolver

Do not hard-code the entire product around Payment API.

============================================================
PRODUCT ROADMAP SCREEN
============================================================

Optional small section:

NEXT:

Company Memory
Crisis Memory
Decision Memory
Customer Memory
Negotiation Memory

But label:

"Future platform modules"

Do not implement them.

============================================================
README
============================================================

Create a comprehensive README containing:

1. Product overview
2. Problem
3. Why this is different from RAG
4. Architecture
5. Hindsight integration
6. Memory lifecycle
7. Data model
8. Permission model
9. Confidence model
10. Contradiction handling
11. Local setup
12. Environment variables
13. Hindsight setup
14. Running frontend
15. Running backend
16. Seeding demo data
17. Running tests
18. Demo script
19. Known limitations
20. Future production architecture

============================================================
DEMO SCRIPT
============================================================

The application should support this exact presentation story.

0–5 seconds:

Dashboard.

Say:

"Companies don't only lose employees.
They lose what those employees learned."

5–15 seconds:

Show Arun's experience capture.

Say:

"This wasn't in the runbook."

15–25 seconds:

Show Hindsight processing.

Say:

"MemoryOS turns experience into organizational memory."

25–40 seconds:

Maya asks the incident question.

Show:

DON'T RESTART YET

Then open:

WHY DID YOU SAY THIS?

Show the three historical incidents.

40–50 seconds:

Record successful outcome.

Say:

"Now the system has another observation."

50–60 seconds:

Introduce Payment Queue v2.

Ask the same question.

Show:

"Historical knowledge may be outdated."

Then show:

Memory Evolution.

Closing:

"We don't copy someone's brain.
We preserve what the organization would otherwise have to learn again."

============================================================
WHAT MAKES THIS STAND OUT
============================================================

The product should visually demonstrate five things competitors may overlook:

1. MEMORY IS NOT DOCUMENT SEARCH

The system remembers experience.

2. NEGATIVE KNOWLEDGE

It remembers what NOT to do.

3. MEMORY HAS SCOPE

Queue v1 knowledge should not automatically apply to Queue v2.

4. MEMORY CAN BECOME WRONG

New evidence can invalidate old assumptions.

5. MEMORY HAS PROVENANCE

The agent can explain why it knows something.

The key experience:

AI doesn't just say:

"I remember."

It says:

"I remember this because the organization experienced it three times, here is the evidence, here is the scope, and here is why I'm not blindly applying it now."

============================================================
JUDGING ALIGNMENT
============================================================

Optimize the prototype around these categories:

INNOVATION

Show a new concept:
organizational experiential memory.

HINDSIGHT MEMORY

Hindsight must visibly power:
retain
recall
reflect
evidence
experience
memory evolution

TECHNICAL

Real working backend.
Real Hindsight.
Real data flow.
Real audit.
Real permission boundary.
Real contradiction handling.

UX

Make the memory visible.

The user should understand:

what the AI remembers
why it remembered
why it used it
what evidence supports it
whether it is still valid

REAL-WORLD IMPACT

Show the cost of losing operational knowledge.

The product should answer:

"What happens if Arun leaves tomorrow?"

Answer:

"The organization does not lose the experience that has been captured, validated, and promoted into organizational memory."

============================================================
IMPORTANT PRODUCT PRINCIPLE
============================================================

Do not call this:

"AI employee replacement."

Do not create an avatar of Arun.

Do not simulate Arun after he leaves.

Do not attempt to recreate a person's personality.

We are preserving:

organizationally useful experience.

This distinction is important for trust, privacy and enterprise adoption.

============================================================
FINAL QUALITY BAR
============================================================

Before declaring the project complete:

Run the application.

Run the tests.

Verify Hindsight connection.

Seed the data.

Verify retain.

Verify recall.

Verify reflect.

Verify outcome retention.

Verify contradiction flow.

Verify permission boundary.

Verify audit.

Verify UI.

Verify mobile responsiveness.

Fix runtime errors.

Do not leave broken imports.

Do not leave TODOs for core features.

Do not use fake API responses where Hindsight should be called.

Do not use static answers for the main demo.

Do not claim functionality that is not implemented.

If something must be simulated, visibly label it:

"SIMULATED"

============================================================
FINAL OUTPUT FROM YOU
============================================================

After building, report:

1. Files created
2. Architecture
3. How to install
4. Environment variables required
5. How to start Hindsight
6. How to start backend
7. How to start frontend
8. How to seed demo
9. Exact demo steps
10. Tests run
11. Any remaining limitations

Do not stop at explaining.

BUILD IT.