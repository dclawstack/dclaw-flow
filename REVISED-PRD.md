---
tags: [meta, prd, revised, swarm]
version: 2.3
date: 2026-05-16
app_id: flow
app_name: DClaw Flow
category: Automation
status: P0
---

# 📘 DClaw Flow — Revised PRD v2.3

> **The single document every agent must read before writing code for this app.**
> Generated from DClaw Master PRD v2.2. Read the Master PRD first: https://raw.githubusercontent.com/dclawstack/dclaw-prd/main/DClaw-Master-PRD.md

---

## 1. Product Identity

| Field | Value |
|-------|-------|
| **App ID** | `flow` |
| **Name** | DClaw Flow |
| **Category** | Automation |
| **Tagline** | Connect anything, automate everything |
| **Color** | #10B981 |
| **Phase** | P0 |
| **Port (Frontend Dev)** | 3003 (Assigned) |
| **Port (Backend Dev)** | 8088 (Assigned) |
| **Maturity Tier** | 🟡 Tier 2 — Partial |

---

## 2. Current State Assessment

### 2.1 Scaffold Status
| Component | Status | Notes |
|-----------|--------|-------|
| `frontend/` | ✅ | Next.js 14+ app |
| `backend/` | ✅ | FastAPI + SQLAlchemy 2.0 |
| `docs/` | ✅ | getting-started, guides, reference, releases |
| `helm/` | ✅ | K8s deployment manifests |
| `.github/workflows/` | ✅ | CI/CD + Claude integration |
| `AGENTS.md` | ✅ | Per-repo agent instructions |
| `PLAN-v1.2.md` | ✅ | Feature roadmap |
| `docker-compose.yml` | ✅ | Local dev stack |
| `tests/` | ✅ | pytest + pytest-asyncio |
| `alembic/` | ✅ | Database migrations |
| `dclaw-manifest.json` | ✅ | DPanel registration |

### 2.2 Code Maturity
| Metric | Value |
|--------|-------|
| Python source files (backend) | ~22 |
| TypeScript/TSX files (frontend) | ~13 |
| Total source files | ~35 |
| Tests | ✅ Present |
| Alembic migrations | ✅ Present |
| DPanel manifest | ✅ Present |

### 2.3 Feature Maturity
- **P0 Foundation:** Partially implemented
- **P1 Platform:** Not yet started
- **P2 Vertical:** Not yet started

---

## 3. Gap Analysis

| # | Gap | Severity | Fix |
|---|-----|----------|-----|
| 1 | Partial implementation — needs more domain features | 🟡 | Expand backend services and frontend pages per P0 roadmap |

---

## 4. Sacred Architecture & Tech Stack

> **NON-NEGOTIABLE. Every DClaw product MUST use this exact stack.**

| Layer | Technology | Version |
|-------|------------|---------|
| **Frontend** | Next.js 14+ | App Router, Tailwind CSS, shadcn/ui |
| **Backend** | FastAPI | Pydantic v2, SQLAlchemy 2.0, asyncpg |
| **Database** | PostgreSQL 16 | CloudNativePG operator in K8s |
| **Vector DB** | Qdrant / pgvector | Only if RAG / semantic search |
| **Cache / Bus** | Redis | 7.x |
| **Object Storage** | MinIO | Latest |
| **Workflow** | Temporal.io | Only if automation/orchestration |
| **Auth** | Logto | JWT validation on all protected routes |
| **Billing** | Stripe | Metered or per-seat |
| **K8s Operator** | Go + controller-runtime | 0.18 |
| **LLM Local** | Ollama | Apple Silicon |
| **LLM Cloud** | OpenRouter + Kimi K2.5 | Fallback |
| **Monitoring** | Prometheus + Grafana | Latest |

### 4.1 Python Rules
- `ruff` formatting enforced
- Type hints on ALL public APIs
- `pydantic` v2 for schemas
- `sqlalchemy` 2.0 style (`Mapped`, `mapped_column`)
- `pytest` + `pytest-asyncio` for tests
- Functions < 50 lines
- No `print()` — use `structlog`

