# ==============================================================================
# ZUKA SOC BACKEND DOCKERFILE
# ==============================================================================
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.lock.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.lock.txt

# --- Runtime Stage ---
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

COPY backend/ /app/backend/
COPY models/ /app/models/
COPY data/ /app/data/
COPY docs/ /app/docs/
COPY rag_assistant/ /app/rag_assistant/
COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY alembic.ini /app/alembic.ini

# Create unprivileged application user
RUN useradd -u 1000 -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]


