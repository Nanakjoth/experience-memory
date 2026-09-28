"""Shared demo actors and helpers."""

from __future__ import annotations

from backend.models.permissions import Actor
from backend.models.memory import Visibility

#: The people in the synthetic demo. Every request is made as one of them.
DEMO_ACTORS: dict[str, Actor] = {
    "arun": Actor(
        id="emp-arun",
        display_name="Arun",
        role="Senior DevOps Engineer",
        team="Payments Operations",
    ),
    "maya": Actor(
        id="emp-maya",
        display_name="Maya",
        role="New DevOps Engineer",
        team="Payments Operations",
    ),
    "priya": Actor(
        id="emp-priya",
        display_name="Priya",
        role="Staff Identity Engineer",
        team="Identity Operations",
    ),
    "ravi": Actor(
        id="emp-ravi",
        display_name="Ravi",
        role="Network Reliability Engineer",
        team="Network Operations",
    ),
    "steward": Actor(
        id="knowledge-steward",
        display_name="Knowledge Steward",
        role="Knowledge Steward",
        team="Platform Operations",
    ),
    "outsider": Actor(
        id="external-contractor",
        display_name="External Contractor",
        role="Contractor",
        team="",
        # A contractor has no organizational standing: they can read nothing
        # beyond their own personal memory, whatever the Memory Gate decided.
        visibility_ceiling=Visibility.PERSONAL,
    ),
    "system": Actor(
        id="system",
        display_name="MemoryOS",
        role="System",
    ),
}

DEMO_QUESTION = "Payment API is showing connection reset alerts. What should I do?"


def actor_for(key: str) -> Actor:
    return DEMO_ACTORS.get(key, DEMO_ACTORS["maya"])


__all__ = ["DEMO_ACTORS", "DEMO_QUESTION", "actor_for"]
