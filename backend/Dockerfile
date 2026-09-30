# ---------------------------------------------------------------------------
# MemoryOS backend — FastAPI + Hindsight memory engine
#
# Build:
#   docker build -t memoryos-backend -f backend/Dockerfile .
# Run:
#   docker run -p 8000:8000 -v memoryos-data:/app/backend/data memoryos-backend
#
# The SQLite file lives on a volume so memory survives container restarts.
# With no HINDSIGHT_BASE_URL reachable the app degrades to the clearly-labelled
# SIMULATED engine rather than failing to boot.
# ---------------------------------------------------------------------------

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first so the layer caches across code edits.
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/

# SQLite needs a writable directory. Run unprivileged: the data volume is
# chowned to the app user at build time so a bind/volume mount still works.
RUN mkdir -p /app/backend/data \
    && useradd --create-home --uid 1000 memoryos \
    && chown -R memoryos:memoryos /app
USER memoryos

EXPOSE 8000

# Fails the container healthcheck if the app cannot serve, so an orchestrator
# can tell "started" apart from "actually healthy".
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status==200 else 1)"

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
