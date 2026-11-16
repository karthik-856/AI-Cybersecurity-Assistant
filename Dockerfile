FROM node:22-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements.lock.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.lock.txt
ENV PYTHONPATH=/install/lib/python3.12/site-packages
COPY models/zuka_unified_xgboost/ /app/models/zuka_unified_xgboost/
COPY scripts/prepare_model.py /app/scripts/prepare_model.py
RUN python scripts/prepare_model.py && rm models/zuka_unified_xgboost/model.json.gz

FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 libgomp1 curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
COPY --from=builder /app/models /app/models
COPY --from=frontend-builder /app/dist /app/frontend/dist
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1 APP_ENV=production ENABLE_IN_PROCESS_REPLAY=false
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
COPY backend/ /app/backend/
COPY data/sample*.csv /app/data/
COPY docs/ /app/docs/
COPY rag_assistant/ /app/rag_assistant/
COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY alembic.ini /app/alembic.ini
RUN useradd -u 1000 -m appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1
CMD ["python", "-m", "scripts.start_server"]
