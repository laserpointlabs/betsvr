# betsvr

Betting product that uses **lmsvr** as the LLM/auth provider.

## Architecture

- **bet_frontend** (Nginx static UI)
  - Chat/models/auth calls go to **lmsvr** (default `https://lmapi.laserpointlabs.com`)
  - Betting alerts endpoints (`/api/alerts*`) go to **betsvr** same-origin and are reverse-proxied to `bet_api`
- **bet_api** (FastAPI)
  - Runs the betting monitoring loop and stores alerts
  - Validates API keys/device tokens by calling **lmsvr** (`LM_API_BASE_URL`)
  - Runs betting MCP servers (`mcp_servers/betting_monitor`, etc.)
- **cloudflared** (Cloudflare Tunnel)
  - Separate tunnel from lmsvr (recommended)

## Local dev quickstart

1. Start `lmsvr` on the host (so it is available at `http://localhost:8001`).
2. Start betsvr:

```bash
cd betsvr
export LM_API_BASE_URL=http://host.docker.internal:8001
docker compose up -d --build
```

3. Open the UI: `http://localhost:8002`

## Production notes

- `bet.laserpointlabs.com` should be routed through **betsvr**’s tunnel.
- `lmapi.laserpointlabs.com` remains routed through **lmsvr**’s tunnel.


