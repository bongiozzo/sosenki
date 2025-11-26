# TODO feat: Align CSS and add Figma MCP to fix wrapping
# - https://www.figma.com/community/file/1248595286803212338/telegram-graphics
# TODO refactor: Access rights - Account details for Administrator
# TODO feat: Management from bot - MCP server for query and Endpoints for actions, 
# TODO feat: Production from branch main and Dev from dev
# TODO refactor: Make git-filter-repo to clean history
# TODO feat: Invest part
# TODO feat: Rule part with Job descriptions

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

.PHONY: help seed test lint format install serve db-reset dead-code coverage coverage-seeding sync-design check-i18n clean

help:
	@echo "SOSenki Development Commands"
	@echo ""
	@echo "  make help              Show this help message"
	@echo "  make install           Install dependencies via uv"
	@echo "  make test              Run all tests (contract, integration, unit)"
	@echo "  make test-seeding      Run seeding tests only"
	@echo "  make lint              Check code style with ruff"
	@echo "  make format            Format code with ruff and prettier"
	@echo "  make check-i18n        Validate translation completeness"
	@echo "  make dead-code         Analyze dead code with vulture and custom scripts"
	@echo "  make coverage          Generate coverage report for src/ tests"
	@echo "  make sync-design       Sync design tokens from Figma"
	@echo ""
	@echo "Database Seeding & Management:"
	@echo "  make seed              Seed database from Google Sheets (OFFLINE ONLY)"
	@echo "                         Idempotent: running twice = identical database state"
	@echo "  make db-reset          Drop and recreate database (OFFLINE ONLY)"
	@echo "                         Deletes all data and recreates fresh schema"
	@echo ""
	@echo "Local Development:"
	@echo "  make serve             Run bot + mini app with webhook (starts ngrok if needed)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean             Remove generated artifacts (coverage, cache, logs)"
	@echo ""

install:
	uv sync

test:
	uv run pytest tests/ -v

test-seeding:
	uv run pytest seeding/tests/ -v

lint:
	uv run ruff check .

check-i18n:
	uv run python scripts/check_translations.py

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

# Dead code detection
# Identifies unused variables, functions, and code paths using two tools:
# - vulture: Static analysis with confidence threshold (80%)
# - analyze_dead_code.py: Custom analysis script for project-specific patterns
# Output helps identify refactoring opportunities and code cleanup targets
dead-code:
	@echo "Analyzing dead code..."
	uv run vulture src/ --min-confidence 80
	uv run python scripts/analyze_dead_code.py

# Coverage report (src/ tests only, excluding seeding)
coverage:
	uv run pytest tests/ --cov=src --cov-report=term-missing --cov-report=html -q
	@echo ""
	@echo "✓ Coverage report complete"
	@echo "Open htmlcov/index.html to view detailed coverage report"


# Design tokens sync
sync-design:
	@echo "Syncing design tokens from Figma..."
	uv run python scripts/sync_figma_tokens.py

# Local Development with Webhook Mode

# Run bot + mini app in webhook mode with ngrok tunnel
# Automatically starts ngrok tunnel and loads environment variables (dynamic + static from .env)
serve:
	@bash scripts/setup-environment.sh && \
	echo "Starting bot + mini app in webhook mode..." && \
	echo "Logs: logs/server.log" && \
	echo "Press Ctrl+C to stop" && \
	echo "" && \
	uv run python -m src.main --mode webhook

# Clean generated artifacts
clean:
	@echo "Cleaning generated artifacts..."
	rm -rf .pytest_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage coverage.json htmlcov/
	rm -rf logs/*.log
	@echo "Clean complete!"
