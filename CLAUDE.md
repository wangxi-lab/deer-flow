# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DeerFlow is a LangGraph-based AI "super agent harness" with a full-stack architecture. It orchestrates sub-agents, memory, and sandboxes to execute complex tasks, powered by extensible skills.

**Stack**:
- Backend: Python 3.12+, LangGraph + FastAPI, sandbox/tool system, memory, MCP integration
- Frontend: Next.js 16 + React 19 + TypeScript + pnpm
- Local dev entry: `make dev` starts all services at `http://localhost:2026`
- Docker dev entry: `make docker-*` commands

## Development Commands

### Full Application (from repo root)

```bash
make check          # Verify Node.js 22+, pnpm, uv, nginx are installed
make install        # Install backend + frontend dependencies
make dev            # Start all services in dev mode (hot-reload)
make dev-pro        # Dev + Gateway mode (agent runtime embedded in Gateway, experimental)
make start          # Start all services in production mode
make stop           # Stop all running services
make doctor         # Validate config.yaml and environment setup
```

### Backend Only (from backend/)

```bash
cd backend
make install        # uv sync
make dev            # LangGraph server only (port 2024)
make gateway        # Gateway API only (port 8001)
make test           # pytest tests/ -v
make lint           # ruff check . && ruff format --check .
make format         # ruff check --fix && ruff format .
```

### Frontend Only (from frontend/)

```bash
cd frontend
pnpm dev            # Next.js dev server (port 3000)
pnpm lint           # ESLint
pnpm typecheck      # tsc --noEmit
pnpm test           # Vitest unit tests
pnpm test:e2e       # Playwright E2E tests
```

### Docker Development

```bash
make docker-init      # Pull sandbox image, build containers
make docker-start      # Start Docker dev services (mode-aware from config.yaml)
make docker-stop       # Stop Docker services
make docker-logs       # View logs
```

## Service Architecture

```
Browser → Nginx (port 2026) → Frontend (3000) / Gateway (8001) / LangGraph (2024)
```

**Standard mode** (`make dev`): 4 processes - frontend, gateway, langgraph, nginx
**Gateway mode** (`make dev-pro`): 3 processes - frontend, gateway (embeds agent), nginx

| Service | Port | Purpose |
|---------|------|---------|
| Nginx | 2026 | Unified reverse proxy entry point |
| Frontend | 3000 | Next.js web UI |
| Gateway API | 8001 | REST API (models, skills, memory, uploads, threads) |
| LangGraph | 2024 | Agent runtime and workflow execution |
| Provisioner | 8002 | Optional - started only for Kubernetes sandbox mode |

## Project Layout

```
deer-flow/
├── Makefile                  # Root development commands
├── config.example.yaml       # Main app config template
├── backend/
│   ├── CLAUDE.md             # Detailed backend architecture
│   ├── packages/harness/     # deerflow-* package (import: deerflow.*)
│   │       └── deerflow/      # Agent core: agents/, sandbox/, tools/, models/, skills/, mcp/
│   ├── app/gateway/          # FastAPI Gateway API (import: app.*)
│   ├── app/channels/         # IM integrations (Feishu, Slack, Telegram, WeChat, WeCom)
│   └── tests/                # Backend unit tests
├── frontend/
│   ├── CLAUDE.md             # Detailed frontend architecture
│   └── src/
│       ├── app/              # Next.js App Router routes
│       ├── components/        # React components
│       └── core/             # Business logic (threads, API, artifacts, models)
├── skills/
│   ├── public/               # Built-in skills (committed)
│   └── custom/               # Custom skills (gitignored)
└── docker/                   # Docker Compose and nginx configs
```

## Critical Gotchas

1. **BETTER_AUTH_SECRET required for frontend build**: `pnpm build` fails without it. Set `BETTER_AUTH_SECRET=local-dev-secret` or use `SKIP_ENV_VALIDATION=1`.

2. **Proxy env vars can break frontend network**: If `pnpm install` fails with registry errors, unset proxy variables and retry.

3. **config.yaml must be in project root**: Configuration priority looks for `config.yaml` in backend/ first, then parent (project root - recommended).

4. **make config is not idempotent**: Aborts if config already exists. Use for first-time setup only; edit config.yaml directly afterwards.

5. **Gateway mode is experimental**: `make dev-pro` embeds agent runtime in Gateway but lacks a separate LangGraph server license requirement.

## Documentation

- [Backend Architecture](backend/CLAUDE.md) - Detailed backend internals, middleware chain, sandbox, subagents, memory
- [Frontend Architecture](frontend/CLAUDE.md) - Detailed frontend internals, components, state management
- [Configuration Guide](backend/docs/CONFIGURATION.md) - Setup and configuration options
- [MCP Server Guide](backend/docs/MCP_SERVER.md) - MCP integration setup

## CI Validation

Before submitting PRs, run locally to match CI:

```bash
# Backend
cd backend && make lint && make test

# Frontend
cd frontend && pnpm lint && pnpm typecheck
# For UI/env changes:
BETTER_AUTH_SECRET=... pnpm build
```
