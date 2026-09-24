# Alpine + Python 3.12 slim image optimized for ~256MB RAM environments.
# Multi-stage: build wheels in builder, copy site-packages into runtime.
FROM python:3.12-alpine AS builder

WORKDIR /build

RUN apk add --no-cache \
        build-base \
        libffi-dev \
        openssl-dev \
    && pip install --no-cache-dir --upgrade pip wheel

COPY requirements.txt .
# Prefer binary wheels; fall back to compiling only what Alpine needs.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.12-alpine AS runtime

# Non-root user for safer runtime
RUN addgroup -S bot && adduser -S -G bot bot \
    && apk add --no-cache libffi openssl \
    && rm -rf /var/cache/apk/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Keep memory footprint lower for CPython
    PYTHONMALLOC=malloc \
    PIP_NO_CACHE_DIR=1 \
    # Default DB path inside the container volume
    DATABASE_URL=sqlite+aiosqlite:////data/bot.db

WORKDIR /app

COPY --from=builder /install /usr/local
COPY bot ./bot
COPY requirements.txt .

RUN mkdir -p /data && chown -R bot:bot /app /data
USER bot

VOLUME ["/data"]

# Long-polling bot — no exposed HTTP port required.
CMD ["python", "-m", "bot.main"]
