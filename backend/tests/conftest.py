"""Pytest configuration.

Tests run entirely in-process against the SIMULATED memory engine with a
throw-away SQLite file, so the suite is deterministic and needs no network.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_TMP = Path(tempfile.mkdtemp(prefix="memoryos-tests-"))
os.environ.setdefault("MEMORYOS_TEST_DIR", str(_TMP))
os.environ["FORCE_SIMULATED_ENGINE"] = "true"
os.environ["HINDSIGHT_BASE_URL"] = "http://127.0.0.1:1"  # guaranteed unreachable
os.environ["APP_DB_PATH"] = str(_TMP / "memoryos.db")
os.environ["SIMULATED_DB_PATH"] = str(_TMP / "hindsight_sim.db")
os.environ["LLM_PROVIDER"] = "none"
os.environ["ENVIRONMENT"] = "test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.config import reset_settings_cache  # noqa: E402
from backend.main import create_app  # noqa: E402
from backend.services import get_services  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    reset_settings_cache()
    services = get_services()
    services.reset_for_tests()
    app = create_app()
    with TestClient(app) as c:
        c.post("/api/demo/reset")
        yield c


@pytest.fixture()
def fresh_client() -> TestClient:
    """A client whose application state has been reset to the seeded baseline."""
    reset_settings_cache()
    services = get_services()
    services.reset_for_tests()
    app = create_app()
    with TestClient(app) as c:
        c.post("/api/demo/reset")
        yield c
