# MemoryOS — Running Instructions

Everything needed to clone, run, verify and deploy. Commands are given for
**Windows/PowerShell and bash** where they differ; the application itself is
platform-independent.

> **No Docker, no API keys and no cloud account are required.** MemoryOS runs
> fully offline against its simulated memory engine.

---

## 1. Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.11+ (3.12 recommended) | `python --version` |
| Node.js | 18+ (20 LTS recommended) | `node --version` |
| npm | 9+ | `npm --version` |
| Docker | *optional* — only for the live Hindsight engine | `docker --version` |

---

## 2. Quick start

Two terminals. Total time from clone to running app: **about 3 minutes.**

### Terminal 1 — backend

```powershell
git clone https://github.com/Nanakjoth/experience-memory.git
cd experience-memory

python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt

.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

- API — <http://127.0.0.1:8000>
- Interactive API docs — <http://127.0.0.1:8000/docs>
- Engine status — <http://127.0.0.1:8000/api/engine>

### Terminal 2 — frontend

```powershell
cd experience-memory/frontend
npm install
npm run dev
```

- UI — <http://localhost:5173>

### Then

Open <http://localhost:5173/demo> and press **Run full demo**. It executes 13
narrated steps against the live backend and renders each result.

---

## 3. Port conflict

If port 8000 is taken, run the backend elsewhere and point the Vite proxy at it:

```powershell
# backend
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

```ts
// frontend/vite.config.ts
proxy: { "/api": { target: "http://127.0.0.1:8001", changeOrigin: true } }
```

`strictPort: true` means Vite will fail rather than silently pick another port,
which avoids the confusing case where the UI is running but the API is not.

---

## 4. Configuration

Every setting has a working default. **You do not need a `.env` file.**

```powershell
copy .env.example .env      # Windows
cp .env.example .env        # bash
```

