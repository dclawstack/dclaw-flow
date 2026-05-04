# DClaw Flow

**Connect anything, automate everything**

Visual workflow automation platform built with Next.js and FastAPI.

## Architecture

```
dclaw-flow/
├── frontend/    → Next.js 14 (App Router), React Flow, Tailwind CSS
├── backend/     → FastAPI, Pydantic v2, SQLAlchemy 2.0, asyncpg
├── helm/        → Kubernetes manifests (future)
└── docker-compose.yml
```

## Quick Start

### Docker Compose (Recommended)

```bash
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8088
- API docs: http://localhost:8088/docs

### Local Development

**Backend**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Ensure PostgreSQL is running, then:
alembic upgrade head
uvicorn app.main:app --reload --port 8088
```

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

## Environment Variables

See `.env.example` in both `frontend/` and `backend/`.

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/flows/workflows` | CRUD | Workflow management |
| `/api/v1/flows/workflows/{id}/execute` | POST | Execute workflow |
| `/api/v1/flows/executions` | GET | List executions |
| `/api/v1/flows/executions/{id}/stream` | GET | SSE real-time status |
| `/api/v1/flows/webhooks/{webhook_id}` | POST | Webhook trigger |

## License

Proprietary — DClaw Stack
