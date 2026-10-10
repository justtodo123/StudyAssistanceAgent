# ===== 构建阶段 =====
FROM python:3.12-slim AS builder

WORKDIR /build

COPY platform/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ===== 运行阶段 =====
FROM python:3.12-slim

LABEL maintainer="StudyAssistanceAgent"
LABEL description="FastAPI RAG backend for learning assistance"

RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

WORKDIR /app

COPY --from=builder /install /usr/local

COPY platform/app ./app
COPY knowledge ./knowledge

RUN mkdir -p /app/.cache && chown -R app:app /app

USER app

ENV SA_KNOWLEDGE_ROOT=/app/knowledge \
    SA_VECTOR_STORE_PATH=/app/.cache/vector_store.sqlite3 \
    SA_LEARNING_STORE_PATH=/app/.cache/learning_state.sqlite3 \
    SA_INDEX_CACHE_PATH=/app/.cache/index \
    SA_SOURCE_REGISTRY_PATH=/app/.cache/source_registry.sqlite3 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
