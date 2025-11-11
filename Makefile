# ============================================================================
# Configuration
# ============================================================================

# Database
DB_FILE := sosenki.db
DATABASE_URL := sqlite:///./$(DB_FILE)

# Google credentials
GOOGLE_CREDENTIALS_PATH := .env_google_credentials.json

# Telegram Bot
TELEGRAM_SOSENKI_BOT := SG_SOSenki_Bot

# Mini App
TELEGRAM_MINI_APP_ID := sosenki-mini-app-id

.PHONY: help seed test lint format install serve db-reset

help:
	@echo "SOSenki Development Commands"
	@echo ""
	@echo "  make help              Show this help message"
	@echo "  make install           Install dependencies via uv"
	@echo "  make test              Run all tests (contract, integration, unit)"
	@echo "  make lint              Check code style with ruff"
	@echo "  make format            Format code with ruff and prettier"
	@echo "  make seed              Seed database from Google Sheets (OFFLINE ONLY)"
	@echo "  make db-reset          Drop and recreate database (OFFLINE ONLY)"
	@echo ""
	@echo "Local Development:"
	@echo "  make serve             Run bot + mini app with webhook (starts ngrok if needed)"
	@echo ""
	@echo "Database Seeding:"
	@echo "  make seed              Synchronize local SQLite with canonical Google Sheet"
	@echo "                         Must run when application is OFFLINE"
	@echo "                         Idempotent: running twice = identical database state"
	@echo "  make db-reset          Drop and recreate database from scratch"
	@echo "                         Must run when application is OFFLINE"
	@echo ""

install:
	uv sync

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check .

format:
	uv run ruff check . --fix
	uv run ruff format .

# Database Seeding from Google Sheets
# IMPORTANT: Application MUST be offline when running this command
# This command is idempotent: running it multiple times produces the same result
# Logs are written to logs/seed.log and stdout (INFO level)
seed:
	@echo "Starting database seed from Google Sheets..."
	@echo "IMPORTANT: Ensure the application is offline before proceeding"
	@echo ""
	export DATABASE_URL=$(DATABASE_URL); \
	export GOOGLE_CREDENTIALS_PATH=$(GOOGLE_CREDENTIALS_PATH); \
	uv run python -m src.cli.seed
	@echo ""
	@echo "Seed complete! Check logs/seed.log for details"

# Drop and recreate database from scratch
# IMPORTANT: Application MUST be offline when running this command
# This will delete all data and recreate fresh schema
db-reset:
	@echo "Resetting database: $(DB_FILE)"
	@echo "IMPORTANT: Ensure the application is offline before proceeding"
	@echo ""
	rm -fv $(DB_FILE) && ls -lah $(DB_FILE) 2>&1 || echo "Database deleted successfully"
	@echo "Database deleted"
	@echo ""
	@echo "Recreating database schema via Alembic..."
	export DATABASE_URL=$(DATABASE_URL); \
	uv run alembic upgrade head
	@echo ""
	@echo "Database reset complete! Ready for seeding with 'make seed'"

# Local Development with Webhook Mode

# Run bot + mini app in webhook mode with ngrok tunnel
# Automatically starts ngrok if not already running
# ngrok configuration is already set up in .ngrok.yml
serve:
	@# Check if ngrok is already running
	@if ! pgrep -f "ngrok http 8000" > /dev/null; then \
		echo "ngrok not running. Starting ngrok tunnel on port 8000..."; \
		ngrok http 8000 > /dev/null 2>&1 & \
		NGROK_PID=$$!; \
		echo "ngrok started with PID $$NGROK_PID"; \
		sleep 2; \
	else \
		echo "ngrok is already running"; \
	fi
	@# Get ngrok tunnel URL from API
	@TUNNEL_URL=$$(curl -s http://127.0.0.1:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | cut -d'"' -f4); \
	if [ -z "$$TUNNEL_URL" ]; then \
		echo "ERROR: Could not retrieve ngrok tunnel URL"; \
		echo "Make sure ngrok is running and accessible at http://127.0.0.1:4040"; \
		exit 1; \
	fi; \
	echo "Tunnel URL: $$TUNNEL_URL"; \
	export DATABASE_URL=$(DATABASE_URL); \
	export GOOGLE_CREDENTIALS_PATH=$(GOOGLE_CREDENTIALS_PATH); \
	export TELEGRAM_MINI_APP_ID=$(TELEGRAM_MINI_APP_ID); \
	export TELEGRAM_SOSENKI_BOT=$(TELEGRAM_SOSENKI_BOT); \
	export NGROK_TUNNEL_URL=$$TUNNEL_URL; \
	export WEBHOOK_URL=$$TUNNEL_URL/webhook/telegram; \
	export MINI_APP_URL=$$TUNNEL_URL/mini-app; \
	echo "Starting bot + mini app in webhook mode..."; \
	echo "Webhook URL: $$WEBHOOK_URL"; \
	echo "Mini App URL: $$MINI_APP_URL"; \
	echo "Logs: logs/server.log"; \
	echo "Press Ctrl+C to stop"; \
	echo ""; \
	uv run python -m src.main --mode webhook
