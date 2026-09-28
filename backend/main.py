"""FastAPI application entrypoint.

    uvicorn backend.main:app --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api import ask as ask_routes
from backend.api import audit as audit_routes
from backend.api import capture as capture_routes
from backend.api import dashboard as dashboard_routes
from backend.api import governance as governance_routes
from backend.api import memories as memories_routes
from backend.api import outcomes as outcomes_routes
from backend.api import routes as demo_routes
from backend.config import get_settings
from backend.memory.hindsight_client import (
    BANK_DIRECTIVES,
    BANK_DISPOSITION,
    BANK_MISSION,
)
from backend.models.permissions import PermissionDenied
from backend.seed.novatech import COMPANY, FUTURE_MODULES, SYNTHETIC_BANNER
from backend.services import get_services
from backend.utils import utcnow

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("memoryos")

DESCRIPTION = """
**MemoryOS — Knowledge Continuity for Organizations**

Hindsight is the memory engine. `retain` stores experience, `recall` retrieves
evidence, `reflect` reasons across accumulated experience.

This is a synthetic demo. Every person, system, incident and measurement is
fictional.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.ensure_directories()
    services = get_services()
    health = await services.engine.probe()
    log.info("MemoryOS starting. Memory engine: %s (%s)", health.label, health.mode)
    if health.simulated:
        log.warning(
            "Hindsight is unreachable at %s. Running the SIMULATED engine. "
            "See README -> Hindsight setup.",
            settings.hindsight_base_url,
        )
    app.state.engine_health = health
    yield
    await services.engine.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description=DESCRIPTION,
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_prefix
    app.include_router(dashboard_routes.router, prefix=prefix)
    app.include_router(capture_routes.router, prefix=prefix)
    app.include_router(ask_routes.router, prefix=prefix)
    app.include_router(outcomes_routes.router, prefix=prefix)
    app.include_router(memories_routes.router, prefix=prefix)
    app.include_router(governance_routes.router, prefix=prefix)
    app.include_router(audit_routes.router, prefix=prefix)
    app.include_router(demo_routes.router, prefix=prefix)

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, Any]:
        services = get_services()
        return {
            "product": settings.app_name,
            "subtitle": settings.app_subtitle,
            "tagline": "When experience leaves, memory stays.",
            "statement": (
                "We don't copy an employee's brain. We preserve what the organization "
                "would otherwise have to learn again."
            ),
            "north_star": (
                "What does an AI agent know because the organization has experienced it "
                "before — and can we prove why it knows it?"
            ),
            "synthetic_data": SYNTHETIC_BANNER,
            "company": COMPANY["name"],
            "memory_engine": {
                "name": "hindsight",
                "bank_id": settings.hindsight_bank_id,
                "operations": ["retain", "recall", "reflect"],
                "bank_mission": BANK_MISSION,
                "bank_directives": BANK_DIRECTIVES,
                "bank_disposition": BANK_DISPOSITION,
                "status": services.describe(),
            },
            "future_platform_modules": FUTURE_MODULES,
            "docs": "/docs",
            "generated_at": utcnow().isoformat(),
        }

    @app.get("/api/engine", tags=["meta"])
    async def engine_info() -> dict[str, Any]:
        services = get_services()
        health = await services.engine.health()
        return {
            "health": {
                "available": health.available,
                "mode": health.mode,
                "label": health.label,
                "bank_id": health.bank_id,
                "detail": health.detail,
                "version": health.version,
                "simulated": health.simulated,
            },
            "status": services.describe(),
            "bank": {
                "mission": BANK_MISSION,
                "directives": BANK_DIRECTIVES,
                "disposition": BANK_DISPOSITION,
            },
            "config": settings.public_dict(),
        }

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "error": "invalid_input"},
        )

    @app.exception_handler(PermissionDenied)
    async def permission_denied_handler(
        request: Request, exc: PermissionDenied
    ) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={"detail": str(exc), "error": "permission_denied"},
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=not get_settings().environment.startswith("prod"),
    )
