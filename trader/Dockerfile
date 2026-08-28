# syntax=docker/dockerfile:1
#
# Multi-stage build for the trader MCP server, using uv.
#
#   Stages:
#     - `base` : Python 3.14 runtime + uv + dependency sync
#     - `dev`  : dev dependencies + editable install (hot-reload friendly)
#     - `prod` : runtime-only, project wheel installed + non-root user
#
#   Build this image from the trader directory:
#     docker build --target dev  -t fifty/trader:dev  .
#     docker build --target prod -t fifty/trader:prod .
#
#   The trader uses the `mt5linux` bridge, so it runs on Linux and talks over
#   RPyC to a separate Wine + MetaTrader 5 sidecar container (see the compose
#   files, `mt5-sidecar` service). Live order execution therefore needs that
#   sidecar to be up and reachable at MT5_HOST:MT5_PORT.

FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS base

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy the project manifests first for better layer caching.
COPY pyproject.toml uv.lock .python-version ./

# Install software dependencies (not the project itself, for a reusable base).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-editable

# Copy the source tree in last (changes most often).
COPY . .

# ---------------------------------------------------------------------------
# dev: full toolchain (pytest) + editable install.
# ---------------------------------------------------------------------------
FROM base AS dev

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --editable

CMD ["sh", "-c", "uv run --active python /app/main.py"]

# ---------------------------------------------------------------------------
# prod: runtime dependencies only + project wheel, drop to non-root user.
# ---------------------------------------------------------------------------
FROM base AS prod

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

# Run as a non-privileged user.
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

CMD ["sh", "-c", "uv run --active python /app/main.py"]
