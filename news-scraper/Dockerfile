# syntax=docker/dockerfile:1
#
# Multi-stage build for the news-scraper MCP server, using uv.
#
#   Stages:
#     - `base` : Python 3.14 runtime + uv + dependency sync
#     - `dev`  : dev dependencies + editable install (hot-reload friendly)
#     - `prod` : runtime-only, project wheel installed + non-root user
#
#   Build this image from the news-scraper directory:
#     docker build --target dev  -t fifty/news-scraper:dev  .
#     docker build --target prod -t fifty/news-scraper:prod .

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

# The spaCy `en_core_web_sm` model is a separate download, not a pip package.
# Pull it once here, into the shared base, so both dev and prod images have it
# at build time instead of on first scrape.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv run --active python -m spacy download en_core_web_sm

# Copy the source tree in last (changes most often).
COPY . .

# ---------------------------------------------------------------------------
# dev: full toolchain (pytest) + editable install, git for mcp dev, source mounted.
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
    uv sync \
    && uv cache clean

# Run as a non-privileged user.
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

CMD ["sh", "-c", "uv run --active python /app/main.py"]
