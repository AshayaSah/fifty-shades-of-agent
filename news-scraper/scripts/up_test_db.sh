#!/usr/bin/env bash
# Start an ephemeral PostgreSQL for the news-scraper test suite.
# The DB tests use TEST_DATABASE_URL (default postgres:news-scraper-test@localhost:15432).
set -euo pipefail

IMAGE="${1:-docker.io/library/postgres:16-alpine}"
NAME="news-scraper-test-pg"
PORT="15432"

if podman container exists "$NAME" 2>/dev/null || docker container inspect "$NAME" >/dev/null 2>&1; then
  echo "test Postgres container '$NAME' already exists — start it with:"
  echo "  podman start $NAME   (or: docker start $NAME)"
  exit 0
fi

RUNNER="podman"
command -v podman >/dev/null 2>&1 || RUNNER="docker"

echo "Starting test Postgres on 127.0.0.1:${PORT} ($RUNNER)…"
$RUNNER run -d \
  --name "$NAME" \
  -p "127.0.0.1:${PORT}:5432" \
  -e POSTGRES_PASSWORD=news-scraper-test \
  -e POSTGRES_DB=postgres \
  "$IMAGE"

for _ in $(seq 1 30); do
  if $RUNNER exec "$NAME" pg_isready -U postgres >/dev/null 2>&1; then
    echo "Ready: postgresql://postgres:news-scraper-test@127.0.0.1:${PORT}/news_scraper_test"
    exit 0
  fi
  sleep 1
done

echo "timed out waiting for Postgres" >&2
exit 1