### 4.2 TypeScript / Next.js Rules
- Strict TypeScript (`strict: true`)
- Tailwind for ALL styling
- `cn()` utility for conditional classes
- No `any` without `// @ts-ignore`

### 4.3 Docker Standards
- Port mappings MUST match container listen port
- Healthchecks MUST use binaries present in base image
- `docker compose config` must pass before shipping
- Service type MUST be `ClusterIP`
- TLS required on all ingress

---

## 5. P0 Foundation Features (Must Have — Demo Ready)

> **Every P0 MUST include an AI Copilot per YC S25/W26 RFS.**

| # | Feature | Description | AI Component | Acceptance Criteria |
|---|---------|-------------|--------------|---------------------|
| P0.1 | **AI Flow Copilot** ✅ | Describe automation in natural language; AI builds the workflow. | LLM workflow generation + node suggestion | Generate valid workflow from description in <10s |
| P0.2 | **Visual Workflow Builder** ✅ | Drag-and-drop canvas for building multi-step automations. | AI layout optimization + path simplification | Canvas supports 50+ nodes; real-time validation |
| P0.3 | **HTTP Webhook Triggers** ✅ | Trigger flows from external services via webhooks. | AI webhook schema inference + payload validation | Webhook ingestion latency <100ms; auto-generate OpenAPI spec |
| P0.4 | **Execution History & Logs** ✅ | Full audit trail of every workflow run with step-level logs. | AI anomaly detection in execution patterns | Retain 90 days of history; query by status, date, or step |

> **P0.1 status (implemented):** Endpoints under `/api/v1/flows/copilot`:
> `POST /generate` turns a natural-language description into a validated
> workflow (and persists it); `POST /suggest/{workflow_id}` recommends next
> nodes; `POST /chat` is a contextual assistant grounded in the user's
> workflows that answers questions and drafts workflows from chat. Provider
> order is local Ollama → cloud OpenRouter → a deterministic heuristic fallback
> (`COPILOT_PROVIDER` env), so it always responds offline / in CI. UI: a
> "Build with AI Copilot" panel on `frontend/app/workflows/new` plus a floating
> **Copilot chat widget on every page** (`frontend/components/copilot-widget.tsx`,
> mounted in the root layout). Service: `backend/app/services/copilot.py`.
>
> Mandate (§9) coverage: contextual awareness ✅ (chat is grounded in the user's
> workflows), suggests next actions ✅, accessible from every page ✅, Ollama
> fallback ✅. RAG (§9.2) is N/A — no knowledge base for this app per the
> "only if RAG/semantic search" stack rule.

> **P0.2 status (implemented):** The React Flow canvas
> (`frontend/components/flow-canvas.tsx`) now persists drag positions, node and
> edge deletions through Save (fixed a backend PATCH 500 in
> `workflows.py` that made saving the graph impossible). Real-time validation
> runs on change (`frontend/lib/validation.ts`, mirroring the engine rules) with
> inline red/amber node highlights and a Save error badge; the server `/validate`
> is the authority on Save. Deterministic **auto-layout** via dagre
> (`frontend/lib/layout.ts`) arranges 50+ nodes (LLM-driven layout deferred to
> P1). Per-type colored nodes (`frontend/components/flow-node.tsx`).
> **Path simplification** ships as non-destructive cleanup hints — unreachable
> nodes are highlighted and listed with per-node delete (mirrors
> `engine.find_unreachable_nodes`, tested). Save UX: toast + dirty-state.

> **P0.3 status (implemented):** Webhooks now accept **raw arbitrary JSON**
> (no `{"data":...}` wrapper) at `POST /api/v1/flows/webhooks/{path}`, matched
> by an **indexed** lookup (`trigger -> 'config' ->> 'path'`, migration `002`)
> instead of a scan — single-request ingestion is well under 100ms (tested).
> **Deterministic schema inference** (`services/schema_inference.py`): the first
> payload defines the schema (stored on `trigger.config.inferred_schema`); later
> payloads are validated and **flagged but never blocked** (response carries
> `schema_valid`/`schema_errors`). `GET /webhooks/{path}/schema` exposes it (the
> auto-OpenAPI fragment). HMAC signature verification is opt-in via a secret.
> UI: the property panel configures path/secret, shows a **copyable webhook URL**
> and the inferred schema; the editor has an **Activate/Pause** toggle (webhooks
> fire only for active workflows). LLM-assisted inference + replay protection are
> deferred to P1.

