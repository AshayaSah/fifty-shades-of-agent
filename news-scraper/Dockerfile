# syntax=docker/dockerfile:1
#
# Single Dockerfile for the news-scraper MCP server (FastAPI + Streamable HTTP).
#
#   Stages:
#     - `dev` : full toolchain (pytest) + editable install (hot-reload friendly)
#     - `prod`: runtime-only, project wheel installed + non-root user
#
#   Deploy to Render by pointing a Blueprint "Docker" service at this directory.
#   Render builds the default (last) stage = `prod` and sets $PORT at runtime.
#
#   Local build / run:
#     docker build --target dev  -t fifty/news-scraper:dev  .
#     docker build --target prod -t fifty/news-scraper:prod .
#     docker run -p 8000:8000 --env-file .env fifty/news-scraper:prod

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS base

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy the project manifests first for better layer caching.
COPY pyproject.toml uv.lock .python-version ./

# Install software dependencies (not the project itself, for a reusable base).
# `en_core_web_sm` is a declared dependency here, so no separate `spacy download`.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-editable

# Copy the source tree in last (changes most often).
COPY . .

EXPOSE 8000

# ---------------------------------------------------------------------------
# onnx-export: build the fp32 ONNX FinBERT for the RAM-constrained runtime.
# torch/transformers exist ONLY in this stage (never in the runtime image);
# the onnxruntime sentiment backend loads /app/models/finbert-onnx lazily.
# ---------------------------------------------------------------------------
FROM base AS onnx-export

RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --python /app/.venv/bin/python torch transformers

RUN python scripts/export_finbert_onnx.py --out /app/models/finbert-onnx

# ---------------------------------------------------------------------------
# dev: full toolchain (pytest) + editable install, git for mcp dev, source mounted.
# ---------------------------------------------------------------------------
FROM base AS dev

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --editable

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

# ---------------------------------------------------------------------------
# prod: runtime dependencies only + project wheel, drop to non-root user.
# ---------------------------------------------------------------------------
FROM base AS prod

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

# Bake the ONNX model into the runtime image (torch-free).
COPY --from=onnx-export /app/models/finbert-onnx /app/models/finbert-onnx

# Run as a non-privileged user.
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]