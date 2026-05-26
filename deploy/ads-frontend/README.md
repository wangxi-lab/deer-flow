# ADS Frontend Deployment

This builds a Nodejs ADS package for the DeerFlow frontend.

The generated package follows the ADS layout:

```text
deerflow-ads-frontend/
  nodeServer
  package.json
  next.config.js
  .next/
  public/
  src/
  node_modules/
```

## Build On Windows / PowerShell

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/ads-frontend/build-package.ps1
```

The output is:

```text
dist/deerflow-ads-frontend.tar.gz
```

If you have already run `pnpm build` and only want to package:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/ads-frontend/build-package.ps1 -SkipBuild
```

## Runtime Environment Variables

Configure these in ADS rather than packaging local `.env` files:

```bash
PORT=8080
BETTER_AUTH_SECRET=change-me-to-a-long-random-string
DEER_FLOW_INTERNAL_GATEWAY_BASE_URL=http://YOUR_BACKEND_HOST:8080
```

Do not set `NEXT_PUBLIC_BACKEND_BASE_URL` or
`NEXT_PUBLIC_LANGGRAPH_BASE_URL` for same-origin frontend deployment unless you
intentionally want the browser to call a separate backend origin directly.

## Node Version

The company ADS image is Node.js 20. The current frontend uses Next.js 16. If
the build or runtime reports a Node version error, use a Node.js 22 ADS image
or downgrade the frontend framework version.
