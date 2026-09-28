"""Application configuration for MemoryOS.

All configuration is environment driven. No secrets are hard-coded and nothing
secret is ever returned to the client: :class:`Settings.public_dict` is the only
representation that leaves the process.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_ROOT.parent

SENSITIVE_KEYS = {
    "hindsight_api_key",
    "openai_api_key",
    "anthropic_api_key",
    "llm_api_key",
}


class Settings(BaseSettings):
    """Runtime settings.

    The defaults are intentionally tuned so that ``uvicorn backend.main:app``
    works on a laptop with no external services running. In that case the
    memory engine falls back to the clearly-labelled SIMULATED engine.
    """

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---------------------------------------------------
    app_name: str = "MemoryOS"
    app_subtitle: str = "Knowledge Continuity for Organizations"
    environment: str = Field(default="development")
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Hindsight -----------------------------------------------------
    hindsight_base_url: str = "http://localhost:8888"
    hindsight_api_key: str | None = None
    hindsight_bank_id: str = "memoryos-novatech"
    hindsight_timeout: float = 60.0
    # When true a live Hindsight server is never contacted and the SIMULATED
    # engine is used. Useful for deterministic tests and offline demos.
    force_simulated_engine: bool = False
    # Number of consecutive live failures before falling back to SIMULATED.
    live_failure_threshold: int = 2

    # --- Storage -------------------------------------------------------
    app_db_path: Path = BACKEND_ROOT / "data" / "memoryos.db"
    simulated_db_path: Path = BACKEND_ROOT / "data" / "hindsight_sim.db"

    # --- LLM (used only for optional answer polishing) -----------------
    llm_provider: str = "none"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"

    # --- Behaviour -----------------------------------------------------
    recall_max_tokens: int = 4096
    recall_budget: str = "mid"
    reflect_budget: str = "low"
    request_timeout_seconds: float = 30.0
    # The actor the UI acts as when nobody has chosen one.
    default_actor: str = "maya"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_directories(self) -> None:
        self.app_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.simulated_db_path.parent.mkdir(parents=True, exist_ok=True)

    def public_dict(self) -> dict[str, object]:
        """Configuration safe to expose over the API."""
        return {
            "app_name": self.app_name,
            "app_subtitle": self.app_subtitle,
            "environment": self.environment,
            "hindsight_base_url": self.hindsight_base_url,
            "hindsight_bank_id": self.hindsight_bank_id,
            "hindsight_api_key_configured": bool(self.hindsight_api_key),
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_api_key_configured": bool(self.llm_api_key),
            "recall_budget": self.recall_budget,
            "reflect_budget": self.reflect_budget,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings


def reset_settings_cache() -> None:
    """Used by tests that mutate the environment."""
    get_settings.cache_clear()


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
