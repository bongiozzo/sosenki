# TODO Switch to another user for Administrator
# TODO Test Coverage Report and find dead code
# TODO Finalize seeding and Report summary
# TODO Fix wrapped tagline on wide monitors
# TODO Localization support
# TODO Invest part
## TODO User management from bot - MCP server
# TODO Make git-filter-repo to clean history
# TODO Production from branch main and Dev from dev
# TODO Rule part with Job descriptions


# ============================================================================
# Configuration
# ============================================================================

# Source shared environment configuration from .env
include .env

export DATABASE_URL
export GOOGLE_CREDENTIALS_PATH
export GOOGLE_SHEET_ID
export TELEGRAM_BOT_NAME
export TELEGRAM_MINI_APP_ID

.PHONY: help seed test lint format install serve db-reset

help:
	@echo "SOSenki Development Commands"
	@echo ""
	@echo "  make help              Show this help message"
	@echo "  make install           Install dependencies via uv"
	@echo "  make test              Run all tests (contract, integration, unit)"
	@echo "  make test-contract     Run Mini App contract tests only"
	@echo "  make test-mini-app     Run Mini App tests (contract + integration)"
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

test-contract:
	uv run pytest tests/contract/test_mini_app_endpoints.py -v

test-mini-app:
	uv run pytest tests/contract/test_mini_app_endpoints.py tests/integration/test_approval_flow_to_mini_app.py -v

lint:
	uv run ruff check .

format:
	uv run ruff check . --fix
	uv run ruff format .

# Database Seeding from Google Sheets
# IMPORTANT: Application MUST be offline when running this command
# This command is idempotent: running it multiple times produces the same result
# Logs are written to logs/seed.log and stdout (INFO level)
# Configuration: seeding/config/seeding.json (copy from seeding.json.example)
# Credentials: credentials.json (from Google Cloud service account)
# NOTE: db-reset is a prerequisite and will run automatically
seed: db-reset
	@echo "Starting database seed from Google Sheets..."
	@echo "IMPORTANT: Ensure the application is offline before proceeding"
	@echo ""
	export DATABASE_URL=$(DATABASE_URL); \
	export GOOGLE_SHEET_ID=$(GOOGLE_SHEET_ID); \
	export GOOGLE_CREDENTIALS_PATH=$(GOOGLE_CREDENTIALS_PATH); \
	export SEEDING_CONFIG_PATH="seeding/config/seeding.json"; \
	uv run python -m seeding.cli.seed
	@echo ""
	@echo "Seed complete! Check logs/seed.log for details"

# Drop and recreate database from scratch
# IMPORTANT: Application MUST be offline when running this command
# This will delete all data and recreate fresh schema
db-reset:
	@echo "Resetting database: sosenki.db"
	@echo "IMPORTANT: Ensure the application is offline before proceeding"
	@echo ""
	rm -fv sosenki.db && ls -lah sosenki.db 2>&1 || echo "Database deleted successfully"
	@echo "Database deleted"
	@echo ""
	@echo "Recreating database schema via Alembic..."
	uv run alembic upgrade head
	@echo ""
	@echo "Database reset complete! Ready for seeding with 'make seed'"

# Local Development with Webhook Mode

# Run bot + mini app in webhook mode with ngrok tunnel
# Automatically starts ngrok tunnel and loads environment variables (dynamic + static from .env)
serve:
	@source ./setup-environment.sh && \
	echo "Starting bot + mini app in webhook mode..." && \
	echo "Logs: logs/server.log" && \
	echo "Press Ctrl+C to stop" && \
	echo "" && \
	uv run python -m src.main --mode webhook
