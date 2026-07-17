# syntax=docker/dockerfile:1.7
#
# HippoAgent multi-stage build
# - Stage 1 (builder): build wheels for all runtime deps inside a fat image
# - Stage 2 (runtime): copy wheels into a slim runtime, drop build tools
#
# Defaults to loopback bind (CVE-008). To expose on a non-loopback interface,
# the operator MUST opt in:
#     -e HIPPO_TRUSTED_NETWORK=1 ... hippo dashboard --insecure-bind --host 0.0.0.0
# See docs/SECURITY.md for the full threat model.

# ──────────────────────────── builder ────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY engram/ engram/
COPY hippoagent/ hippoagent/
COPY benchmark/ benchmark/

# Build wheels for the project + the "server" extra. NOT [headless]: that
# extra is empty (core only) and fastapi/uvicorn live in [server] — an image
# built without them cannot run its own CMD (dashboard) nor the gateway
# (latent bug caught 2026-07-08 while adding gateway support). The runtime
# image never sees apt build-essential.
RUN python -m pip install --upgrade pip wheel build && \
    python -m pip wheel --wheel-dir /wheels ".[server]"

# Pre-fetch the embedding model into a known cache, then copy it into runtime.
# Pre-fetch BOTH the active default model (multilingual-e5-base, 768d — what the
# server actually uses) AND the legacy MiniLM (384d — the COALESCE fallback for
# pre-v9 NULL-embedding rows). Baking them = the image works fully OFFLINE /
# air-gapped (no HF Hub round-trip on first encode).
# NOT --no-deps: sentence-transformers imports `transformers` at module load,
# so a deps-less install crashes the prefetch (ModuleNotFoundError: transformers).
# Install ST + its deps from the wheels built above, OFFLINE (--no-index).
RUN python -m pip install --no-index --find-links /wheels sentence-transformers && \
    python -c "from sentence_transformers import SentenceTransformer as S; \
        S('intfloat/multilingual-e5-base'); \
        S('sentence-transformers/all-MiniLM-L6-v2')" && \
    cp -R /root/.cache /tmp/cache_seed

# ──────────────────────────── runtime ────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HIPPO_DATA_DIR=/app/data \
    HF_HOME=/home/hippo/.cache/huggingface

# Minimal runtime libs (libgomp for sklearn/onnx, libglib for opencv runtime).
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl libgomp1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1000 hippo \
    && useradd  --system --uid 1000 --gid hippo --create-home --shell /usr/sbin/nologin hippo

WORKDIR /app

# Install from wheels only — no compiler in the runtime image.
COPY --from=builder /wheels /wheels
COPY pyproject.toml README.md ./
COPY engram/ engram/
COPY hippoagent/ hippoagent/
COPY benchmark/ benchmark/

# Install the PREBUILT project wheel by distribution NAME (verimem), not "."
# — `.` would make pip rebuild /app from source, which needs a build backend
# that --no-index can't fetch ("Failed to build file:///app"). The builder
# already produced verimem-*.whl + every dep wheel, so this is fully offline.
# NB: the distribution was renamed hippoagent -> verimem (2026-07-06); this
# line used the stale name and broke the image build (verified 2026-07-17:
# `pip install hippoagent` -> "No matching distribution found").
RUN pip install --upgrade pip && \
    pip install --no-index --find-links /wheels "verimem[server]" && \
    rm -rf /wheels

# Move pre-fetched HuggingFace cache into the unprivileged user's home.
COPY --from=builder /tmp/cache_seed /home/hippo/.cache
RUN chown -R hippo:hippo /home/hippo /app && mkdir -p /app/data && chown hippo:hippo /app/data

VOLUME ["/app/data"]
# 8765 = dashboard (legacy default CMD); 8377 = self-host gateway (see
# docker-compose.gateway.yml — override the command to run it).
EXPOSE 8765 8377

USER hippo

# Healthcheck against the loopback bind (the default).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl --fail --silent --show-error http://127.0.0.1:8765/healthz || exit 1

# Default to loopback. Operators that need to expose on 0.0.0.0 must:
#   docker run -e HIPPO_TRUSTED_NETWORK=1 verimem \
#     verimem dashboard --insecure-bind --host 0.0.0.0 --port 8765
CMD ["verimem", "dashboard", "--host", "127.0.0.1", "--port", "8765"]
