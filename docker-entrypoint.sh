#!/bin/sh
set -e

# Migrations are not run here; apply them explicitly with `make migrate`
# (or `alembic upgrade head`) as a separate step.

# Default command: run the API. RELOAD=true enables hot-reload for local dev.
# Note: with reload on, uvicorn's reloader keeps the container alive even if
# startup fails, so leave it off when you want a failed startup to exit.
if [ "$#" -eq 0 ]; then
  set -- uvicorn main:app --host 0.0.0.0 --port 8000
  if [ "${RELOAD:-false}" = "true" ]; then
    set -- "$@" --reload
  fi
fi

exec "$@"
