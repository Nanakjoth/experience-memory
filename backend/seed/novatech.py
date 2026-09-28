"""SYNTHETIC DEMO DATA for NovaTech.

Every person, system, team, incident, date and measurement in this file is
fictional. Nothing here is a real company, a real employee or a real customer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SYNTHETIC_BANNER = "SYNTHETIC DEMO DATA"

COMPANY = {
    "name": "NovaTech",
    "description": "Synthetic mid-size fintech platform company used for the MemoryOS demo.",
    "systems": [
        {
            "id": "sys-payment",
            "name": "Payment Platform",
            "owner": "Arun",
            "team": "Payments Operations",
            "domain": "payments",
            "criticality": "critical",
            "components": ["Payment API", "Payment Queue v1", "Payment Queue v2"],
            "active_component": "Payment Queue v1",
            "dependency_depth": 3,
        },
        {
            "id": "sys-identity",
            "name": "Identity Platform",
            "owner": "Priya",
            "team": "Identity Operations",
            "domain": "identity",
            "criticality": "high",
            "components": ["Auth Gateway", "Session Store", "Token Service"],
            "active_component": "Auth Gateway",
            "dependency_depth": 2,
        },
        {
            "id": "sys-network",
            "name": "Network Platform",
            "owner": "Ravi",
            "team": "Network Operations",
            "domain": "network",
            "criticality": "high",
            "components": ["Edge Router", "Transit Fabric", "DNS Resolver"],
            "active_component": "Edge Router",
            "dependency_depth": 2,
        },
    ],
    "employees": [
        {
            "id": "emp-arun",
            "name": "Arun",
            "role": "Senior DevOps Engineer",
            "team": "Payments Operations",
            "systems": ["sys-payment"],
            "status": "unavailable",
            "note": "Single owner of Payment Platform operational knowledge. Long-term absence.",
        },
        {
            "id": "emp-maya",
            "name": "Maya",
            "role": "New DevOps Engineer",
            "team": "Payments Operations",
            "systems": ["sys-payment"],
            "status": "active",
            "note": "Successor. Joined three weeks ago.",
        },
        {
            "id": "emp-priya",
            "name": "Priya",
            "role": "Staff Identity Engineer",
            "team": "Identity Operations",
            "systems": ["sys-identity"],
            "status": "active",
            "note": "Sole documented owner of the Session Store.",
        },
        {
            "id": "emp-ravi",
            "name": "Ravi",
            "role": "Network Reliability Engineer",
            "team": "Network Operations",
            "systems": ["sys-network"],
            "status": "active",
            "note": "Holds undocumented knowledge of the transit fabric.",
        },
    ],
    "teams": [
        {
            "id": "team-payments-ops",
            "name": "Payments Operations",
            "members": ["Arun", "Maya"],
            "owns": "Payment Platform escalation",
        },
        {
            "id": "team-identity-ops",
            "name": "Identity Operations",
            "members": ["Priya"],
            "owns": "Identity Platform escalation",
        },
        {
            "id": "team-network-ops",
            "name": "Network Operations",
            "members": ["Ravi"],
            "owns": "Network Platform escalation",
        },
    ],
}


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


INCIDENTS: list[dict[str, Any]] = [
    # --- the three that carry the hero story -----------------------------
    {
        "id": "INC-1042",
        "title": "Payment API connection resets during queue saturation",
        "system": "Payment Platform",
        "service": "Payment API",
        "component": "Payment Queue v1",
        "severity": "SEV-2",
        "status": "resolved",
        "opened_at": "2026-03-14T08:12:00Z",
        "resolved_at": "2026-03-14T10:41:00Z",
        "engineer": "Arun",
        "queue_depth": 91,
        "action": "Restarted Payment API immediately without checking queue depth",
        "outcome": "Duplicate payment processing for 1,204 transactions; manual reversal required",
        "duplicate_processing": True,
        "narrative": (
            "INC-1042. Payment API began emitting connection-reset alerts at 08:12 UTC. "
            "The documented runbook says to restart the Payment API. The on-call engineer "
            "followed the runbook and restarted the service at 08:19 UTC without checking "
            "Payment Queue v1 depth. At that moment the queue was at 91 percent. In-flight "
            "messages were redelivered after the restart and 1,204 payments were processed "
            "twice. The incident ran 2 hours 29 minutes and required a manual reversal "
            "batch. Root cause was queue saturation, not the Payment API process itself. "
            "Arun identified the real cause during the postmortem."
        ),
        "metrics": {
            "queue_depth_pct": 91,
            "duplicate_transactions": 1204,
            "mttr_minutes": 149,
            "restart_attempted": True,
        },
    },
    {
        "id": "INC-1088",
        "title": "Payment API connection resets, resolved without restart",
        "system": "Payment Platform",
        "service": "Payment API",
        "component": "Payment Queue v1",
        "severity": "SEV-3",
        "status": "resolved",
        "opened_at": "2026-05-02T13:26:00Z",
        "resolved_at": "2026-05-02T14:08:00Z",
        "engineer": "Arun",
        "queue_depth": 87,
        "action": "Checked queue depth, contacted Payments Operations, did not restart",
        "outcome": "Resolved without duplicate processing; queue drained in 6 minutes",
        "duplicate_processing": False,
        "narrative": (
            "INC-1088. Payment API emitted connection-reset alerts at 13:26 UTC. Because of "
            "INC-1042 the on-call engineer checked Payment Queue v1 depth first and found it "
            "at 87 percent, above the escalation threshold. Payments Operations was paged and "
            "confirmed that the queue was draining normally under a settlement batch. The "
            "Payment API was deliberately NOT restarted. Alerts cleared at 14:08 UTC when the "
            "queue drained. No duplicate processing occurred. The postmortem recorded that "
            "the documented restart step was unnecessary."
        ),
        "metrics": {
            "queue_depth_pct": 87,
            "duplicate_transactions": 0,
            "mttr_minutes": 42,
            "restart_attempted": False,
        },
    },
    {
        "id": "INC-1104",
        "title": "Payment API resets during settlement batch, no restart required",
        "system": "Payment Platform",
        "service": "Payment API",
        "component": "Payment Queue v1",
        "severity": "SEV-3",
        "status": "resolved",
        "opened_at": "2026-06-21T19:40:00Z",
        "resolved_at": "2026-06-21T20:22:00Z",
        "engineer": "Arun",
        "queue_depth": 84,
        "action": "Checked queue, followed the Payments Operations procedure, did not restart",
        "outcome": "Resolved without restart; no customer impact",
        "duplicate_processing": False,
        "narrative": (
            "INC-1104. Connection-reset alerts on the Payment API during the nightly "
            "settlement batch. Payment Queue v1 depth was 84 percent. The engineer followed "
            "the documented Payments Operations procedure for queue-related saturation, "
            "which is to allow the batch to drain and to hold the restart. Alerts cleared at "
            "20:22 UTC. This is the third consecutive incident in which restarting would "
            "have been harmful and waiting was correct."
        ),
        "metrics": {
            "queue_depth_pct": 84,
            "duplicate_transactions": 0,
            "mttr_minutes": 42,
            "restart_attempted": False,
        },
    },
    # --- supporting Payment Platform incidents ---------------------------
    {
        "id": "INC-1012",
        "title": "Payment API elevated latency from session store timeouts",
        "system": "Payment Platform",
        "service": "Payment API",
        "component": "Auth Gateway",
        "severity": "SEV-3",
        "status": "resolved",
        "opened_at": "2026-01-22T11:05:00Z",
        "resolved_at": "2026-01-22T12:30:00Z",
        "engineer": "Arun",
        "queue_depth": 12,
        "action": "Traced to Identity Platform session store, raised ticket with Priya",
        "outcome": "Root cause in Session Store eviction policy; fixed by Identity Operations",
        "duplicate_processing": False,
        "narrative": (
            "INC-1012. Payment API latency rose to 4.2 seconds p99. Queue depth was normal at "
            "12 percent, so the Payment Platform was not the cause. Tracing showed session "
            "validation calls to the Identity Platform timing out. Priya's team found an "
            "eviction policy change in the Session Store. This is the clearest example of a "
            "Payment Platform symptom with an Identity Platform root cause, and it is why "
            "restarting the Payment API would not have helped."
        ),
        "metrics": {"queue_depth_pct": 12, "p99_latency_ms": 4200, "restart_attempted": False},
    },
    {
        "id": "INC-1055",
        "title": "Payment Queue v1 consumer lag after consumer scale-out",
        "system": "Payment Platform",
        "service": "Payment Queue v1",
        "component": "Payment Queue v1",
        "severity": "SEV-3",
        "status": "resolved",
        "opened_at": "2026-04-02T07:55:00Z",
        "resolved_at": "2026-04-02T09:12:00Z",
        "engineer": "Arun",
        "queue_depth": 78,
        "action": "Reverted the consumer scale-out, restored previous consumer count",
        "outcome": "Lag cleared; scale-out was the cause",
        "duplicate_processing": False,
        "narrative": (
            "INC-1055. After scaling Payment Queue v1 consumers from 8 to 16, consumer lag "
            "rose sharply while queue depth stayed at 78 percent. The scale-out caused "
            "redelivery storms. Reverting to 8 consumers cleared the lag in 77 minutes. "
            "The takeaway is that consumer count on Payment Queue v1 is load-bearing and "
            "must not be raised during settlement windows."
        ),
        "metrics": {"queue_depth_pct": 78, "consumer_lag_messages": 412000, "restart_attempted": False},
    },
    {
        "id": "INC-1067",
        "title": "Duplicate webhook delivery from manual replay",
        "system": "Payment Platform",
        "service": "Payment Webhook Dispatcher",
        "component": "Payment Queue v1",
        "severity": "SEV-2",
        "status": "resolved",
        "opened_at": "2026-04-18T15:33:00Z",
        "resolved_at": "2026-04-18T16:47:00Z",
        "engineer": "Arun",
        "queue_depth": 66,
        "action": "Stopped replay, drained the queue, replayed with idempotency keys",
        "outcome": "Duplicate webhooks resolved via idempotency key replay",
        "duplicate_processing": True,
        "narrative": (
            "INC-1067. An operator replayed the Payment Queue v1 dead-letter queue without "
            "regenerating idempotency keys, producing 318 duplicate webhooks to merchants. "
            "Recovery required stopping the replay, draining the live queue, then replaying "
            "with regenerated idempotency keys. This is a workaround that exists only in "
            "Arun's head and is not in any runbook."
        ),
        "metrics": {"queue_depth_pct": 66, "duplicate_webhooks": 318, "restart_attempted": False},
    },
    {
        "id": "INC-1093",
        "title": "Payment API timeouts behind edge router change",
        "system": "Payment Platform",
        "service": "Payment API",
        "component": "Edge Router",
        "severity": "SEV-3",
        "status": "resolved",
        "opened_at": "2026-05-19T09:14:00Z",
        "resolved_at": "2026-05-19T10:02:00Z",
        "engineer": "Ravi",
        "queue_depth": 22,
        "action": "Reverted edge router keepalive setting, coordinated with Network Operations",
        "outcome": "Timeouts cleared; edge change was the cause",
        "duplicate_processing": False,
        "narrative": (
            "INC-1093. Payment API timeouts traced to a keepalive reduction on the Edge "
            "Router applied by the Network Platform team two days earlier. Queue depth was "
            "normal. Network Operations reverted the keepalive. Shows cross-platform "
            "dependencies that no single runbook covers."
        ),
        "metrics": {"queue_depth_pct": 22, "timeout_rate_pct": 6.4, "restart_attempted": False},
    },
    {
        "id": "INC-1111",
        "title": "Queue drain stalled by settlement retry storm",
        "system": "Payment Platform",
        "service": "Payment Queue v1",
        "component": "Payment Queue v1",
        "severity": "SEV-2",
        "status": "resolved",
        "opened_at": "2026-07-08T02:14:00Z",
        "resolved_at": "2026-07-08T04:36:00Z",
        "engineer": "Arun",
        "queue_depth": 93,
        "action": "Disabled the retry worker, waited for depth to fall below 80, re-enabled",
        "outcome": "Drain resumed; avoided the INC-1042 failure mode",
        "duplicate_processing": False,
        "narrative": (
            "INC-1111. A settlement partner returned errors causing a retry storm in Payment "
            "Queue v1, pushing depth to 93 percent and stalling the drain. The documented "
            "procedure was followed exactly: the retry worker was disabled, depth was allowed "
            "to fall below 80 percent, then the worker was re-enabled. Depth fell to 74 "
            "percent in 2 hours 9 minutes. Critically, the Payment API was never restarted, "
            "which avoided repeating INC-1042."
        ),
        "metrics": {"queue_depth_pct": 93, "peak_depth_pct": 93, "mttr_minutes": 142, "restart_attempted": False},
    },
    {
        "id": "INC-1120",
        "title": "Settlement batch timeout, upstream partner slow",
        "system": "Payment Platform",
        "service": "Settlement Worker",
        "component": "Payment Queue v1",
        "severity": "SEV-3",
        "status": "resolved",
        "opened_at": "2026-07-29T22:03:00Z",
        "resolved_at": "2026-07-30T00:11:00Z",
        "engineer": "Maya",
        "queue_depth": 71,
        "action": "Waited for upstream partner, no service restart",
        "outcome": "Batch completed once the partner recovered; Maya's first incident",
        "duplicate_processing": False,
        "narrative": (
            "INC-1120. The settlement worker timed out against an upstream banking partner. "
            "Queue depth peaked at 71 percent. Maya, in her first weeks, checked queue depth "
            "before acting, did not restart the service, and escalated to Payments "
            "Operations. The batch completed when the partner recovered. Recorded here as "
            "the first time a successor followed organizational memory successfully."
        ),
        "metrics": {"queue_depth_pct": 71, "mttr_minutes": 128, "restart_attempted": False},
    },
    # --- other platforms, so Memory Center feels real --------------------
    {
        "id": "INC-2014",
        "title": "Auth Gateway token validation failures",
        "system": "Identity Platform",
        "service": "Auth Gateway",
        "component": "Token Service",
        "severity": "SEV-2",
        "status": "resolved",
        "opened_at": "2026-02-11T06:40:00Z",
        "resolved_at": "2026-02-11T08:15:00Z",
        "engineer": "Priya",
        "queue_depth": None,
        "action": "Rolled back the token key rotation",
        "outcome": "Validation restored; key rotation rolled back",
        "duplicate_processing": False,
        "narrative": (
            "INC-2014. Auth Gateway rejected tokens after a key rotation because the "
            "secondary verification key was not propagated. Priya rolled back the rotation. "
            "Key rotations on the Token Service must be verified against the secondary "
            "verification slot before the primary is replaced."
        ),
        "metrics": {"error_rate_pct": 41.0},
    },
    {
        "id": "INC-2031",
        "title": "Session Store eviction storm",
        "system": "Identity Platform",
        "service": "Session Store",
        "component": "Session Store",
        "severity": "SEV-3",
        "status": "resolved",
        "opened_at": "2026-05-30T18:22:00Z",
        "resolved_at": "2026-05-30T19:50:00Z",
        "engineer": "Priya",
        "queue_depth": None,
        "action": "Restored the previous eviction policy",
        "outcome": "Eviction returned to baseline",
        "duplicate_processing": False,
        "narrative": (
            "INC-2031. A change to the Session Store eviction policy caused mass session "
            "eviction and downstream login failures. Priya restored the previous policy. "
            "This was the root cause behind INC-1012 on the Payment Platform."
        ),
        "metrics": {"evicted_sessions": 91200},
    },
    {
        "id": "INC-3022",
        "title": "Transit fabric packet loss under failover",
        "system": "Network Platform",
        "service": "Transit Fabric",
        "component": "Transit Fabric",
        "severity": "SEV-2",
        "status": "resolved",
        "opened_at": "2026-04-29T03:18:00Z",
        "resolved_at": "2026-04-29T05:44:00Z",
        "engineer": "Ravi",
        "queue_depth": None,
        "action": "Failed back to the primary path after confirming the backup was clean",
        "outcome": "Packet loss cleared; failover had left stale routes",
        "duplicate_processing": False,
        "narrative": (
            "INC-3022. A transit fabric failover left stale routes on the backup path, "
            "causing 3.8 percent packet loss. Ravi failed back to the primary path only "
            "after confirming the backup path was clean. Failover on the transit fabric "
            "must be verified route-by-route before failing back."
        ),
        "metrics": {"packet_loss_pct": 3.8},
    },
    {
        "id": "INC-3040",
        "title": "DNS resolver cache poisoning warning",
        "system": "Network Platform",
        "service": "DNS Resolver",
        "component": "DNS Resolver",
        "severity": "SEV-1",
        "status": "resolved",
        "opened_at": "2026-06-12T21:05:00Z",
        "resolved_at": "2026-06-12T21:29:00Z",
        "engineer": "Ravi",
        "queue_depth": None,
        "action": "Flushed resolver cache and rotated the upstream resolver",
        "outcome": "Spoofed records removed",
        "duplicate_processing": False,
        "narrative": (
            "INC-3040. The DNS Resolver served spoofed records for a partner domain. Ravi "
            "flushed the cache, rotated the upstream resolver and notified the partner. "
            "Upstream resolver rotation is not documented in the Network runbook."
        ),
        "metrics": {"spoofed_records": 12},
    },
]


EXPERT_INTERVIEWS: list[dict[str, Any]] = [
    {
        "id": "expert-arun-payment",
        "expert": "Arun",
        "role": "Senior DevOps Engineer",
        "team": "Payments Operations",
        "captured_at": "2026-08-04T09:00:00Z",
        "scope": "Payment Queue v1",
        "system": "Payment Platform",
        "title": "Arun — Payment API operational interview",
        "transcript": [
            (
                "MemoryOS",
                "What system do you know well?",
            ),
            (
                "Arun",
                "The Payment API on the Payment Platform, and the Payment Queue v1 that sits "
                "behind it. I have run that queue through two settlement redesigns.",
            ),
            (
                "MemoryOS",
                "What usually goes wrong?",
            ),
            (
                "Arun",
                "Connection-reset alerts on the Payment API. Almost every time it looks like "
                "the API needs a restart. It usually does not. It is the queue behind it "
                "backing up.",
            ),
            (
                "MemoryOS",
                "What should a new engineer NOT do?",
            ),
            (
                "Arun",
                "Do not restart the Payment API immediately when you see connection-reset "
                "alerts. If the Payment Queue v1 depth is above 80 percent, a restart causes "
                "duplicate payment processing. We did it in INC-1042 at 91 percent and it "
                "processed 1,204 payments twice. That is the single most expensive mistake "
                "on this platform.",
            ),
            (
                "MemoryOS",
                "What do you check first?",
            ),
            (
                "Arun",
                "Payment Queue v1 depth. Always first. The number decides everything. Above "
                "80 percent you escalate, below 80 percent you look at the API itself.",
            ),
            (
                "MemoryOS",
                "When should someone escalate?",
            ),
            (
                "Arun",
                "When queue depth is above 80 percent, contact Payments Operations before "
                "restarting anything. They own the settlement batches and they know whether "
                "the depth is a batch that will drain on its own.",
            ),
            (
                "MemoryOS",
                "Who normally handles it?",
            ),
            (
                "Arun",
                "Payments Operations. They hold the settlement schedule. Escalate to the "
                "Payments Operations on-call, not to me.",
            ),
            (
                "MemoryOS",
                "What workaround have you used?",
            ),
            (
                "Arun",
                "When the queue is saturated and a settlement partner is erroring, I disable "
                "the retry worker and let the depth fall below 80 percent before re-enabling "
                "it. It is in INC-1111. Never disable the retry worker if the partner is "
                "healthy, because you will stall the drain instead.",
            ),
            (
                "MemoryOS",
                "Why does that workaround exist?",
            ),
            (
                "Arun",
                "Because the retry worker keeps re-enqueueing and the queue never drains "
                "while the API keeps resetting. The workaround exists to break the loop, not "
                "to fix anything.",
            ),
            (
                "MemoryOS",
                "Tell me about a time the normal procedure failed.",
            ),
            (
                "Arun",
                "INC-1042. The runbook says restart. I followed it. Queue was at 91 percent. "
                "We duplicated 1,204 payments. The lesson is in the lesson, not in the runbook, "
                "and the runbook has never been updated because it is owned by a different team.",
            ),
            (
                "MemoryOS",
                "Does this apply everywhere?",
            ),
            (
                "Arun",
                "This procedure applies to Payment Queue v1. It does not automatically apply "
                "to any other queue version. The threshold is a property of the v1 consumer "
                "count, which is 8.",
            ),
        ],
    },
    {
        "id": "expert-priya-identity",
        "expert": "Priya",
        "role": "Staff Identity Engineer",
        "team": "Identity Operations",
        "captured_at": "2026-08-05T10:30:00Z",
        "scope": "Token Service",
        "system": "Identity Platform",
        "title": "Priya — Identity Platform operational interview",
        "transcript": [
            ("MemoryOS", "What usually goes wrong?"),
            (
                "Priya",
                "Token validation failures after a key rotation. The secondary verification "
                "slot has to be verified before the primary is replaced, or Auth Gateway "
                "rejects every token.",
            ),
            ("MemoryOS", "What should a new engineer NOT do?"),
            (
                "Priya",
                "Do not delete the Session Store eviction history after a policy change. That "
                "history is the only way to tell an eviction storm from an attack. It caused "
                "INC-2031.",
            ),
            ("MemoryOS", "What do you check first?"),
            (
                "Priya",
                "Key propagation state in the Token Service. If the secondary is not "
                "acknowledged, stop. You are one deploy away from an outage.",
            ),
            ("MemoryOS", "When should someone escalate?"),
            (
                "Priya",
                "Escalate to Identity Operations whenever Auth Gateway validation error rate "
                "passes 5 percent. Below that it is usually a single bad client.",
            ),
        ],
    },
    {
        "id": "expert-ravi-network",
        "expert": "Ravi",
        "role": "Network Reliability Engineer",
        "team": "Network Operations",
        "captured_at": "2026-08-06T14:10:00Z",
        "scope": "Transit Fabric",
        "system": "Network Platform",
        "title": "Ravi — Network Platform operational interview",
        "transcript": [
            ("MemoryOS", "What should a new engineer NOT do?"),
            (
                "Ravi",
                "Do not fail back to the primary transit path without verifying the backup "
                "route-by-route. INC-3022 was a failover that left stale routes on the backup, "
                "and failing back blindly made it worse for two hours.",
            ),
            ("MemoryOS", "What do you check first?"),
            (
                "Ravi",
                "Route tables on the backup path, not the primary. The primary always looks "
                "healthy; that is the trap.",
            ),
            ("MemoryOS", "Who normally handles it?"),
            (
                "Ravi",
                "Network Operations owns the transit fabric, and DNS Resolver rotation is "
                "ours even though the runbook lives with the platform teams.",
            ),
        ],
    },
]


HANDOVER_DOCUMENTS: list[dict[str, Any]] = [
    {
        "id": "handover-arun-payment",
        "author": "Arun",
        "role": "Senior DevOps Engineer",
        "system": "Payment Platform",
        "scope": "Payment Queue v1",
        "created_at": "2026-08-20T16:00:00Z",
        "title": "Arun — Payment Platform handover note",
        "content": (
            "Handover note, Payment Platform. I am unavailable for an extended period. "
            "The Payment API runbook is incomplete in one important respect: it tells you to "
            "restart on connection-reset alerts, and it does not mention that the queue must "
            "be checked first. I have given the full explanation in the interview capture, "
            "and the incidents INC-1042, INC-1088, INC-1104 and INC-1111 are the evidence. "
            "Two things I could not get into any document: the retry-worker workaround, and "
            "the fact that the queue version matters, because the 80 percent threshold is a "
            "property of Payment Queue v1 and not of the Payment API. "
            "I also want it on the record that I work best early in the morning. "
            "That one is personal and does not belong in operational memory."
        ),
    },
    {
        "id": "handover-priya-identity",
        "author": "Priya",
        "role": "Staff Identity Engineer",
        "system": "Identity Platform",
        "scope": "Token Service",
        "created_at": "2026-08-21T09:30:00Z",
        "title": "Priya — Identity Platform handover note",
        "content": (
            "Handover note, Identity Platform. Key rotations on the Token Service require "
            "secondary-slot verification first. The Session Store eviction history is "
            "diagnostic evidence and must be preserved. Auth Gateway validation error rate "
            "above 5 percent means escalate to Identity Operations immediately."
        ),
    },
    {
        "id": "handover-ravi-network",
        "author": "Ravi",
        "role": "Network Reliability Engineer",
        "system": "Network Platform",
        "scope": "Transit Fabric",
        "created_at": "2026-08-21T11:15:00Z",
        "title": "Ravi — Network Platform handover note",
        "content": (
            "Handover note, Network Platform. Verify the backup transit path route-by-route "
            "before failing back. DNS Resolver upstream rotation belongs to Network "
            "Operations even though it is not in the platform runbooks."
        ),
    },
]


#: Pre-authored expert lessons. The interview adapter yields the first five as
#: extracted claims; these extra ones keep Memory Center populated and exercise
#: every memory type.
EXPERT_LESSONS: list[dict[str, Any]] = [
    {
        "id": "lesson-arun-001",
        "type": "EXPERIENCE",
        "title": "Restarting Payment API during queue saturation caused duplicate processing",
        "content": (
            "Restarting the Payment API while Payment Queue v1 was at 91 percent depth caused "
            "1,204 transactions to be processed twice during INC-1042."
        ),
        "summary": "Immediate restart under queue saturation is the most expensive mistake on the platform.",
        "scope": "Payment Queue v1",
        "owner": "Arun",
        "domain": "payments",
        "purpose": "Prevent the INC-1042 failure mode from recurring.",
        "entities": ["Payment API", "Payment Queue v1", "INC-1042"],
        "evidence": [("incident", "INC-1042", "Restart at 91% queue depth")],
        "observed_at": "2026-03-14T10:41:00Z",
        "source": "expert-arun-payment",
        "visibility": "PERSONAL",
    },
    {
        "id": "lesson-arun-002",
        "type": "LESSON",
        "title": "Check queue depth before restarting the Payment API",
        "content": (
            "Check Payment Queue v1 depth before restarting the Payment API. Above 80 percent "
            "the restart is harmful; below 80 percent the API itself is a valid suspect."
        ),
        "summary": "Queue depth is the deciding measurement, not the alert type.",
        "scope": "Payment Queue v1",
        "owner": "Arun",
        "domain": "payments",
        "purpose": "Give successors a deterministic first step that no runbook contains.",
        "entities": ["Payment API", "Payment Queue v1", "INC-1042", "INC-1088", "INC-1104"],
        "evidence": [
            ("incident", "INC-1042", "Restart at 91% caused duplicates"),
            ("incident", "INC-1088", "No restart at 87% resolved cleanly"),
            ("incident", "INC-1104", "No restart at 84% resolved cleanly"),
        ],
        "observed_at": "2026-08-04T09:00:00Z",
        "source": "expert-arun-payment",
        "visibility": "PERSONAL",
    },
    {
        "id": "lesson-arun-003",
        "type": "EXCEPTION",
        "title": "The 80% threshold is a property of Payment Queue v1, not of the Payment API",
        "content": (
            "This procedure applies to Payment Queue v1. The 80 percent escalation threshold is "
            "derived from the v1 consumer count of 8 and must not be transferred to another "
            "queue version without re-validation."
        ),
        "summary": "Scope boundary: the rule is version-specific.",
        "scope": "Payment Queue v1",
        "owner": "Arun",
        "domain": "payments",
        "purpose": "Stop a v1 threshold being applied to a different queue implementation.",
        "entities": ["Payment Queue v1", "Payment API"],
        "evidence": [],
        "observed_at": "2026-08-04T09:00:00Z",
        "source": "expert-arun-payment",
        "visibility": "PERSONAL",
    },
    {
        "id": "lesson-arun-004",
        "type": "RELATIONSHIP",
        "title": "Payments Operations owns queue-related escalation",
        "content": (
            "Payments Operations holds the settlement schedule and owns escalation for "
            "Payment Queue v1 saturation. Escalate to the Payments Operations on-call, not to "
            "the individual engineer who built the service."
        ),
        "summary": "Escalate to the team that owns the schedule, not to a person.",
        "scope": "Payment Queue v1",
        "owner": "Arun",
        "domain": "payments",
        "purpose": "Avoid a single-person dependency for escalation knowledge.",
        "entities": ["Payments Operations", "Payment Queue v1"],
        "evidence": [("incident", "INC-1088", "Escalated to Payments Operations")],
        "observed_at": "2026-05-02T14:08:00Z",
        "source": "expert-arun-payment",
        "visibility": "PERSONAL",
    },
    {
        "id": "lesson-arun-005",
        "type": "FACT",
        "title": "Payment API depends on Payment Queue v1",
        "content": (
            "The Payment API reads from and writes to Payment Queue v1. Connection-reset alerts "
            "on the Payment API are frequently caused by the queue rather than the API process."
        ),
        "summary": "Structural dependency that explains the misleading alert.",
        "scope": "Payment Queue v1",
        "owner": "Arun",
        "domain": "payments",
        "purpose": "Record the structural dependency behind the operational lesson.",
        "entities": ["Payment API", "Payment Queue v1"],
        "evidence": [("incident", "INC-1012", "Symptom in one platform, cause in another")],
        "observed_at": "2026-08-04T09:00:00Z",
        "source": "expert-arun-payment",
        "visibility": "PERSONAL",
    },
    {
        "id": "lesson-arun-006",
        "type": "HYPOTHESIS",
        "title": "Retry worker must be disabled only when the settlement partner is unhealthy",
        "content": (
            "Disabling the Payment Queue v1 retry worker is only correct when the settlement "
            "partner is unhealthy. With a healthy partner, disabling the worker stalls the "
            "drain. Arun believes this but has not isolated it in a controlled test."
        ),
        "summary": "Believed condition, not yet proven. Held as a hypothesis on purpose.",
        "scope": "Payment Queue v1",
        "owner": "Arun",
        "domain": "payments",
        "purpose": "Keep unproven operational belief distinguishable from proven experience.",
        "entities": ["Payment Queue v1", "INC-1111"],
        "evidence": [("incident", "INC-1111", "Retry worker disabled during a partner error")],
        "observed_at": "2026-07-08T04:36:00Z",
        "source": "expert-arun-payment",
        "visibility": "PERSONAL",
    },
    {
        "id": "lesson-arun-007",
        "type": "EXCEPTION",
        "title": "Consumer count on Payment Queue v1 must not change during settlement",
        "content": (
            "Scaling Payment Queue v1 consumers from 8 to 16 during a settlement window caused "
            "a redelivery storm in INC-1055. Consumer count changes are only safe outside "
            "settlement windows."
        ),
        "summary": "A configuration change that is safe sometimes and harmful other times.",
        "scope": "Payment Queue v1",
        "owner": "Arun",
        "domain": "payments",
        "purpose": "Record a negative constraint that configuration review would otherwise miss.",
        "entities": ["Payment Queue v1", "INC-1055"],
        "evidence": [("incident", "INC-1055", "Scale-out caused redelivery storm")],
        "observed_at": "2026-04-02T09:12:00Z",
        "source": "expert-arun-payment",
        "visibility": "PERSONAL",
    },
    {
        "id": "lesson-arun-008",
        "type": "COMMITMENT",
        "title": "Arun committed to hand over the retry-worker workaround to Payments Operations",
        "content": (
            "Arun committed to documenting the retry-worker workaround in the Payments "
            "Operations runbook before going unavailable. The workaround is still not in any "
            "runbook, so the commitment is outstanding."
        ),
        "summary": "An outstanding commitment that is itself a risk signal.",
        "scope": "Payment Queue v1",
        "owner": "Arun",
        "domain": "payments",
        "purpose": "Surface promises that were never fulfilled as an operational risk.",
        "entities": ["Payments Operations", "Payment Queue v1"],
        "evidence": [],
        "observed_at": "2026-08-20T16:00:00Z",
        "source": "handover-arun-payment",
        "visibility": "PERSONAL",
    },
    {
        "id": "lesson-priya-001",
        "type": "LESSON",
        "title": "Verify the secondary verification slot before rotating Token Service keys",
        "content": (
            "On the Token Service, confirm the secondary verification key has propagated before "
            "replacing the primary. INC-2014 rejected 41 percent of tokens because this was "
            "skipped."
        ),
        "summary": "Two-step key rotation is mandatory on the Token Service.",
        "scope": "Token Service",
        "owner": "Priya",
        "domain": "identity",
        "purpose": "Prevent a repeat of the INC-2014 validation outage.",
        "entities": ["Token Service", "Auth Gateway", "INC-2014"],
        "evidence": [("incident", "INC-2014", "Key rotation without propagation check")],
        "observed_at": "2026-02-11T08:15:00Z",
        "source": "expert-priya-identity",
        "visibility": "TEAM",
    },
    {
        "id": "lesson-priya-002",
        "type": "EXCEPTION",
        "title": "Session Store eviction history is diagnostic evidence and must be preserved",
        "content": (
            "Never clear the Session Store eviction history after a policy change. It is the "
            "only way to distinguish an eviction storm from an attack, and clearing it cost "
            "hours during INC-2031."
        ),
        "summary": "Negative knowledge about destroying evidence.",
        "scope": "Session Store",
        "owner": "Priya",
        "domain": "identity",
        "purpose": "Preserve the diagnostic trail needed during a security review.",
        "entities": ["Session Store", "INC-2031", "INC-1012"],
        "evidence": [
            ("incident", "INC-2031", "Eviction policy change"),
            ("incident", "INC-1012", "Downstream impact on Payment API"),
        ],
        "observed_at": "2026-05-30T19:50:00Z",
        "source": "expert-priya-identity",
        "visibility": "TEAM",
    },
    {
        "id": "lesson-priya-003",
        "type": "FACT",
        "title": "Payment Platform latency can originate in the Identity Platform",
        "content": (
            "Payment API latency and timeouts are frequently caused by the Identity Platform "
            "Session Store, not by the Payment Platform. Restarting the Payment API never "
            "fixes a Session Store problem."
        ),
        "summary": "Cross-platform dependency that redirects the investigation.",
        "scope": "Session Store",
        "owner": "Priya",
        "domain": "identity",
        "purpose": "Stop engineers restarting the wrong service.",
        "entities": ["Payment API", "Session Store", "INC-1012"],
        "evidence": [("incident", "INC-1012", "Latency traced to Session Store")],
        "observed_at": "2026-01-22T12:30:00Z",
        "source": "handover-priya-identity",
        "visibility": "TEAM",
    },
    {
        "id": "lesson-ravi-001",
        "type": "LESSON",
        "title": "Verify the backup transit path route-by-route before failing back",
        "content": (
            "Before failing the transit fabric back to the primary path, verify every route on "
            "the backup. INC-3022 lost 3.8 percent of packets to stale routes left after "
            "failover."
        ),
        "summary": "Failover is not symmetric; the backup must be inspected.",
        "scope": "Transit Fabric",
        "owner": "Ravi",
        "domain": "network",
        "purpose": "Prevent a worse outage while recovering from a failover.",
        "entities": ["Transit Fabric", "INC-3022"],
        "evidence": [("incident", "INC-3022", "Stale routes on the backup path")],
        "observed_at": "2026-04-29T05:44:00Z",
        "source": "expert-ravi-network",
        "visibility": "TEAM",
    },
    {
        "id": "lesson-ravi-002",
        "type": "EXCEPTION",
        "title": "DNS Resolver upstream rotation belongs to Network Operations",
        "content": (
            "Upstream DNS Resolver rotation is owned by Network Operations even though the "
            "runbook lives with the platform teams. During INC-3040 the platform teams could "
            "not authorise the rotation they needed."
        ),
        "summary": "Ownership that does not match the documentation.",
        "scope": "DNS Resolver",
        "owner": "Ravi",
        "domain": "network",
        "purpose": "Remove an authorisation deadlock during a security incident.",
        "entities": ["DNS Resolver", "Network Operations", "INC-3040"],
        "evidence": [("incident", "INC-3040", "Spoofed records required resolver rotation")],
        "observed_at": "2026-06-12T21:29:00Z",
        "source": "handover-ravi-network",
        "visibility": "TEAM",
    },
    {
        "id": "lesson-ravi-003",
        "type": "RELATIONSHIP",
        "title": "Edge Router keepalive changes affect Payment API timeouts",
        "content": (
            "A keepalive reduction applied on the Edge Router caused Payment API timeouts in "
            "INC-1093. Network Platform changes can present as Payment Platform incidents."
        ),
        "summary": "A dependency that crosses platform boundaries.",
        "scope": "Edge Router",
        "owner": "Ravi",
        "domain": "network",
        "purpose": "Route investigations to the owning platform faster.",
        "entities": ["Edge Router", "Payment API", "INC-1093"],
        "evidence": [("incident", "INC-1093", "Keepalive reduction caused timeouts")],
        "observed_at": "2026-05-19T10:02:00Z",
        "source": "expert-ravi-network",
        "visibility": "TEAM",
    },
]


ARCHITECTURE_CHANGES: list[dict[str, Any]] = [
    {
        "id": "ARCH-2026-02-11",
        "title": "Token Service key rotation pipeline introduced",
        "system": "Identity Platform",
        "component": "Token Service",
        "effective_at": "2026-02-10T00:00:00Z",
        "summary": (
            "The Token Service gained an automated secondary-slot propagation check. Manual "
            "verification of the secondary key before rotation is now enforced by the pipeline."
        ),
        "invalidates_scope": None,
    },
    {
        "id": "ARCH-2026-05-19",
        "title": "Edge Router keepalive default lowered to 30s",
        "system": "Network Platform",
        "component": "Edge Router",
        "effective_at": "2026-05-17T00:00:00Z",
        "summary": (
            "The Edge Router keepalive default was lowered from 60s to 30s to reduce idle "
            "connection count. This changed the timeout profile observed by the Payment API."
        ),
        "invalidates_scope": "Edge Router",
    },
    {
        "id": "ARCH-2026-09-28",
        "title": "Payment Queue v2 deployed, replacing Payment Queue v1",
        "system": "Payment Platform",
        "component": "Payment Queue v2",
        "effective_at": "2026-09-28T00:00:00Z",
        "summary": (
            "Payment Queue v2 was deployed and replaced Payment Queue v1. The restart "
            "procedure has changed. The historical Payment Queue v1 lesson must not "
            "automatically be applied to Queue v2. Validate the new operational procedure "
            "with Payments Operations before acting on the historical lesson."
        ),
        "invalidates_scope": "Payment Queue v1",
    },
]


#: The Payment Platform memory timeline shown on the Evolution page.
TIMELINE_EVENTS: list[dict[str, Any]] = [
    {
        "at": "2026-01-22T12:30:00Z",
        "label": "INC-1012",
        "detail": "Payment API latency traced to the Identity Platform Session Store",
        "kind": "incident",
    },
    {
        "at": "2026-03-14T10:41:00Z",
        "label": "INC-1042",
        "detail": "Immediate restart at 91% queue depth caused 1,204 duplicate payments",
        "kind": "incident",
        "critical": True,
    },
    {
        "at": "2026-05-02T14:08:00Z",
        "label": "INC-1088",
        "detail": "Queue checked, escalated, no restart, resolved cleanly at 87%",
        "kind": "incident",
        "supporting": True,
    },
    {
        "at": "2026-06-21T20:22:00Z",
        "label": "INC-1104",
        "detail": "Payments Operations procedure followed, resolved without restart at 84%",
        "kind": "incident",
        "supporting": True,
    },
    {
        "at": "2026-07-08T04:36:00Z",
        "label": "INC-1111",
        "detail": "Retry worker disabled at 93%, drain resumed, no restart",
        "kind": "incident",
        "supporting": True,
    },
    {
        "at": "2026-08-04T09:00:00Z",
        "label": "Expert lesson captured",
        "detail": "Arun explains the queue-saturation rule and the retry-worker workaround",
        "kind": "capture",
    },
    {
        "at": "2026-08-20T16:00:00Z",
        "label": "Handover note",
        "detail": "Arun records that the runbook is incomplete and the threshold is version-specific",
        "kind": "handover",
    },
    {
        "at": "2026-08-28T10:20:00Z",
        "label": "Promotion to organization",
        "detail": "Arun's queue-saturation lesson reviewed and promoted to organizational knowledge",
        "kind": "governance",
    },
    {
        "at": "2026-09-05T14:02:00Z",
        "label": "Successor recommendation",
        "detail": "Maya asks about connection resets and is told not to restart yet",
        "kind": "agent",
    },
    {
        "at": "2026-09-05T14:31:00Z",
        "label": "Outcome recorded",
        "detail": "Queue at 88%, escalated to Payments Operations, resolved without restart",
        "kind": "outcome",
        "supporting": True,
    },
    {
        "at": "2026-09-28T00:00:00Z",
        "label": "ARCH-2026-09-28",
        "detail": "Payment Queue v2 deployed, restart procedure changed",
        "kind": "change",
        "critical": True,
    },
    {
        "at": "2026-09-28T00:12:00Z",
        "label": "Potential contradiction",
        "detail": "Payment Queue v1 lesson detected as possibly outdated in the v2 environment",
        "kind": "contradiction",
        "critical": True,
    },
    {
        "at": "2026-09-28T00:26:00Z",
        "label": "Memory scope updated",
        "detail": "Lesson restricted to Payment Queue v1; Queue v2 marked as requiring validation",
        "kind": "governance",
    },
]


MEMORY_GRAPH_EDGES: list[dict[str, str]] = [
    {"from": "Arun", "to": "Payment API", "label": "knows", "kind": "person_system"},
    {"from": "Payment API", "to": "Payment Queue v1", "label": "depends_on", "kind": "dependency"},
    {"from": "Payment API", "to": "Payment Queue v2", "label": "depends_on", "kind": "dependency"},
    {"from": "INC-1042", "to": "Restart during saturation", "label": "demonstrates", "kind": "failure"},
    {"from": "INC-1088", "to": "Queue saturation lesson", "label": "supports", "kind": "support"},
    {"from": "INC-1104", "to": "Queue saturation lesson", "label": "supports", "kind": "support"},
    {"from": "INC-1111", "to": "Queue saturation lesson", "label": "supports", "kind": "support"},
    {
        "from": "Queue saturation lesson",
        "to": "Payments Operations",
        "label": "escalates_to",
        "kind": "escalation",
    },
    {"from": "Arun", "to": "Queue saturation lesson", "label": "authored", "kind": "authorship"},
    {
        "from": "Payment Queue v2",
        "to": "Queue saturation lesson",
        "label": "invalidates",
        "kind": "change",
    },
]


FUTURE_MODULES: list[dict[str, str]] = [
    {
        "name": "Company Memory",
        "description": "Cross-entity knowledge about customers, contracts and commitments.",
    },
    {
        "name": "Crisis Memory",
        "description": "How this organization actually behaved under pressure, and what worked.",
    },
    {
        "name": "Decision Memory",
        "description": "The reasoning behind decisions, including the options that were rejected.",
    },
    {
        "name": "Customer Memory",
        "description": "Account-specific history for support and success teams.",
    },
    {
        "name": "Negotiation Memory",
        "description": "Positions that worked or failed in commercial negotiation.",
    },
]


def incident_ids_for_lesson(lesson_id: str) -> list[str]:
    for lesson in EXPERT_LESSONS:
        if lesson["id"] == lesson_id:
            return [e[1] for e in lesson.get("evidence", []) if e[0] == "incident"]
    return []


def incident(incident_id: str) -> dict[str, Any] | None:
    for i in INCIDENTS:
        if i["id"] == incident_id:
            return i
    return None


def _dt_parse(value: str) -> datetime:
    return _dt(value)


__all__ = [
    "ARCHITECTURE_CHANGES",
    "COMPANY",
    "EXPERT_INTERVIEWS",
    "EXPERT_LESSONS",
    "FUTURE_MODULES",
    "HANDOVER_DOCUMENTS",
    "INCIDENTS",
    "MEMORY_GRAPH_EDGES",
    "SYNTHETIC_BANNER",
    "TIMELINE_EVENTS",
    "incident",
    "incident_ids_for_lesson",
]
