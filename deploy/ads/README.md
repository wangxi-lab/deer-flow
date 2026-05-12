# ADS Backend-Only Deployment

This package is for enterprise ADS platforms that provide a Python base image
and start the application through `app.sh`.

In the current DeerFlow branch, the FastAPI Gateway embeds the LangGraph
runtime. You only need to start one backend process:

```text
Gateway 8080 = REST API + LangGraph-compatible API + agent runtime
```

## Build Package

Run from the repository root:

```bash
bash deploy/ads/build-package.sh
```

The output is:

```text
dist/deerflow-ads-backend.tar.gz
```

By default, `.env` is not included. ADS should inject secrets through platform
environment variables. For a private test package, you can include the local
`.env` file:

```bash
INCLUDE_ENV=1 bash deploy/ads/build-package.sh
```

If ADS cannot install dependencies at startup, build `backend/.venv` in a Linux
environment compatible with ADS and include it:

```bash
cd backend
uv sync
cd ..
INCLUDE_VENV=1 bash deploy/ads/build-package.sh
```

When a prebuilt `.venv` is included, build it on the same CPU architecture and
a compatible Linux distribution as ADS. Python virtual environments are not
fully relocatable: scripts such as `backend/.venv/bin/uvicorn` may contain a
shebang pointing to the build-time absolute path. The generated `app.sh` avoids
that specific issue by starting Uvicorn with:

```bash
backend/.venv/bin/python -m uvicorn app.gateway.app:app ...
```

If `backend/.venv/bin/python` itself cannot run after extraction, rebuild the
virtual environment on the target machine or let ADS install from
`requirements.txt`.

If ADS can install Python dependencies at startup, `app.sh` falls back to:

```bash
uv run --frozen uvicorn app.gateway.app:app ...
```

You can override the uv arguments when needed:

```bash
UV_RUN_ARGS="" ./app.sh
```

## ADS Runtime

Extract the package in ADS and set the startup entry to:

```bash
./app.sh
```

`app.sh` follows the ADS shell-entry convention:

```sh
#!/bin/sh
echo "DeerFlow Gateway starting........................"
binPath=$(dirname "$0")
cd "$binPath" || exit 1
# start DeerFlow Gateway in background with "&"
while :
do
  sleep 1
done
```

The actual application entry inside the script is the Gateway process:

```bash
uvicorn app.gateway.app:app --host 0.0.0.0 --port "$GATEWAY_PORT" &
```

Required files in the extracted package:

```text
app.sh
requirements.txt
config.yaml
extensions_config.json
backend/
skills/
```

ADS can install Python dependencies from the generated root-level
`requirements.txt`. The file is exported from `backend/uv.lock` without uv
headers/annotations and contains only registry-style package lines such as
`fastapi==...`.

The local DeerFlow harness package is not listed with `-e ...` because some ADS
installers reject editable/path requirements. It is shipped in
`backend/packages/harness` and loaded through `PYTHONPATH` by `app.sh`.

If ADS installs dependencies automatically before running `app.sh`, no extra
startup install step is needed. If ADS does not install dependencies
automatically, either install manually with:

```bash
pip install -r requirements.txt
```

or include a prebuilt Linux virtual environment with `INCLUDE_VENV=1`.

Recommended ADS environment variables:

```bash
PORT=8080
GATEWAY_WORKERS=1
DEER_FLOW_HOME=/data/deer-flow
DEER_FLOW_CONFIG_PATH=/app/config.yaml
DEER_FLOW_EXTENSIONS_CONFIG_PATH=/app/extensions_config.json
DEER_FLOW_SKILLS_PATH=/app/skills
GATEWAY_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Use a persistent ADS volume for `DEER_FLOW_HOME`; otherwise threads, uploads,
memory, and local database files will be lost after container restart.

## Local Frontend Connecting to ADS

Run the frontend locally and point it to the ADS Gateway:

```bash
cd frontend
cat > .env.local <<'EOF'
DEER_FLOW_INTERNAL_GATEWAY_BASE_URL=http://ADS_HOST:8080
EOF
pnpm dev
```

Do not set `NEXT_PUBLIC_BACKEND_BASE_URL` or
`NEXT_PUBLIC_LANGGRAPH_BASE_URL` for this local-frontend mode. Leaving them
unset lets Next.js rewrite same-origin `/api/*` and `/api/langgraph/*` requests
to the ADS Gateway. This is required because auth pages call relative URLs such
as `/api/v1/auth/login/local`.

Then open:

```text
http://localhost:3000
```

## Verification

After ADS starts the package, verify:

```bash
curl http://ADS_HOST:8080/health
```

Expected response:

```json
{"status":"healthy","service":"deer-flow-gateway"}
```

If authentication is enabled, visit the local frontend and complete setup or
login through the UI. The frontend will call the ADS Gateway directly.

## Notes

- Do not start a separate `langgraph dev` service for this branch.
- Do not expose `backend/.deer-flow` as a public static path.
- If sandbox execution requires Docker or Kubernetes, confirm ADS supports the
  configured sandbox backend. Otherwise use a local/no-container sandbox mode.
- If custom skills are needed, copy them into `skills/custom` in the package or
  mount a platform-managed skills directory and set `DEER_FLOW_SKILLS_PATH`.
