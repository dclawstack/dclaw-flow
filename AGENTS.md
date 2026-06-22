# DClaw App — Agent Development Guide

> **Read this file first before making any code changes.**
> This document is the source of truth for architecture, anti-patterns, and development workflow.

## App Identity

**DClaw Flow** is a vertical SaaS application built on the DClaw Stack.

- **Backend Port:** `8088` (FastAPI)
- **Frontend Port:** `3003` (Next.js)
- **Database:** `dclaw_flow` (PostgreSQL)
- **Base API Path:** `/api/v1/flows`

## Architecture Lock — DO NOT CHANGE

These are non-negotiable. If an agent suggests changing them, reject it.

### Backend
- **FastAPI** with `lifespan` handler (`app/main.py`)
- **SQLAlchemy 2.0** — `Base = declarative_base()` lives in `app/database.py`; models import it via `from app.database import Base` and use `Mapped`/`mapped_column`. Do NOT use `MappedAsDataclass`. Do NOT introduce a second `Base` or an `app/models/` package — one once shadowed `app/models.py` and broke every import.
- **Pydantic v2** schemas with `ConfigDict(from_attributes=True)` in a single `app/schemas.py`
- **Async SQLAlchemy** — `create_async_engine` + `AsyncSession`
- **DB access in routers/services** — `Depends(get_db)` + SQLAlchemy directly; business logic in `app/services/`. There is **no** repository layer.
- **NO MOCK DATA** — never use in-memory `dict`s; persist to Postgres
- **pytest-asyncio==0.24.0** — pinned version, do not upgrade

### Frontend
- **Next.js 14+ App Router** — pages in `frontend/app/`
- **Tailwind CSS** utility classes directly; `cn()` helper in `frontend/lib/utils.ts` (clsx + tailwind-merge); icons via `lucide-react`
- **Components** in `frontend/components/` — domain components (there is **no** `src/` dir and **no** pre-built `ui/` primitive library)
- **API client** in `frontend/lib/api.ts` — typed fetch wrapper
- **Environment variables** — `NEXT_PUBLIC_API_URL` baked at build time. Dockerfile MUST declare `ARG NEXT_PUBLIC_API_URL`.
- **DO NOT install the shadcn CLI or `@base-ui/react`** — they break the Tailwind v3 build; build components with plain Tailwind + `lucide-react`

### Docker
- **Backend:** `python:3.11-slim`, non-root `appuser`, port `8088`, healthcheck with `python urllib.request.urlopen('http://localhost:8088/health')`
- **Frontend:** `node:20-alpine`, port `3003`
- **Compose:** container port MUST match `EXPOSE`/`ENV PORT`

## Directory Structure

> The code is **flat** — single-file `models.py`/`schemas.py`, no `api/`,
> `core/`, `repositories/`, or `models/` package; the frontend has **no** `src/`.

```
dclaw-flow/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app, lifespan, /health, router includes
│   │   ├── config.py             # Settings (pydantic-settings)
│   │   ├── database.py           # Base = declarative_base(), engine, AsyncSessionLocal, get_db
│   │   ├── models.py             # Workflow, Execution, NodeExecution
│   │   ├── schemas.py            # Pydantic v2 request/response models
│   │   ├── seed.py               # sample workflow on first boot
│   │   ├── core/utils.py         # utc_now() etc.
│   │   ├── routers/              # workflows, executions, webhooks, copilot (prefix /api/v1/flows)
│   │   └── services/             # engine, executor, copilot, schema_inference, anomaly, retention
│   ├── alembic/versions/         # 001_initial, 002_webhook_path_index, 003_execution_status_index
│   ├── tests/                    # conftest.py + test_*.py (pytest-asyncio, httpx ASGITransport)
│   ├── Dockerfile                # python:3.11-slim, EXPOSE 8088
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── app/                      # Next.js App Router (workflows, workflows/[id], executions, executions/[id])
│   ├── components/               # flow-canvas, flow-node, node-palette, property-panel, copilot-widget
│   ├── lib/                      # api.ts (typed fetch), utils.ts (cn())
│   ├── types/index.ts
│   ├── public/dclaw-manifest.json
│   └── Dockerfile                # node:20-alpine, EXPOSE 3003
├── docker-compose.yml            # postgres / backend(8088) / frontend(3003)
├── .github/workflows/            # ci.yml (DO NOT DELETE) + Claude Code Action
├── helm/
└── .env.example
```

## UI Components

There is **no pre-built `ui/` primitive library** (no shadcn). The UI is built from
**plain Tailwind** utility classes plus `lucide-react` icons, with the `cn()` helper in
`frontend/lib/utils.ts` (clsx + tailwind-merge). Domain components live in
`frontend/components/`:

- `flow-canvas.tsx` — the React Flow (`@xyflow/react`) editor canvas + dagre auto-layout
- `flow-node.tsx` — custom per-type node (color + icon), validation/cleanup highlights
- `node-palette.tsx` — add-node sidebar
- `property-panel.tsx` — selected-node config + trigger/webhook config + Save
- `copilot-widget.tsx` — floating AI Copilot chat (mounted in `app/layout.tsx`)

Build new UI with Tailwind directly. Do NOT install the shadcn CLI or `@base-ui/react` —
they break the Tailwind v3 build. The Tailwind plugin in use is `@tailwindcss/forms`
(see `tailwind.config.ts`).

## Anti-Patterns — NEVER DO

