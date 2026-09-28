"""Ask MemoryOS — the central interaction."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.actors import DEMO_ACTORS, DEMO_QUESTION, actor_for
from backend.api.schemas import AskRequest, AskResponse
from backend.models.memory import Visibility
from backend.models.permissions import PermissionDenied, can_reach
from backend.services import Services, get_services

router = APIRouter(tags=["ask"])


@router.get("/ask/suggestions")
async def suggestions(s: Services = Depends(get_services)) -> dict[str, Any]:
    current = s.retrieval.current_scope()
    return {
        "questions": [
            DEMO_QUESTION,
            "Payment Queue v1 is at 91%. What do I do?",
            "What should a new engineer not do on the Payment API?",
            "Who do I escalate a saturated Payment Queue v1 to?",
            "What is still valid on Payment Queue v2?",
            "What does Arun prefer to work on?",
        ],
        "current_environment": current,
        "actors": [
            {"id": k, "name": v.display_name, "role": v.role, "team": v.team}
            for k, v in DEMO_ACTORS.items()
            if v.role != "System"
        ],
    }


@router.post("/ask", response_model=AskResponse)
async def ask(payload: AskRequest, s: Services = Depends(get_services)) -> AskResponse:
    actor = actor_for(payload.actor)
    question = (payload.question or "").strip() or DEMO_QUESTION
    if len(question) > 2000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question is too long (2000 character limit).",
        )

    try:
        answer = await s.agent.ask(
            question, actor=actor, current_scope=payload.current_scope
        )
    except PermissionDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": str(exc), "reason": exc.reason},
        ) from exc

    s.db.add_conversation_turn(
        actor_id=actor.id, role="user", content=question, turn_index=_next_turn(s, actor.id)
    )
    s.db.add_conversation_turn(
        actor_id=actor.id, role="assistant", content=answer.answer.headline, turn_index=_next_turn(s, actor.id) + 1
    )
    return AskResponse(**answer.to_dict())


def _next_turn(s: Services, actor_id: str) -> int:
    turns = s.db.list_conversation(actor_id=actor_id, limit=1000)
    return len(turns)


@router.get("/actors")
async def actors(s: Services = Depends(get_services)) -> dict[str, Any]:
    """The people the demo can act as, plus what each of them is allowed to see.

    The visibility ceiling is real: it comes from the permission resolver, not
    from a hard-coded list in the UI.
    """
    default = s.settings.default_actor
    return {
        "default": default,
        "current_environment": s.retrieval.current_scope(),
        "actors": [
            {
                "id": key,
                "name": actor.display_name,
                "display_name": actor.display_name,
                "role": actor.role,
                "team": actor.team,
                "is_system": actor.is_system,
                "visibility_ceiling": str(actor.visibility_ceiling),
                "can_read": {
                    # Personal knowledge is always readable by its owner and is
                    # never readable by anyone else, whatever the ceiling is.
                    "own_personal": True,
                    "others_personal": actor.is_system,
                    "team": can_reach(actor.visibility_ceiling, Visibility.TEAM),
                    "organization": can_reach(
                        actor.visibility_ceiling, Visibility.ORGANIZATION
                    ),
                },
                "can_promote": {
                    "team": s.resolver.may_promote_to(actor, Visibility.TEAM)[0],
                    "organization": s.resolver.may_promote_to(
                        actor, Visibility.ORGANIZATION
                    )[0],
                },
                "promotion_note": s.resolver.may_promote_to(
                    actor, Visibility.ORGANIZATION
                )[1],
            }
            for key, actor in DEMO_ACTORS.items()
        ],
    }


@router.get("/conversations")
async def conversations(
    s: Services = Depends(get_services),
    actor: str = "maya",
) -> dict[str, Any]:
    """Ask history for one actor, oldest first."""
    person = actor_for(actor)
    turns = s.db.list_conversation(actor_id=person.id, limit=500)
    return {
        "actor": {"id": person.id, "name": person.display_name, "role": person.role},
        "turns": [
            {
                "index": t["turn_index"],
                "role": t["role"],
                "content": t["content"],
                "at": t["at"],
            }
            for t in turns
        ],
        "count": len(turns),
    }


__all__ = ["router"]
