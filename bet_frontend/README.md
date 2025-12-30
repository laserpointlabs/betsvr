# Bet Frontend - Chat Interface

Simple web-based chat interface for the LMSVR API Gateway.

## Features

- 🔐 API key authentication (stored in browser localStorage)
- 💬 Real-time streaming chat responses
- 🎯 Model selection dropdown
- 📱 Mobile-responsive design
- ⚡ Fast and lightweight (Nginx + static files)

## Configuration

Set the default model via environment variable in your `.env` file:

```bash
BET_DEFAULT_MODEL=llama3.2:1b
```

Or in `docker-compose.yml`:

```yaml
bet_frontend:
  environment:
    - DEFAULT_MODEL=${BET_DEFAULT_MODEL:-llama3.2:1b}
```

## Local Development

### Build and run locally:

```bash
cd bet_frontend
docker build -t bet-frontend .
docker run -p 8002:80 -e DEFAULT_MODEL=llama3.2:1b bet-frontend
```

Access at: `http://localhost:8002`

### With Docker Compose:

```bash
docker compose up -d bet_frontend
```

Access at: `http://localhost:8002`

## Cloudflare Setup

The frontend is configured to be accessible at `bet.laserpointlabs.com` via Cloudflare Tunnel.

### DNS Setup

Add DNS record in Cloudflare Dashboard:
- Type: CNAME
- Name: `bet`
- Target: `7a14aef0-282b-4d81-9e3a-817338eef3df.cfargotunnel.com`
- Proxy: Enabled (orange cloud)

Or via CLI:
```bash
cloudflared tunnel route dns ollama-gateway bet.laserpointlabs.com
```

### Cloudflare Config

The `cloudflare/config.yml` is already configured with:
```yaml
- hostname: bet.laserpointlabs.com
  service: http://bet_frontend:80
```

## Usage

1. Visit `https://bet.laserpointlabs.com`
2. Enter your API key (from LMSVR CLI)
3. Select a model from the dropdown
4. Start chatting!

## Architecture

- **Frontend**: Nginx serving static HTML/CSS/JS
- **API**: Calls `https://lmapi.laserpointlabs.com/api/chat`
- **Authentication**: API key passed in Authorization header
- **Streaming**: Real-time response streaming via Server-Sent Events

## File Structure

```
bet_frontend/
├── Dockerfile          # Nginx container
├── entrypoint.sh       # Injects DEFAULT_MODEL env var
├── nginx.conf          # Nginx configuration
├── static/
│   ├── index.html     # Main HTML page
│   ├── app.js         # JavaScript logic
│   └── style.css      # Styling
└── README.md          # This file
```


