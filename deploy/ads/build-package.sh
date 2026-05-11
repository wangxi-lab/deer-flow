#!/usr/bin/env bash
set -euo pipefail

# Build a backend-only ADS upload package.
#
# Recommended usage from repo root:
#   bash deploy/ads/build-package.sh
#
# Optional:
#   INCLUDE_ENV=1 bash deploy/ads/build-package.sh
#   PACKAGE_NAME=deerflow-ads-backend.tar.gz bash deploy/ads/build-package.sh

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." >/dev/null 2>&1 && pwd -P)"
DIST_DIR="$REPO_ROOT/dist"
STAGE_DIR="$DIST_DIR/deerflow-ads-backend"
PACKAGE_NAME="${PACKAGE_NAME:-deerflow-ads-backend.tar.gz}"
PACKAGE_PATH="$DIST_DIR/$PACKAGE_NAME"

mkdir -p "$DIST_DIR"
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"

copy_required_file() {
  local src="$1"
  local dst="$2"
  if [ ! -e "$src" ]; then
    echo "Missing required file: $src" >&2
    exit 1
  fi
  cp "$src" "$dst"
}

copy_required_file "$REPO_ROOT/deploy/ads/app.sh" "$STAGE_DIR/app.sh"
copy_required_file "$REPO_ROOT/config.yaml" "$STAGE_DIR/config.yaml"
copy_required_file "$REPO_ROOT/extensions_config.json" "$STAGE_DIR/extensions_config.json"

if [ "${INCLUDE_ENV:-0}" = "1" ] && [ -f "$REPO_ROOT/.env" ]; then
  cp "$REPO_ROOT/.env" "$STAGE_DIR/.env"
else
  cp "$REPO_ROOT/.env.example" "$STAGE_DIR/.env.example"
fi

rsync -a \
  --exclude ".venv" \
  --exclude ".vscode" \
  --exclude ".pytest_cache" \
  --exclude ".ruff_cache" \
  --exclude ".langgraph_api" \
  --exclude ".deer-flow" \
  --exclude ".mypy_cache" \
  --exclude "tests" \
  --exclude "__pycache__" \
  "$REPO_ROOT/backend/" "$STAGE_DIR/backend/"

rsync -a \
  --exclude "custom" \
  "$REPO_ROOT/skills/" "$STAGE_DIR/skills/"

chmod +x "$STAGE_DIR/app.sh"

if [ "${INCLUDE_VENV:-0}" = "1" ]; then
  if [ ! -d "$REPO_ROOT/backend/.venv" ]; then
    echo "INCLUDE_VENV=1 was set, but backend/.venv does not exist." >&2
    echo "Run 'cd backend && uv sync' on a Linux environment compatible with ADS first." >&2
    exit 1
  fi
  rsync -a "$REPO_ROOT/backend/.venv/" "$STAGE_DIR/backend/.venv/"
fi

tar -C "$DIST_DIR" -czf "$PACKAGE_PATH" "$(basename "$STAGE_DIR")"

echo "ADS backend package created:"
echo "  $PACKAGE_PATH"
echo
echo "Upload and extract it in ADS, then run:"
echo "  ./app.sh"
