#!/usr/bin/env bash
set -euo pipefail

# ADS backend-only entrypoint.
# This starts the FastAPI Gateway. In the current DeerFlow branch the Gateway
# embeds the LangGraph runtime, so there is no separate langgraph service.

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
cd "$APP_DIR"

if [ -f "$APP_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$APP_DIR/.env"
  set +a
fi

export LANG="${LANG:-C.UTF-8}"
export LC_ALL="${LC_ALL:-C.UTF-8}"
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

export DEER_FLOW_PROJECT_ROOT="${DEER_FLOW_PROJECT_ROOT:-$APP_DIR}"
export DEER_FLOW_HOME="${DEER_FLOW_HOME:-$APP_DIR/data}"
export DEER_FLOW_CONFIG_PATH="${DEER_FLOW_CONFIG_PATH:-$APP_DIR/config.yaml}"
export DEER_FLOW_EXTENSIONS_CONFIG_PATH="${DEER_FLOW_EXTENSIONS_CONFIG_PATH:-$APP_DIR/extensions_config.json}"
export DEER_FLOW_SKILLS_PATH="${DEER_FLOW_SKILLS_PATH:-$APP_DIR/skills}"

export GATEWAY_HOST="${GATEWAY_HOST:-0.0.0.0}"
export GATEWAY_PORT="${GATEWAY_PORT:-${PORT:-8001}}"

# Useful when testing from a local frontend. Override in ADS when needed.
export GATEWAY_CORS_ORIGINS="${GATEWAY_CORS_ORIGINS:-http://localhost:3000,http://127.0.0.1:3000}"

mkdir -p "$DEER_FLOW_HOME"

if [ ! -f "$DEER_FLOW_CONFIG_PATH" ]; then
  echo "Missing config file: $DEER_FLOW_CONFIG_PATH" >&2
  exit 1
fi

if [ ! -f "$DEER_FLOW_EXTENSIONS_CONFIG_PATH" ]; then
  echo "Missing extensions config file: $DEER_FLOW_EXTENSIONS_CONFIG_PATH" >&2
  exit 1
fi

cd "$APP_DIR/backend"
export PYTHONPATH="$APP_DIR/backend${PYTHONPATH:+:$PYTHONPATH}"

if [ -x "$APP_DIR/backend/.venv/bin/uvicorn" ]; then
  exec "$APP_DIR/backend/.venv/bin/uvicorn" app.gateway.app:app \
    --host "$GATEWAY_HOST" \
    --port "$GATEWAY_PORT" \
    --workers "${GATEWAY_WORKERS:-1}"
fi

if command -v uv >/dev/null 2>&1; then
  exec uv run ${UV_RUN_ARGS---frozen} uvicorn app.gateway.app:app \
    --host "$GATEWAY_HOST" \
    --port "$GATEWAY_PORT" \
    --workers "${GATEWAY_WORKERS:-1}"
fi

exec python -m uvicorn app.gateway.app:app \
  --host "$GATEWAY_HOST" \
  --port "$GATEWAY_PORT" \
  --workers "${GATEWAY_WORKERS:-1}"
