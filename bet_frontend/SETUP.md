# Bet Frontend Setup Guide

## Quick Setup

### 1. Add Environment Variable

Add to your `.env` file in the project root:

```bash
BET_DEFAULT_MODEL=llama3.2:1b
```

You can use any available model:
- `llama3.2:1b` (small, fast)
- `mistral` (balanced)
- `qwen3-coder:30b` (large, powerful)

### 2. Build and Start

```bash
docker compose build bet_frontend
docker compose up -d bet_frontend
```

### 3. Set Up Cloudflare Tunnel + DNS (betsvr)

Create a new betsvr-owned tunnel and route `bet.laserpointlabs.com` to it.

**Via Cloudflare Dashboard:**
1. Go to DNS → Records
2. Add CNAME record:
   - Name: `bet`
   - Target: `<YOUR_TUNNEL_ID>.cfargotunnel.com`
   - Proxy: Enabled (orange cloud)

**Via CLI:**
```bash
cloudflared tunnel create betsvr-bet
cloudflared tunnel route dns betsvr-bet bet.laserpointlabs.com
```

### 4. Start betsvr tunnel (docker)

```bash
docker compose up -d cloudflared
```

### 5. Access

Visit: `https://bet.laserpointlabs.com`

## Testing Locally

Before deploying to Cloudflare, test locally:

```bash
# Build
docker compose build bet_frontend

# Start
docker compose up -d bet_frontend

# Access at http://localhost:8002
# Access at http://localhost:8004
```

## Verify Setup

1. Check container is running:
   ```bash
   docker compose ps bet_frontend
   ```

2. Check logs:
   ```bash
   docker compose logs bet_frontend
   ```

3. Test locally:
   ```bash
   curl http://localhost:8004
   ```

4. Test via Cloudflare (after DNS setup):
   ```bash
   curl https://bet.laserpointlabs.com
   ```

## Troubleshooting

### Container won't start
- Check logs: `docker compose logs bet_frontend`
- Verify Dockerfile syntax
- Check file permissions on entrypoint.sh

### DNS not resolving
- Wait 2-5 minutes for DNS propagation
- Verify DNS record in Cloudflare Dashboard
- Check Cloudflare tunnel logs: `docker compose logs cloudflared`

### API calls failing
- Verify API Gateway is running: `docker compose ps api_gateway`
- Check CORS settings in API Gateway
- Verify API key is valid


