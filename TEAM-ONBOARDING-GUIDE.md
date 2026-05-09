# Team Member Onboarding Guide — Building a DClaw App with Parallel Agents

> **Read this entire document before opening any agent tabs.**
> This guide assumes you have been assigned an app (e.g., `dclaw-crm`) and have write access to its GitHub repo.

---

## Table of Contents

1. [The Big Picture](#the-big-picture)
2. [What You Need Before Starting](#what-you-need-before-starting)
3. [Step 1: Prepare Your App Repo (Human — 5 minutes)](#step-1-prepare-your-app-repo-human--5-minutes)
4. [Step 2: Open 3 Agent Tabs (The Parallel Build)](#step-2-open-3-agent-tabs-the-parallel-build)
5. [Step 3: Merge & Test (Human — 10 minutes)](#step-3-merge--test-human--10-minutes)
6. [Lessons from Building 3 Apps](#lessons-from-building-3-apps)
7. [Troubleshooting Common Errors](#troubleshooting-common-errors)
8. [Checklist Before Saying "Done"](#checklist-before-saying-done)

---

## The Big Picture

You are building a web application. It has:
- **Backend** = the server that stores data (like a database + API)
- **Frontend** = the website users see and click on
- **Infrastructure** = Docker containers and deployment configs

Instead of building these one after another (slow), you build them **at the same time** using 3 separate AI agents in 3 browser tabs.

> **Important:** Each agent commits to a **separate branch** (`feat/backend`, `feat/frontend`, `feat/infra`), so they never conflict.

---

## What You Need Before Starting

| Item | What It Is | Where You Get It |
|------|-----------|-----------------|
| GitHub org invite | Access to `dclawstack` org | Your manager sends it |
| Assigned app name | e.g., `dclaw-crm` | Your manager tells you |
| Reserved ports | Backend + frontend port numbers | See port registry in `README.md` |
| `PRODUCT-SPEC.md` | A document describing YOUR app's features | You write this (see template below) |
| Coding agent access | Claude, Kimi, Cursor, etc. | Your team's tool |

---

## Step 1: Prepare Your App Repo (Human — 5 minutes)

This step sets up the "skeleton" that your 3 agents will flesh out.

### 1A. Clone the Scaffold Template

```bash
# Open your terminal
# Go to wherever you keep projects
cd ~/projects

# Clone the scaffold (this is the template)
git clone https://github.com/dclawstack/dclaw-scaffold.git dclaw-YOURAPP

# Example: if your app is "crm"
git clone https://github.com/dclawstack/dclaw-scaffold.git dclaw-crm
```

**What this does:** Copies the template into a new folder named after your app.

### 1B. Customize the Placeholders

The scaffold has placeholder text like `{APP_NAME}` and `{BACKEND_PORT}`. You must replace these with your actual values.

**Find/replace in these files:**

| File | What to Replace | Example (for CRM) |
|------|----------------|-------------------|
| `backend/app/core/config.py` | `DClaw App` → your name | `DClaw CRM` |
| `backend/app/api/main.py` | `DClaw App` → your name | `DClaw CRM` |
| `frontend/package.json` | `dclaw-app-frontend` | `dclaw-crm-frontend` |
| `frontend/src/app/layout.tsx` | `DClaw App` | `DClaw CRM` |
| `frontend/src/app/page.tsx` | `DClaw App` | `DClaw CRM` |
| `docker-compose.yml` | `8000` → backend port | `8095` |
| `docker-compose.yml` | `3000` → frontend port | `3006` |
| `docker-compose.yml` | `dclaw_app` → DB name | `dclaw_crm` |
| `AGENTS.md` | `{APP_NAME}`, ports, DB | Fill all placeholders |
| `PLAN-v1.2.md` | `{APP_NAME}` | Your app name |
| `README.md` | `{APP_NAME}` | Your app name |
| `.env.example` | `8000`, `3000`, `dclaw_app` | Your ports and DB |
| `backend/Dockerfile` | `8000` | `8095` |
| `frontend/Dockerfile` | `3000` | `3006` |
| `helm/Chart.yaml` | `dclaw-app` | `dclaw-crm` |
| `helm/values.yaml` | `dclaw-app` | `dclaw-crm` |

**Quick way to do all replacements:**
```bash
cd dclaw-YOURAPP

# Replace app name (run for YOUR name)
sed -i '' 's/DClaw App/DClaw CRM/g' backend/app/core/config.py backend/app/api/main.py frontend/src/app/layout.tsx frontend/src/app/page.tsx

# Replace ports (example: 8095 backend, 3006 frontend)
sed -i '' 's/8000/8095/g' docker-compose.yml backend/Dockerfile .env.example
sed -i '' 's/3000/3006/g' docker-compose.yml frontend/Dockerfile .env.example

# Replace DB name
sed -i '' 's/dclaw_app/dclaw_crm/g' docker-compose.yml backend/app/core/config.py .env.example
```

### 1C. Write Your PRODUCT-SPEC.md

This is **the most important document**. It tells the agents WHAT to build.

Create a file called `PRODUCT-SPEC.md` in your app folder:

```bash
cd dclaw-YOURAPP
touch PRODUCT-SPEC.md
```

Paste this template and fill it in:

```markdown
# PRODUCT-SPEC: YOURAPP

## Overview
**App Name:** YOURAPP
**Domain:** What industry? (e.g., CRM, Finance, HR)
**Target User:** Who uses it? (e.g., sales teams, accountants)

## Core Entities
List your main data models. For each:
- Name of the thing (e.g., Customer, Invoice, Employee)
- Fields (name, type, required or optional)
- Relationships to other things

Example:
### Customer
- id: UUID (auto-generated)
- name: text (required)
- email: text (required, must be unique)
- status: choice of ["lead", "active", "churned"]

## Screens / Pages
List every screen users will see:
1. Dashboard — what charts, numbers, quick actions?
2. List page — table of items, search, filters
3. Detail page — view one item, edit, delete
4. Any other pages

## API Endpoints
List the backend URLs needed:
- GET /api/v1/customers → list all
- POST /api/v1/customers → create one
- etc.

## AI Features (if any)
What should the AI do? (e.g., "predict deal closing probability")
```

**Tips for a good PRODUCT-SPEC:**
- Be specific. "A customer page" is bad. "A page showing customer name, email, company, and a table of their deals" is good.
- List 2-4 main entities max for v1.0. Don't over-engineer.
- Copy the examples from `dclaw-crm`, `dclaw-finance`, or `dclaw-hr`.

### 1D. Push to GitHub

```bash
cd dclaw-YOURAPP

# Set the remote to YOUR repo (not the scaffold)
git remote set-url origin https://github.com/dclawstack/dclaw-YOURAPP.git

# Add everything
git add -A

# Commit
git commit -m "chore: customize scaffold for YOURAPP app"

# Push
git push origin main
```

**What this does:** Saves your skeleton to GitHub so the agents can pull from it.

---

## Step 2: Open 3 Agent Tabs (The Parallel Build)

This is where the magic happens. You open **3 separate conversations** with your AI coding agent. Each gets a different job.

> **Important:** Give each agent the SAME starting info:
> - The repo path: `~/projects/dclaw-YOURAPP`
> - The full text of your `PRODUCT-SPEC.md`
> - The anti-patterns list from `AGENTS.md`

---

### Tab 1: Backend Architect

**What this agent builds:**
1. **Models** → Database table definitions (e.g., `Customer` table with name, email, status columns)
2. **Schemas** → Validation rules (e.g., "email must be unique", "status must be lead/active/churned")
3. **Repositories** → Database query helpers (e.g., `get_customer_by_id()`, `list_all_customers()`)
4. **Routers** → HTTP API endpoints (e.g., `GET /api/v1/customers` returns JSON list)
5. **Tests** → Automated checks that prove the API works
6. **Alembic migration** → A file that creates the database tables

**What you give it:**
- The repo path
- Your `PRODUCT-SPEC.md`
- The anti-patterns list

**What you get back:**
- A working FastAPI backend
- All CRUD endpoints testable with `pytest`
- Database migration ready to run

**Branch:** `feat/backend`

**Copy-paste this prompt into Tab 1:**

```
You are the Backend Architect for the DClaw YOURAPP app.

REPO PATH: /Users/YOURNAME/projects/dclaw-YOURAPP

## Your Task
Build the COMPLETE backend for this app. Read the PRODUCT-SPEC.md in the repo for the exact entities and API endpoints needed.

## Stack Rules (NEVER violate these)
1. All models MUST inherit from Base in app/models/base.py (DeclarativeBase)
2. NEVER use declarative_base() — this breaks everything
3. NEVER use in-memory dicts for data storage
4. All models MUST use Mapped[...] and mapped_column()
5. Relationships MUST use lazy="selectin"
6. All repositories MUST accept AsyncSession in __init__
7. All routers MUST use Depends(get_db)
8. Pydantic schemas MUST use ConfigDict(from_attributes=True)
9. Generate alembic migration after creating models: alembic revision --autogenerate -m "initial"
10. Write tests for ALL endpoints using pytest-asyncio and @pytest.mark.asyncio
11. tests/conftest.py MUST use localhost:5432 for PostgreSQL (CI requirement)
12. Keep pytest-asyncio==0.24.0 — do NOT upgrade
13. NEVER delete .github/workflows/ci.yml

## Step-by-Step Instructions
1. Read /Users/YOURNAME/projects/dclaw-YOURAPP/PRODUCT-SPEC.md
2. Create models in app/models/ (one file per entity)
3. Create schemas in app/schemas/ (Create, Update, Response classes)
4. Create repositories in app/repositories/ (CRUD methods)
5. Create routers in app/api/v1/ (HTTP endpoints)
6. Wire routers in app/api/main.py
7. Generate alembic migration
8. Write tests in tests/
9. Run pytest to verify everything passes
10. Commit all changes with: git add -A && git commit -m "feat: add backend models, API, and tests"
11. Push: git push origin feat/backend

## Anti-Patterns to Avoid
- declarative_base() → use Base from app.models.base
- In-memory MOCK_* dicts → use real repositories
- Manual get_db() with __anext__() → use Depends(get_db)
- Skipping alembic migrations → always generate one
- Changing postgres port in tests → keep localhost:5432

Report back with:
- Did pytest pass? How many tests?
- List of files you created
```

---

### Tab 2: Frontend Builder

**What this agent builds:**
1. **Pages** → What users see:
   - `/` → Dashboard with charts and summary cards
   - `/customers` → Table with search, filters, pagination
   - `/customers/123` → Detail page for one customer
   - `/customers/new` → Form to create a customer
2. **Components** → Reusable UI pieces (buttons, cards, forms, tables)
3. **API client** → Code that talks to the backend (`fetch('/api/v1/customers')`)
4. **Styling** → Tailwind CSS classes for layout, colors, responsiveness

**What you give it:**
- The repo path
- Your `PRODUCT-SPEC.md`
- The backend API contract (from Tab 1's output)

**What you get back:**
- A working Next.js website
- All screens connected to real backend data
- `npm run build` passes

**Branch:** `feat/frontend`

**Copy-paste this prompt into Tab 2:**

```
You are the Frontend Builder for the DClaw YOURAPP app.

REPO PATH: /Users/YOURNAME/projects/dclaw-YOURAPP

## Your Task
Build the COMPLETE frontend for this app. Read the PRODUCT-SPEC.md in the repo for the screens and user flows.

## Stack Rules (NEVER violate these)
1. Next.js 14 App Router
2. Tailwind CSS for styling
3. UI components from src/components/ui/ — these are pre-built and work. DO NOT install shadcn CLI or @base-ui/react.
4. API calls MUST go through src/lib/api.ts
5. NEVER hardcode "http://localhost:8000" — use process.env.NEXT_PUBLIC_API_URL
6. NEVER use mock/in-memory data — call the real backend API
7. npm run build MUST pass before you finish
8. ALWAYS commit package-lock.json after npm install
9. NEVER delete .github/workflows/ci.yml

## Pre-Built Components Available
- Button, Card, Input, Label, Badge, Select, Dialog, Table, Tabs, Avatar
Import them like: import { Button } from "@/components/ui/button"

## Step-by-Step Instructions
1. Read /Users/YOURNAME/projects/dclaw-YOURAPP/PRODUCT-SPEC.md
2. Read the backend API routers to know the exact endpoints (check app/api/v1/)
3. Update src/lib/api.ts with API functions for your endpoints
4. Create pages in src/app/:
   - / → Dashboard
   - /customers → List page (or whatever your entity is)
   - /customers/[id] → Detail page
   - /customers/new → Create form
   - Add more pages as needed
5. Run npm run build
6. Commit with: git add -A && git commit -m "feat: add frontend pages and components"
7. Push: git push origin feat/frontend

## Anti-Patterns to Avoid
- Hardcoded localhost:PORT → use NEXT_PUBLIC_API_URL
- Mock data → call real API
- Forgetting package-lock.json → commit it
- Breaking the build → npm run build must pass
- Installing shadcn v4 → use pre-built components

Report back with:
- Did npm run build pass?
- List of pages you created
- Any API endpoint mismatches you found
```

---

### Tab 3: DevOps Engineer

**What this agent builds/fixes:**
1. **Backend Dockerfile** → Python container with correct port, non-root user, healthcheck
2. **Frontend Dockerfile** → Node container with `ARG NEXT_PUBLIC_API_URL` (critical!)
3. **docker-compose.yml** → Ties backend + frontend + database together with correct ports
4. **Helm chart** → Kubernetes deployment configs
5. **GitHub Actions** → CI that runs tests on every push

**What you give it:**
- The repo path
- Your reserved backend/frontend ports
- The anti-patterns list

**What you get back:**
- `docker-compose up -d` starts everything
- All healthchecks pass
- CI config is valid

**Branch:** `feat/infra`

**Copy-paste this prompt into Tab 3:**

```
You are the DevOps Engineer for the DClaw YOURAPP app.

REPO PATH: /Users/YOURNAME/projects/dclaw-YOURAPP
BACKEND PORT: YOUR_BACKEND_PORT (e.g., 8095)
FRONTEND PORT: YOUR_FRONTEND_PORT (e.g., 3006)

## Your Task
Verify and fix all infrastructure configuration for this app.

## Stack Rules (NEVER violate these)
1. Backend Dockerfile: python:3.11-slim, non-root appuser
2. Frontend Dockerfile: MUST have ARG NEXT_PUBLIC_API_URL before RUN npm run build
3. Backend healthcheck: python -c "import urllib.request; urllib.request.urlopen('http://localhost:PORT/health/')"
4. Frontend healthcheck: wget -q --spider http://localhost:PORT/
5. docker-compose.yml ports must match the app's reserved ports
6. Helm chart must reference the correct app name and image repos
7. NEVER delete .github/workflows/ci.yml

## Step-by-Step Instructions
1. Read /Users/YOURNAME/projects/dclaw-YOURAPP/PRODUCT-SPEC.md
2. Verify backend/Dockerfile:
   - Uses python:3.11-slim
   - Has non-root appuser
   - Exposes the correct backend port
   - Healthcheck uses urllib.request (NOT curl)
3. Verify frontend/Dockerfile:
   - Has ARG NEXT_PUBLIC_API_URL before RUN npm run build
   - Exposes the correct frontend port
4. Verify docker-compose.yml:
   - Backend port mapping is correct (e.g., 8095:8095)
   - Frontend port mapping is correct (e.g., 3006:3006)
   - Database name is correct
   - Healthchecks are correct
5. Verify helm/Chart.yaml, helm/values.yaml, helm/templates/:
   - App name is correct
   - Image repository names are correct
   - Ports are correct
6. Verify .github/workflows/ci.yml exists and is valid
7. Update .env.example with app-specific defaults
8. Commit all changes to branch feat/infra

## Anti-Patterns to Avoid
- curl in python:*-slim healthchecks → use urllib.request
- Missing ARG NEXT_PUBLIC_API_URL → add it before build
- Wrong ports in docker-compose → match the reserved ports
- Deleting CI workflow → keep it

Report back with:
- Did docker-compose config pass?
- List of files you modified
```

---

## Step 3: Merge & Test (Human — 10 minutes)

After all 3 agents finish, you combine their work.

### 3A. Pull All Branches

```bash
cd dclaw-YOURAPP

# Fetch all branches
git fetch origin

# See what the agents created
git branch -a
```

You should see:
- `origin/feat/backend`
- `origin/feat/frontend`
- `origin/feat/infra`

### 3B. Merge Everything

```bash
# Switch to main
git checkout main

# Merge all three branches
git merge origin/feat/backend origin/feat/frontend origin/feat/infra

# If there are conflicts (rare), the agents touched different files
# so just accept both changes:
# git add -A && git merge --continue
```

**What this does:** Combines all 3 agents' work into one codebase.

### 3C. Test Locally

```bash
# Validate docker-compose config
docker-compose config

# If valid, try starting everything
docker-compose up -d

# Wait 30 seconds, then check health
curl http://localhost:YOUR_BACKEND_PORT/health/
# Should return: {"status":"ok"}

# Check frontend
curl http://localhost:YOUR_FRONTONT_PORT/
# Should return HTML

# Check all services are healthy
docker-compose ps
```

### 3D. Push to GitHub

```bash
git push origin main
```

Go to `https://github.com/dclawstack/dclaw-YOURAPP/actions` and verify the CI turns green.

---

## Lessons from Building 3 Apps

We built `dclaw-crm`, `dclaw-finance`, and `dclaw-hr` using parallel agents. Here's what we learned:

### Lesson 1: shadcn v4 Breaks Everything

**What happened:** Agents installed `shadcn` npm package v4 and `@base-ui/react`. These are designed for Tailwind v4 and break Tailwind v3 builds with cryptic CSS errors.

**Time wasted:** Each agent spent 20+ minutes retrying `npm install` and `npm run build` before timing out.

**Fix:** The scaffold now includes pre-built UI components that work with Tailwind v3. Agents should use these directly instead of installing shadcn CLI.

### Lesson 2: pytest-asyncio Version Hell

**What happened:** `pytest-asyncio>=0.24.0` in requirements.txt installed version `1.3.0` which behaves differently from `0.24.x`. Session-scoped fixtures failed, repo tests couldn't find `db_session`.

**Fix:** Pinned to `pytest-asyncio==0.24.0` in requirements.txt.

### Lesson 3: Postgres Port Mismatch in CI

**What happened:** Agents hardcoded non-standard postgres ports (5433, 5434, 5435) in `conftest.py`, but GitHub Actions service always maps to 5432.

**Fix:** Enforced `localhost:5432` in conftest.py template.

### Lesson 4: Agents Delete CI Workflows

**What happened:** Two out of three agents deleted `.github/workflows/ci.yml` during their work.

**Fix:** Added "DO NOT DELETE" rule to AGENTS.md.

### Lesson 5: 30-Minute Timeout Is Tight

**What happened:** All 3 agents timed out after 30 minutes because they spent too much time on the shadcn issue.

**Recommendation:** Give agents smaller, focused tasks instead of "build everything":
- Task 1: Models + schemas (10 min)
- Task 2: Repositories + routers (10 min)
- Task 3: Frontend pages (10 min)

---

## Troubleshooting Common Errors

| Error | What It Means | Fix |
|-------|--------------|-----|
| `npm ci` fails | Missing `package-lock.json` | Run `npm install` and commit the lockfile |
| `next build` fails | TypeScript or CSS error | Check `src/lib/api.ts` for bad imports; verify no `@base-ui/react` imports |
| `pytest` fails | Backend test error | Check that `get_db` is overridden in `conftest.py`; verify port is 5432 |
| `fixture 'db_session' not found` | Missing fixture in conftest.py | Add `db_session` fixture if repo tests need it |
| Port conflict | Two apps use same port | Use port registry, never reuse |
| Git push rejected | Remote has newer commits | Run `git pull --rebase` then push |
| `curl not found` | Wrong healthcheck | Use `python urllib.request.urlopen()` |
| `border-border` class error | shadcn v4 CSS in globals.css | Use the scaffold's globals.css template |

---

## Checklist Before Saying "Done"

- [ ] `docker-compose up -d` starts all 3 services
- [ ] Backend health endpoint returns `{"status":"ok"}`
- [ ] Frontend loads at `http://localhost:YOUR_FRONTEND_PORT`
- [ ] You can create/read/update/delete at least one entity through the UI
- [ ] `pytest` passes in `backend/`
- [ ] `npm run build` passes in `frontend/`
- [ ] GitHub Actions CI is green
- [ ] `AGENTS.md` and `PLAN-v1.2.md` are customized (no `{APP_NAME}` placeholders)
- [ ] `package-lock.json` is committed
- [ ] No in-memory `MOCK_*` dicts exist in the codebase
- [ ] `.github/workflows/ci.yml` exists and was not deleted

---

## Example Timeline

| Time | What Happens |
|------|-------------|
| 0:00 | You write PRODUCT-SPEC.md and push scaffold |
| 0:05 | Open 3 agent tabs, paste prompts |
| 0:10 | Tab 3 (DevOps) finishes |
| 0:20 | Tab 1 (Backend) finishes |
| 0:25 | Tab 2 (Frontend) finishes |
| 0:30 | You merge branches |
| 0:35 | You test with docker-compose |
| 0:40 | Push to GitHub, CI runs |
| 0:45 | **App is live** |

**Total time: ~45 minutes** (vs. ~4 hours if built serially)
