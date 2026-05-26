#!/usr/bin/env bash
set -euo pipefail

# Build a backend-only ADS upload package.
#
# Recommended usage from repo root:
#   bash deploy/ads/build-package.sh
#
# Optional:
#   INCLUDE_ENV=1 bash deploy/ads/build-package.sh
#   INCLUDE_POSTGRES=1 bash deploy/ads/build-package.sh
#   PACKAGE_NAME=deerflow-ads-backend.tar.gz bash deploy/ads/build-package.sh

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." >/dev/null 2>&1 && pwd -P)"
DIST_DIR="$REPO_ROOT/dist"
STAGE_DIR="$DIST_DIR/deerflow-ads-backend"
PACKAGE_NAME="${PACKAGE_NAME:-deerflow-ads-backend.tar.gz}"
PACKAGE_PATH="$DIST_DIR/$PACKAGE_NAME"

uses_postgres_config() {
  local config_path="$1"
  [ -f "$config_path" ] || return 1

  awk '
    /^[[:space:]]*#/ { next }
    /^[^[:space:]][^:]*:/ {
      section=$0
      sub(/:.*/, "", section)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", section)
    }
    section=="database" && /^[[:space:]]*backend:[[:space:]]*["'\'']?postgres["'\'']?[[:space:]]*(#.*)?$/ { found=1 }
    section=="checkpointer" && /^[[:space:]]*type:[[:space:]]*["'\'']?postgres["'\'']?[[:space:]]*(#.*)?$/ { found=1 }
    END { exit found ? 0 : 1 }
  ' "$config_path"
}

includes_postgres_extra() {
  if [ "${INCLUDE_POSTGRES:-0}" = "1" ]; then
    return 0
  fi
  case " ${UV_EXTRAS:-} " in
    *" postgres "*|*",postgres "*|*" postgres,"*|*",postgres,"*) return 0 ;;
  esac
  uses_postgres_config "$REPO_ROOT/config.yaml"
}

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

UV_BIN="${UV_BIN:-}"
if [ -z "$UV_BIN" ]; then
  if command -v uv >/dev/null 2>&1; then
    UV_BIN="uv"
  elif command -v uv.exe >/dev/null 2>&1; then
    UV_BIN="uv.exe"
  fi
fi

if [ -n "$UV_BIN" ]; then
  UV_EXPORT_ARGS=(export --frozen --no-dev --format requirements.txt --no-hashes --no-header --no-annotate)
  if includes_postgres_extra; then
    UV_EXPORT_ARGS+=(--extra postgres)
    echo "Including postgres extra dependencies in requirements.txt"
  fi
  (
    cd "$REPO_ROOT/backend"
    "$UV_BIN" "${UV_EXPORT_ARGS[@]}"
  ) > "$STAGE_DIR/requirements.txt"
  # ADS only accepts registry-style requirement lines (package==version).
  # The local workspace package is shipped in backend/packages/harness and
  # exposed through PYTHONPATH by app.sh instead of being installed with -e.
  sed -i.bak \
    -e '/^-e \.\/packages\/harness$/d' \
    -e '/^[[:space:]]*#/d' \
    -e '/^[[:space:]]*$/d' \
    "$STAGE_DIR/requirements.txt"
  rm -f "$STAGE_DIR/requirements.txt.bak"
else
  echo "uv is required to generate ADS requirements.txt from backend/uv.lock." >&2
  echo "Install uv or build the package on a machine that has uv available." >&2
  exit 1
fi

chmod +x "$STAGE_DIR/app.sh"

if [ "${INCLUDE_VENV:-0}" = "1" ]; then
  if [ ! -d "$REPO_ROOT/backend/.venv" ]; then
    echo "INCLUDE_VENV=1 was set, but backend/.venv does not exist." >&2
    echo "Run 'cd backend && uv sync' on a Linux environment compatible with ADS first." >&2
    exit 1
  fi
  if [ ! -x "$REPO_ROOT/backend/.venv/bin/python" ]; then
    echo "INCLUDE_VENV=1 requires a Linux virtualenv at backend/.venv." >&2
    echo "The current backend/.venv does not contain bin/python." >&2
    echo "Build the package on a Linux machine/container compatible with ADS." >&2
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
echo
echo "Postgres dependencies are included automatically when config.yaml uses postgres."
echo "You can also force them with:"
echo "  INCLUDE_POSTGRES=1 bash deploy/ads/build-package.sh"
