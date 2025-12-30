# Betting MCP Server Architecture

## Overview

This document summarizes the architecture and design decisions for integrating MCP (Model Context Protocol) servers into the `lmsvr` platform for a gambling/betting use case. The system enables users to access real-time betting data, gambling information, and AI-powered suggestions through a web interface.

## Core Concept

The betting system combines:
- **RAG (Retrieval Augmented Generation)**: For accessing detailed gambling data and methods
- **MCP Servers**: For capturing live data from paid data sources
- **Pluggable Architecture**: Kits act as versioned plugins for easy management

## Architecture Design

### Three-Tier Billing Model

The system charges users for three distinct access types:

1. **Model Access**: Cost per model usage
2. **Request/Query**: Cost per API request
3. **Kit Access**: Cost for accessing specialized betting kits

#### Kit Pricing Components

- **Base Kit Cost**: Per-request cost when a kit is used
- **MCP Call Costs**: Cost per MCP tool call made during inference
- **RAG Retrieval Costs**: 
  - Cost per RAG query
  - Cost per retrieved chunk (optional tiered pricing)

### Pluggable Kit System

Kits are designed as self-contained, versioned plugins with:

- **Clear Interfaces**: Well-defined APIs for kit registration and lifecycle
- **Version Management**: Each kit has a version (e.g., "gambling-kit:1.0.0")
- **Configuration**: Kit-specific pricing and access control
- **Isolation**: Kits can be developed and deployed independently

#### Proposed Database Schema

```python
# Kit Pricing Configuration
class KitPricingConfig:
    kit_id: str              # e.g., "gambling-kit"
    kit_version: str         # e.g., "1.0.0"
    per_kit_request_cost: float
    per_mcp_call_cost: float
    per_rag_retrieval_cost: float
    rag_cost_per_chunk: float
    active: bool

# Customer Kit Access
class CustomerKitAccess:
    customer_id: int
    kit_id: str
    kit_version: str
    enabled: bool
    access_type: str         # "pay_per_use" or "subscription"
    subscription_cost: float  # If subscription-based
```

### Deployment Strategy

**Initial Approach**: Integrated into existing API Gateway
- Kits run as part of the main server
- Easier to manage initially
- Lower operational overhead

**Future Path**: Separate microservices
- Kits can be extracted to separate services
- Better scalability and isolation
- More complex deployment but more flexible

## Frontend Implementation

### Web Interface: bet.laserpointlabs.com

A simple, mobile-first chat interface built as a separate container:

- **API Key Authentication**: Users provide API key to access
- **Device Registration**: One-time activation per device using device tokens
- **Model Selection**: Limited to `llama3.2:latest` and `mistral:latest`
- **Conversation Persistence**: Chat history saved to localStorage
- **Markdown Rendering**: Assistant responses render formatted markdown

### Device Registration Flow

1. User receives email with API key link
2. Clicks link → Opens `bet.laserpointlabs.com?key=API_KEY`
3. Frontend auto-fills API key input
4. User clicks "Save Key"
5. Frontend calls `/api/register-device` with API key
6. Server validates key, generates device token, stores registration
7. Device token saved to localStorage (not the API key)
8. Next visit: Frontend calls `/api/verify-device` → Auto-login

**Benefits**:
- API key never stored locally (more secure)
- Device token is useless without server validation
- Users can revoke device access via CLI
- Works with device management UI

### API Endpoints

#### Device Registration
- `POST /api/register-device`: Register device with API key, returns device token
- `POST /api/verify-device`: Verify device token is still valid
- `DELETE /api/device/{device_token}`: Revoke a device

#### CLI Commands
- `python cli/cli.py list-devices`: List all registered devices
- `python cli/cli.py list-devices --customer-id 3`: Filter by customer
- `python cli/cli.py revoke-device <id>`: Revoke a device
- `python cli/cli.py delete-device <id>`: Permanently delete a device

## Technical Stack

### Backend
- **FastAPI**: Python web framework for API Gateway
- **SQLAlchemy**: Database ORM
- **Ollama**: Local LLM inference
- **Docker Compose**: Container orchestration

### Frontend
- **Vanilla JavaScript**: No framework dependencies
- **Marked.js**: Markdown rendering (CDN)
- **localStorage**: Client-side persistence
- **Nginx**: Static file serving

### Infrastructure
- **Cloudflare Tunnel**: Secure HTTPS access with DDoS protection
- **Separate Containers**: Frontend isolated from API Gateway
- **Environment Variables**: Configuration via `.env` files

## Key Features Implemented

### 1. Email API Key Delivery
- CLI command: `python cli/cli.py generate-key <customer_id> --send-email`
- Uses Gmail SMTP with App Passwords
- Email contains button linking to frontend with auto-fill URL
- One-tap access: Click button → Key auto-filled → Ready to use

### 2. Responsive Design
- Mobile-first approach
- Larger fonts and touch targets for phones
- Collapsible settings panel
- Football icon (⚙️) for settings access

### 3. Conversation Management
- Chat history persists across page refreshes
- Clear chat button in settings
- Model selection persists
- Streaming responses with markdown rendering

### 4. Model Filtering
- Frontend filters to only allowed models
- Currently: `llama3.2:latest` and `mistral:latest`
- Prevents users from accessing unauthorized models

## Future Enhancements

### Kit System Implementation
- [ ] Create kit registry and plugin loader
- [ ] Implement kit lifecycle management
- [ ] Add kit versioning and rollback
- [ ] Build kit marketplace/discovery

### RAG Integration
- [ ] Embedding generation for gambling data
- [ ] Vector database for retrieval
- [ ] Reranking for better context selection
- [ ] Cost tracking per retrieval

### MCP Server Development
- [ ] Build gambling data MCP server
- [ ] Integrate paid data source APIs
- [ ] Real-time odds and statistics
- [ ] Historical data access

### Enhanced Billing
- [ ] Subscription-based kit access
- [ ] Usage analytics dashboard
- [ ] Budget alerts and limits
- [ ] Invoice generation

## Configuration

### Environment Variables

```bash
# Gmail credentials for sending API keys
GMAIL_USER=your-email@gmail.com
GMAIL_PASSWORD=your-16-character-app-password

# Default model for Bet Frontend
BET_DEFAULT_MODEL=llama3.2:latest

# Ollama preload models
OLLAMA_PRELOAD_MODELS="llama3.2:latest,mistral:latest"
```

### Docker Services

- `bet_frontend`: Nginx serving static frontend (port 8002)
- `api_gateway`: FastAPI backend (port 8001)
- `ollama`: LLM inference server (port 11434)
- `cloudflared`: Cloudflare Tunnel for public access

## Security Considerations

1. **API Keys**: Never stored in localStorage, only device tokens
2. **Device Tokens**: Server-validated, can be revoked
3. **HTTPS**: All traffic encrypted via Cloudflare Tunnel
4. **Input Validation**: Server-side validation of all requests
5. **Rate Limiting**: Should be implemented for production

## Performance Optimizations

1. **Model Preloading**: Keep frequently used models loaded
2. **Streaming Responses**: Real-time token streaming for better UX
3. **localStorage Caching**: Conversation history cached client-side
4. **CDN**: Cloudflare CDN for static assets
5. **GPU Utilization**: Multi-GPU support for Ollama

## Notes

- The kit system architecture is designed but not yet fully implemented
- Current focus is on the frontend and device registration
- Kit pricing and RAG/MCP integration are planned for future phases
- The system is designed to scale from integrated to microservices architecture

---

**Last Updated**: December 2, 2025
**Status**: Frontend and device registration complete, kit system architecture designed

