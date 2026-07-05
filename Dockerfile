# syntax=docker/dockerfile:1

# --- Build stage: compile wheel with build deps ---
FROM python:3.11-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY platform_core platform_core
COPY backend backend
COPY evidence evidence
COPY telemetry telemetry
COPY failure_system failure_system
COPY src src
COPY edge_device edge_device
COPY endpoint_agent endpoint_agent
COPY shared shared
COPY config config
COPY shared shared
COPY knowledge knowledge
COPY fixtures fixtures

RUN pip install --upgrade pip \
    && pip wheel --wheel-dir /wheels ".[postgres]"

# --- Runtime stage: minimal image, non-root user ---
FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PLATFORM_SAFE_MODE=1 \
    PLATFORM_DATA_DIR=/data/platform \
    FAIL_FAST_ON_STARTUP=1 \
    REQUIRE_PING_BINARY=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl "psycopg2-binary>=2.9" "redis>=5" "rq>=1.16" \
    && rm -rf /wheels \
    && mkdir -p /data/platform \
    && chown -R app:app /data/platform /app

COPY --chown=app:app config config
COPY --chown=app:app shared shared

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/platform/health')"

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
