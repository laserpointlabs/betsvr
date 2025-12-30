# Bet Frontend - Deployment Summary

## ✅ What's Been Created

1. **Frontend Container** (`bet_frontend/`)
   - Nginx-based static file server
   - Chat interface HTML/CSS/JavaScript
   - Environment variable injection for default model

2. **Docker Configuration**
   - Added `bet_frontend` service to `docker-compose.yml`
   - Configured to use `BET_DEFAULT_MODEL` from `.env`
   - Exposed on port 8002 for local testing

3. **Cloudflare Configuration**
   - Updated `cloudflare/config.yml` to route `bet.laserpointlabs.com` → `bet_frontend:80`
   - Cloudflare tunnel will automatically route traffic

4. **Environment Variable**
   - Added `BET_DEFAULT_MODEL=llama3.2:1b` to `.env`

## 🚀 Next Steps to Deploy

### 1. Set Up DNS Record

Add DNS record for `bet.laserpointlabs.com`:

**Option A: Cloudflare Dashboard**
1. Go to Cloudflare Dashboard → DNS → Records
2. Click "Add record"
3. Configure:
   - Type: `CNAME`
   - Name: `bet`
   - Target: `7a14aef0-282b-4d81-9e3a-817338eef3df.cfargotunnel.com`
   - Proxy status: Proxied (orange cloud)
4. Save

**Option B: CLI**
```bash
cloudflared tunnel route dns ollama-gateway bet.laserpointlabs.com
```

### 2. Restart Cloudflare Tunnel

```bash
docker compose restart cloudflared
```

### 3. Verify Deployment

```bash
# Check all services are running
docker compose ps

# Check frontend logs
docker compose logs bet_frontend

# Test locally
curl http://localhost:8002

# Test via Cloudflare (after DNS propagates, 2-5 minutes)
curl https://bet.laserpointlabs.com
```

### 4. Access the Interface

Visit: `https://bet.laserpointlabs.com`

## 📝 Configuration

### Change Default Model

Edit `.env` file:
```bash
BET_DEFAULT_MODEL=mistral
# or
BET_DEFAULT_MODEL=qwen3-coder:30b
```

Then restart:
```bash
docker compose restart bet_frontend
```

## 🧪 Testing

### Local Testing
```bash
# Start frontend
docker compose up -d bet_frontend

# Access at http://localhost:8002
```

### Production Testing
1. Ensure DNS is set up
2. Wait 2-5 minutes for DNS propagation
3. Visit https://bet.laserpointlabs.com
4. Enter API key (get from `python cli/cli.py generate-key <customer_id>`)
5. Start chatting!

## 📁 File Structure

```
bet_frontend/
├── Dockerfile          # Nginx container definition
├── entrypoint.sh       # Injects DEFAULT_MODEL env var
├── nginx.conf          # Nginx server configuration
├── static/
│   ├── index.html     # Main chat interface
│   ├── app.js         # JavaScript logic (API calls, streaming)
│   └── style.css      # Styling
├── README.md          # General documentation
├── SETUP.md           # Setup instructions
└── DEPLOYMENT.md      # This file
```

## 🔧 Troubleshooting

### Container won't start
```bash
docker compose logs bet_frontend
```

### DNS not resolving
- Wait 2-5 minutes after adding DNS record
- Verify record in Cloudflare Dashboard
- Check tunnel logs: `docker compose logs cloudflared`

### API calls failing
- Verify API Gateway is running: `docker compose ps api_gateway`
- Check API key is valid
- Verify CORS is enabled in API Gateway

### Model not loading
- Check `.env` has `BET_DEFAULT_MODEL` set
- Verify model exists: `docker exec ollama ollama list`
- Check frontend logs for errors

## ✨ Features

- ✅ API key authentication (stored in localStorage)
- ✅ Real-time streaming responses
- ✅ Model selection dropdown
- ✅ Mobile-responsive design
- ✅ Error handling and user feedback
- ✅ Conversation history
- ✅ Environment-based configuration

## 🎯 Current Status

- ✅ Frontend container built and tested
- ✅ Docker Compose configured
- ✅ Cloudflare config updated
- ⏳ DNS record needs to be added
- ⏳ Cloudflare tunnel needs restart after DNS