| Anti-Pattern | Why It Breaks Things | Correct Alternative |
|--------------|---------------------|---------------------|
| A second `Base` / an `app/models/` package | Shadows `app/models.py` → `ImportError` on `from app.models import ...`; backend won't start | Keep the single `Base = declarative_base()` in `app/database.py` |
| `curl` in healthcheck on `python:*-slim` | No `curl` → silent failure | `python -c "import urllib.request; urllib.request.urlopen(...)"` |
| In-memory `MOCK_*` dicts | Data lost on restart | Persist via a real model + `Depends(get_db)` |
| Missing `ARG NEXT_PUBLIC_API_URL` | Wrong API URL baked in | Add `ARG NEXT_PUBLIC_API_URL` before build |
| Manual `get_db()` with `__anext__()` | Session leaks | `Depends(get_db)` |
| Hardcoded `localhost:PORT` | Breaks Docker/K8s | Use `process.env.NEXT_PUBLIC_API_URL` |
| No alembic migration for new models | Schema drift | `alembic revision --autogenerate` |
| **Installing `shadcn` CLI v4** | Breaks Tailwind v3 build | Build with plain Tailwind + `lucide-react` |
| **Using `@base-ui/react`** | Incompatible with Tailwind v3 | Build with plain Tailwind + `lucide-react` |
| **Using non-standard Postgres port in tests** | CI service maps 5432 only | Always use `localhost:5432` in conftest.py |
| **Upgrading `pytest-asyncio`** | v1.3.0 breaks fixture scoping | Keep `pytest-asyncio==0.24.0` pinned |
| **Deleting `.github/workflows/ci.yml`** | No CI runs, no quality gate | Leave CI workflow intact |
| **Missing `frontend/lib/utils.ts`** | Components fail to import `cn()` | Already in scaffold — do NOT delete |
| **Using `MappedAsDataclass` in `Base`** | Relationship/foreign-key sync conflicts on flush | Use plain `DeclarativeBase` only |
| **`default_factory` in `mapped_column()`** | SQLAlchemy interprets it as dataclass config; throws `ArgumentError` on plain `DeclarativeBase` | Use `default=` with a callable (e.g., `default=uuid.uuid4`) |
| **Timezone-aware `datetime` in models** | `DataError` with `TIMESTAMP WITHOUT TIME ZONE` | Use `utc_now()` from `app.core.utils` or `datetime.now(timezone.utc).replace(tzinfo=None)` |

## Database Rules

1. All models MUST import `Base` from `app.database` and use `Mapped[...]` + `mapped_column()`
2. **Never use `default_factory=` in `mapped_column()`** — use `default=` with a callable
3. Relationships SHOULD specify `lazy="selectin"` (async lazy-loads otherwise raise `MissingGreenlet` during response serialization)
4. All new tables MUST get an alembic migration
5. Use `ondelete="CASCADE"` for child tables; `ondelete="SET NULL"` for optional references

> ⚠️ Boot currently runs `Base.metadata.create_all` (in `main.py` lifespan), which
> creates tables but **not** indexes that exist only in migrations (e.g. the webhook-path
> index `002` and execution-status index `003`). For those to exist in a deployment you must
> run `alembic upgrade head`. Reconciling boot to migrations is an open decision.

## How to Add a Feature

1. **Read this file** and `REVISED-PRD.md` (the authoritative spec; `PLAN-v1.2.md` is a template)
2. **Backend:**
   - Add/update models in `app/models.py`
   - Add/update schemas in `app/schemas.py`
   - Business logic in `app/services/`
   - Add/update a router in `app/routers/` (mounted under `/api/v1/flows` in `app/main.py`)
   - Add tests in `tests/` and an alembic migration in `alembic/versions/` for new tables/indexes
3. **Frontend:**
   - Add API types in `frontend/types/index.ts` and client methods in `frontend/lib/api.ts`
   - Add a page in `frontend/app/` or a component in `frontend/components/` (plain Tailwind + `lucide-react`)
4. **Verify:** backend `pytest`, frontend `tsc --noEmit` + `next build`, and `docker compose config`
5. **Commit** with a conventional commit message

## Testing Requirements

- Every new service and router endpoint MUST be covered
- Use `pytest-asyncio` with `async` test functions and `@pytest.mark.asyncio`
- Use `httpx.AsyncClient` with `ASGITransport`
- `conftest.py` overrides `get_db` and builds the schema with `Base.metadata.create_all`
- Tests MUST use `localhost:5432` for PostgreSQL (CI requirement)

## Port Registry

| App | Backend | Frontend | Postgres DB |
|-----|---------|----------|-------------|
| dclaw-chat | 8090 | 3000 | dclaw_chat |
| dclaw-med | 8092 | 3004 | dclaw_med |
| dclaw-learn | 8093 | 3003 | dclaw_learn |
| dclaw-code | 8094 | 3005 | dclaw_code |
| dclaw-legal | 8099 | 3013 | dclaw_legal |
| dclaw-crm | 8095 | 3006 | dclaw_crm |
| dclaw-finance | 8096 | 3007 | dclaw_finance |
| dclaw-hr | 8097 | 3008 | dclaw_hr |
| dclaw-inventory | 8098 | 3009 | dclaw_inventory |
| dclaw-project | 8100 | 3010 | dclaw_project |
| dclaw-support | 8101 | 3014 | dclaw_support |
| dclaw-marketing | 8102 | 3015 | dclaw_marketing |
| dclaw-real-estate | 8103 | 3016 | dclaw_real_estate |
| dclaw-sales | 8104 | 3017 | dclaw_sales |
| dclaw-recruit | 8105 | 3018 | dclaw_recruit |
| dclaw-vendor | 8106 | 3019 | dclaw_vendor |
| dclaw-doc | 8107 | 3020 | dclaw_doc |
| dclaw-calendar | 8108 | 3021 | dclaw_calendar |