> **P0.4 status (implemented):** `GET /executions` now filters server-side by
> **status, date range, and step** (`node_id`); added a `(status, started_at)`
> index (migration `003`) and made `node_executions` eager-loaded (`selectin`,
> which also fixed an async lazy-load hazard). New **`/executions/[id]` detail
> page** shows metadata, anomaly flags, and per-step logs (input/output/error).
> **Deterministic anomaly detection** (`services/anomaly.py`,
> `GET /executions/{id}/anomalies`): slow-run outliers, repeated-failure streaks,
> failing-node flags — no LLM. **90-day retention** via
> `delete_executions_older_than` + a token-guarded
> `POST /executions/admin/cleanup` and a documented cron
> (`docs/guides/execution-retention.md`); no in-cluster scheduler (P1). The SSE
> stream now emits valid JSON and terminates correctly (two bugs fixed); live
> step streaming in the UI is deferred to P1.

---

## 6. P1 Platform Features (Should Have — v1.1–1.2)

| # | Feature | Description | AI Component | Acceptance Criteria |
|---|---------|-------------|--------------|---------------------|
| P1.1 | **Temporal.io Integration** | Durable workflow execution with retries, timeouts, and sagas. | AI retry-policy recommendation | Support long-running workflows; automatic saga compensation |
| P1.2 | **100+ Connectors** | Pre-built integrations for Slack, GitHub, Salesforce, Stripe, etc. | AI connector health monitoring | OAuth-based auth; connectors auto-tested weekly |
| P1.3 | **Conditional Logic & Branching** 🟡 | If/else, loops, and parallel execution in workflows. | AI branch-coverage analysis + dead-path detection | Visual condition builder; parallel execution up to 10 branches |
| P1.4 | **Error Handling & Alerts** 🟡 | Smart retries, fallback paths, and PagerDuty/Slack alerts. | AI root-cause analysis for failed steps | 3 retry strategies; alert within 30s of failure |

---

> **P1.3 status (in progress):** Conditional **branching now executes** —
> `executor.py` traverses only active edges from the trigger and records untaken
> nodes as `skipped`. Branch model is **edge-condition expressions**: an edge is
> active when its `condition` is empty (always) or resolves truthy (e.g.
> `{{node.field}}`); a `conditional` node exposes `{{c.result}}` / `{{c.else}}`
> for if/else. Edges with no condition are always active, so existing/linear
> flows are unchanged. Deferred: canvas edge-condition **authoring UI** (next
> PR), comparison operators, parallel/loop execution, and AI branch-coverage
> hints (later phases).

> **P1.4 status (in progress):** **Per-node retries** ship. A node carries an
> optional `retry` policy (`max_attempts` clamped 1–10, `backoff_strategy`
> none/fixed/exponential, `backoff_seconds`); the executor retries a failed node
> with backoff and records **one `NodeExecution` row per attempt**
> (`attempt_number`, migration `004`). HTTP actions now **raise on transport
> errors and 5xx** (retriable); 4xx still flows through as output to branch on.
> No `retry` config = 1 attempt (unchanged). Deferred (Phase 2+): fallback/error
> branches, Slack/webhook **alerts**, AI root-cause analysis, and the
> retry-policy authoring UI.

> **P1.4 status (phase 2 — fallback paths):** Edges now carry a `kind`
> (`normal` | `error`, default `normal`). When a node fails (after retries),
> the executor follows its **error edges** to a recovery path instead of
> failing the run; the failed node's error is exposed as
> `{{node.error}}`/`{{node.failed}}` for error edges and recovery nodes. A
> failure with no firing error edge still fails the execution (unchanged). A
> recovered run is `completed` (the failure stays visible in the per-node
> rows). Deferred: Slack/webhook **alerts**, AI root-cause, and the
> error-edge + retry **authoring UI**.