| Variable | Default | Notes |
|---|---|---|
| `ENVIRONMENT` | `development` | Set to `prod` to disable auto-reload |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Add your deployed origin here |
| `HINDSIGHT_BASE_URL` | `http://localhost:8888` | Live engine URL |
| `HINDSIGHT_BANK_ID` | `memoryos-novatech` | Must match the bank's id |
| `HINDSIGHT_API_KEY` | *(unset)* | Only if the instance requires auth |
| `FORCE_SIMULATED_ENGINE` | `false` | `true` for deterministic tests |
| `DEFAULT_ACTOR` | `maya` | Identity used before the header picker is touched |
| `RECALL_BUDGET` / `REFLECT_BUDGET` | `mid` / `low` | Retrieval depth (20 / 8 facts) |
| `LLM_PROVIDER` | `none` | **Not wired to any execution path** — see [PROMPT_CONFIGS §7](PROMPT_CONFIGS.md#7-llm-configuration--and-why-it-is-inert) |

`.env` is gitignored. `public_dict()` is the only representation of settings
that ever leaves the process, and it reports key *presence*, never key values.

---

## 5. Optional — the live Hindsight engine

Not required. Skipping this changes nothing about what the app can demonstrate.

```powershell
docker compose -f docker-compose.hindsight.yml up -d
```

Wait for the healthcheck, then restart the backend and confirm:

```bash
curl -s http://127.0.0.1:8000/api/engine | python -m json.tool
```

| Field | Simulated | Live |
|---|---|---|
| `health.mode` | `simulated` | `live` |
| `health.label` | `HINDSIGHT (SIMULATED)` | `HINDSIGHT (LIVE)` |
| `health.simulated` | `true` | `false` |

The bank id must match `HINDSIGHT_BANK_ID`. On first contact the app creates the
bank and applies its mission and directives
([PROMPT_CONFIGS §2–4](PROMPT_CONFIGS.md#2-bank-mission)).

> When live, the engine *accumulates* history. `POST /api/demo/reset` clears the
> app database and the local cache but deliberately leaves a live bank intact —
> it does not pretend to erase a server's contents.

---

## 6. Verifying the installation

```powershell
# Backend — expect 37 passed
.venv\Scripts\python.exe -m pytest backend/tests -q
```

```powershell
# Frontend — all three must exit 0
cd frontend
npm run lint
npm run typecheck
npm run build
```

### End-to-end proof

```bash
# The whole product story in one call.
# Expect: status "ok", 13 steps, progress_percent 100
curl -s -X POST http://127.0.0.1:8000/api/demo/run \
     -H "Content-Type: application/json" -d '{}'
```

```bash
# The privacy boundary. Compare the visibility counts:
curl -s "http://127.0.0.1:8000/api/memories?actor=maya&limit=200"
curl -s "http://127.0.0.1:8000/api/memories?actor=outsider&limit=200"
```

---

## 7. What each screen demonstrates

| Route | What it proves |
|---|---|
| `/` | Metrics are real application events, not fabricated numbers |
| `/demo` | The 13-step story end to end |
| `/ask` | Evidence, scope, confidence, suppression counts, full trace |
| `/capture` | Knowledge starts `PERSONAL`; the gate shows its reasoning |
| `/memory` | Master-detail, only legal lifecycle actions offered |
| `/evolution` | Lifecycle ladder and history; scope invalidation |
| `/risk` | Bus-factor analysis — who holds knowledge nobody else does |
| `/governance` | Contradiction resolution, driven by server-provided actions |
| `/audit` | Every mutation is recorded |

---

## 8. Docker

```powershell
# Backend
docker build -t memoryos-backend -f backend/Dockerfile .
docker run -d --name memoryos-api -p 8000:8000 -v memoryos-data:/app/backend/data memoryos-backend

# Frontend
docker build -t memoryos-frontend -f frontend/Dockerfile .
docker run -d --name memoryos-web -p 8080:80 memoryos-frontend
```

- UI — <http://localhost:8080>

Both images run as a non-root user and define a `HEALTHCHECK`. The backend's
SQLite file lives on the `memoryos-data` volume so memory survives restarts.

---

## 9. Production build

```powershell
cd frontend
npm run build          # -> frontend/dist
```

`VITE_API_BASE_URL` is inlined **at build time**:

```powershell
# Same-origin (API behind the same host / reverse proxy)
$env:VITE_API_BASE_URL = ""
npm run build

# Different origin
$env:VITE_API_BASE_URL = "https://api.example.com"
npm run build
```

**SPA fallback is mandatory.** The app uses `BrowserRouter`, so a static host
must rewrite unknown paths to `index.html` or every deep link and refresh
returns 404. `frontend/nginx.conf` includes the correct rule:

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

Equivalent for other hosts:

- **Netlify** — `/* /index.html 200` in `_redirects`
- **Firebase Hosting** — `"rewrites": [{ "source": "**", "destination": "/index.html" }]`
- **S3 + CloudFront** — error document `index.html`, plus a CloudFront function

If the API is on a different origin, add that origin to the backend's
`CORS_ORIGINS`.

---

## 10. Continuous integration

`.github/workflows/ci.yml` runs on every push and PR:

| Job | Does |
|---|---|
| `backend` | installs `requirements-dev.txt`, runs pytest, imports the app |
| `frontend` | `npm ci`, `typecheck`, `lint`, `build` |
| `secrets` | asserts `.env` is untracked and `.gitignore` covers env/venv/data/node_modules/dist |

The `secrets` job is a guard, not a formality — it fails the build if a `.env`
is ever committed.

---

## 11. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `HINDSIGHT (SIMULATED)` in the header | Hindsight unreachable | Expected by default. See §5 to run it live. |
| `Address already in use` | Port 8000 or 5173 taken | See §3 |
| UI loads, every panel errors | Backend not running, or proxy target wrong | `curl /api/engine`; check `vite.config.ts` |
| Fresh deep link 404s in production | Missing SPA fallback | See §9 |
| `ModuleNotFoundError: backend` | Wrong working directory | Run uvicorn from the repo root |
| Tests fail after editing config | Cached settings | `reset_settings_cache()` exists for exactly this |
| Answers say `outdated: true` | Correct behaviour after a scope change | Demo step 10 is meant to do this |

---

## 12. Repository layout

```
.
├── backend/                  FastAPI application
│   ├── api/                  thin HTTP layer (8 routers, 49 routes)
│   ├── memory/               the domain: engine, retrieval, reflection,
│   │                         confidence, governance, lifecycle, provenance
│   ├── models/               Pydantic models — the API contract
│   ├── agents/               SuccessorAgent
│   ├── sources/              capture adapters (interview, incident, handover…)
│   ├── db/database.py        SQLite access
│   ├── seed/novatech.py      the synthetic scenario
│   ├── services.py           object graph / DI container
│   ├── config.py             settings
│   └── tests/                37 tests
├── frontend/                 React + Vite SPA (9 pages)
│   ├── src/pages/            one file per screen
│   ├── src/components/       layout + UI primitives
│   ├── src/lib/              api client, app state, types, formatters
│   ├── Dockerfile
│   └── nginx.conf
├── docs/                     architecture, flowcharts, prompts, this file
├── .github/workflows/ci.yml
├── .env.example              every setting, documented
├── requirements.txt          runtime deps
├── requirements-dev.txt      + pytest
└── docker-compose.hindsight.yml
```

---

## 13. Further reading

| Document | Read it for |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Structure and why; Mermaid diagrams |
| [`FLOWCHART.md`](FLOWCHART.md) | Step-by-step runtime behaviour |
| [`PROMPT_CONFIGS.md`](PROMPT_CONFIGS.md) | Every prompt and config, and what it actually does |
| [`../README.md`](../README.md) | Product overview and screen-by-screen guide |
| [`../arch.md`](../arch.md) | Deep design rationale |
| [`../flow.md`](../flow.md) | Narrative runtime walkthrough |
| [`../session.md`](../session.md) | Build history and open items |
