FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uvicorn[standard]

COPY . .
RUN pip install --no-cache-dir .

EXPOSE 8088

# Apply migrations (so migration-only indexes exist) then serve. Render injects
# $PORT; locally it falls back to 8088 (matches docker-compose).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8088}"]