## 7. P2 Vertical / Scale Features (Could Have — v1.3+)

| # | Feature | Description | AI Component | Acceptance Criteria |
|---|---------|-------------|--------------|---------------------|
| P2.1 | **Custom Code Nodes** | Run Python/TypeScript code inside workflows. | AI code suggestion + linting | Sandboxed execution; 5s timeout; access to flow context |
| P2.2 | **Workflow Marketplace** | Share and discover community-built workflows. | AI recommendation engine based on usage patterns | Rate + review workflows; one-click import |
| P2.3 | **Multi-Tenant Execution** | Isolate workflow executions per organization. | AI resource-quota optimization | Namespace isolation; per-tenant concurrency limits |
| P2.4 | **AI Document Processing** | Extract data from PDFs, images, and emails in workflows. | Vision-language model + structured extraction | Support PDF, PNG, JPG; extract to JSON schema |

---

## 8. Scaffold Checklist

Before marking this app "shipped", confirm:

- [ ] `frontend/` with Next.js 14+, Tailwind, shadcn/ui
- [ ] `backend/` with FastAPI, Pydantic v2, SQLAlchemy 2.0, asyncpg
- [ ] `docs/` with getting-started, guides, reference, releases, troubleshooting
- [ ] `helm/` with Chart.yaml, values.yaml, templates (deployment, service, ingress, cloudnativepg)
- [ ] `.github/workflows/` with build-backend.yml, build-frontend.yml, deploy.yml, claude.yml
- [ ] `frontend/public/dclaw-manifest.json` for DPanel registration
- [ ] `backend/tests/` with pytest + pytest-asyncio
- [ ] `backend/alembic/` with initial migration
- [ ] `Dockerfile` + `docker-compose.yml` with correct healthchecks
- [ ] Health endpoint at `/health` returning `{"status":"ok"}`
- [ ] `AGENTS.md` with per-repo instructions
- [ ] `PLAN-v1.2.md` with feature roadmap
- [ ] Port assigned from registry and documented
- [ ] No hardcoded secrets — use `.env.example` + K8s Secrets
- [ ] Non-root containers in Dockerfile

---

## 9. AI Copilot Mandate (YC S25/W26 Requirement)

Every DClaw app MUST have an AI Copilot as its first P0 feature. The copilot must:
1. Be contextually aware of the app's domain data
2. Use RAG over the app's knowledge base where applicable
3. Suggest next actions, not just answer questions
4. Be accessible from every page via floating chat or sidebar
5. Fall back to local Ollama when cloud is unavailable

---

## 10. Next Tasks for Vibe Coders

1. **Complete P0 features**: Finish any incomplete P0 backend services and frontend pages.
2. **Add missing scaffold**: Fill gaps identified above (docs, helm, tests, manifest, etc.).
3. **Start P1 features**: Implement the first 2 P1 features to deepen domain capability.
4. **Polish and integrate**: Ensure health endpoints, Docker builds, and DPanel manifest are production-ready.

---

## 11. Domain Research Notes

Inspired by Zapier, Make, n8n, Temporal. YC loves automation: high ROI, clear value prop, viral loops via templates.

---

## 12. Links & Resources

| Resource | URL |
|----------|-----|
| **Master PRD** | https://raw.githubusercontent.com/dclawstack/dclaw-prd/main/DClaw-Master-PRD.md |
| **GitHub Org** | https://github.com/dclawstack |
| **DPanel** | https://dpanel.dclawstack.io |
| **Port Registry** | See `dclaw-platform/PORT_REGISTRY.md` |
| **App PRD Template** | Obsidian Vault → `00-META/📐 App PRD Template.md` |
| **Scaffold Source** | `dclaw-scaffold/` in DClaw-Stack |

---

*Revised PRD version: 2.3*
*Generated: 2026-05-16 by DClaw Stack Generator*
*Next review: When P0 features are complete or architecture changes*
