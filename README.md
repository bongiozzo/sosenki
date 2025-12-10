# SOSenki

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Shared-Goals/SOSenki)

**Shared property management system for small communities** — Telegram bot + Mini App for tracking bills, balances, and service periods.

## Vision

A lightweight, self-hosted solution for 20-100 users managing shared property expenses. Built with YAGNI/KISS principles: SQLite database, Python/FastAPI backend, Telegram as the only UI.

### Prerequisites

Install before running `make install`:

- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [Ollama](https://ollama.com/) — `curl -fsSL https://ollama.com/install.sh | sh`
- [Caddy](https://caddyserver.com/) — `apt install caddy`

### Configuration

Edit `.env` before running `make install`:

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Your bot token from @BotFather |
| `DOMAIN` | Your domain (e.g., `sosenki.sharedgoals.ru`) |
| `PORT` | Server port (default: `8000` |
| `OLLAMA_MODEL` | LLM model (default: `qwen2.5:1.5b`) |

`make install` derives `WEBHOOK_URL` and `MINI_APP_URL` from `DOMAIN` automatically.

## Deployment

**Target platform:** Linux server (Ubuntu 22.04+, 4GB+ RAM)

```bash
git clone https://github.com/Shared-Goals/SOSenki.git
cd SOSenki
cp .env.example .env    # Configure: TELEGRAM_BOT_TOKEN, DOMAIN, OLLAMA_MODEL, PORT
sudo make install       # Full setup: deps + Ollama + systemd + Caddy
sudo systemctl start sosenki
```

### Network Configuration (Router Setup)

If running behind a router with static IP:

1. **Port Forwarding** (in router admin panel):
   - Forward external port `80` (HTTP) → internal server port `80`
   - Forward external port `443` (HTTPS) → internal server port `443`
   - (Caddy handles SSL termination automatically)

2. **Environment Variables**:

   ```env
   DOMAIN=sosenki.sharedgoals.ru
   PORT=8000
   ```

3. **Verify Deployment**:

   ```bash
   # Check internal connectivity
   curl http://localhost:8000/health
   # {\"status\":\"ok\"}

   # Check external connectivity
   curl https://sosenki.sharedgoals.ru/health
   # {\"status\":\"ok\"}
   ```

## Development

```bash
make sync         # Install Python dependencies via uv
make serve        # Run bot + mini app (ngrok tunnel for dev)
make test         # Run all tests
make coverage     # Generate coverage report
```

See `make help` for full command reference.

## Documentation

Auto-generated documentation: [DeepWiki](https://deepwiki.com/Shared-Goals/SOSenki)
