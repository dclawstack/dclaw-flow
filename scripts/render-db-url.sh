#!/usr/bin/env bash
# Print the Neon connection string in the asyncpg form Render needs.
#
# Reads the gitignored frontend/.env.local (pulled by the Vercel/Neon
# integration) at runtime — no secret is stored in this script or the repo.
# Use it to copy DATABASE_URL into the Render dashboard:
#
#   bash scripts/render-db-url.sh
#
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f frontend/.env.local ]; then
  echo "frontend/.env.local not found — run: vercel env pull --cwd frontend" >&2
  exit 1
fi

python3 - <<'PY'
import re
env = {}
for line in open("frontend/.env.local"):
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        env[k] = v.strip().strip('"').strip("'")
# Direct (unpooled) endpoint — best for a long-running SQLAlchemy backend.
url = env.get("DATABASE_URL_UNPOOLED") or env["DATABASE_URL"]
url = re.sub(r"^postgres(ql)?://", "postgresql+asyncpg://", url)
# asyncpg rejects libpq sslmode/channel_binding params; use ssl=require.
print(url.split("?", 1)[0] + "?ssl=require")
PY
