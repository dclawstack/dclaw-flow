# E2E smoke test

A Playwright browser smoke test that loads the deployed (or local) DClaw Flow
app and asserts the key pages render. Kept out of `package.json` so it doesn't
slow the CI build (no browser download on `npm install`).

## Setup (one-time)

```bash
cd frontend
npm i -D playwright@^1.60
npx playwright install chromium
```

## Run

```bash
node e2e/smoke.mjs                          # production (dclaw-flow.vercel.app)
node e2e/smoke.mjs http://localhost:3003    # a local dev server
```

Exits non-zero if any check fails. Checks: home + nav, Copilot widget opens,
workflows list, workflow-editor canvas + rendered nodes, executions page, and
no uncaught page errors.

> Note: the editor check opens the first real workflow card, so it expects at
> least one workflow to exist (the seeded "Hello World Flow" satisfies this).
> On the free Render backend, allow for a ~20–60s cold start on the first hit.
