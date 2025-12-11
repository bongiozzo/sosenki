# ============================================================================
# Roadmap (commit-based milestones)
# ============================================================================
#
# TODO feat: Limit /request as the only command for new users
# TODO agent: Add role-based tool filtering
#            - User tools: get_balance, list_bills, get_period_info (read-only)
#            - Admin tools: + create_service_period (write)
#            - Check user.is_administrator for admin tools
# TODO agent: Add confirmation prompts for write operations
#
# --- Features ---
# TODO feat: Invest tracking module
# TODO feat: Rules/Job descriptions module
# TODO feat: New Electricity Service Period 1 Sept 2025 - 1 Jan 2026
#
# ============================================================================
# Configuration
# ============================================================================

# Environment detection FIRST (before .env) to allow command-line override
# Usage: ENV=prod make deploy-check
ENV ?= dev

# Source shared environment configuration from .env
include .env

# Reapply ENV for command-line override
ENV ?= dev

export DATABASE_URL
export GOOGLE_CREDENTIALS_PATH
export GOOGLE_SHEET_ID
export TELEGRAM_BOT_NAME
export TELEGRAM_MINI_APP_ID
export ENV

.PHONY: help seed test lint format sync install preflight serve db-reset backup restore dead-code coverage coverage-seeding check-i18n clean

help:
	@echo "SOSenki Commands"
	@echo ""
	@echo "Production Deployment (Linux server):"
	@echo "  make install           Full production setup (run with sudo)"
	@echo ""
	@echo "Development:"
	@echo "  make sync              Install Python dependencies via uv"
	@echo "  make serve             Run bot + mini app with webhook (starts ngrok if needed)"
	@echo "  make test              Run all tests (contract, integration, unit)"
	@echo "  make test-seeding      Run seeding tests only"
	@echo "  make lint              Check code style with ruff"
	@echo "  make format            Format code with ruff and prettier"
	@echo "  make check-i18n        Validate translation completeness"
	@echo "  make dead-code         Analyze dead code with vulture and custom scripts"
	@echo "  make coverage          Generate coverage report for src/ tests"
	@echo ""
	@echo "Database:"
	@echo "  make seed              Seed database from Google Sheets (dev only)"
	@echo "  make db-reset          Drop and recreate database (dev only)"
	@echo "  make backup            Create timestamped database backup (prod only)"
	@echo "  make restore           Restore from latest backup (prod only)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean             Remove generated artifacts (coverage, cache, logs)"
	@echo ""

# ============================================================================
# Production Deployment
# ============================================================================

# Preflight checks (used by install and can be run standalone)
# Checks differ based on ENV: dev or prod
preflight:
	@echo "====== SOSenki Preflight Checks (ENV=$(ENV)) ======"
	@echo ""
	@echo "Step 1: Check uv installed..."
	@command -v uv >/dev/null 2>&1 || \
		(echo "❌ uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1)
	@echo "✅ uv installed"
	@echo ""
	@echo "Step 2: Check .env exists..."
	@test -f .env || (echo "❌ .env not found. Copy from .env.example and configure."; exit 1)
	@echo "✅ .env exists"
	@echo ""
	@echo "Step 3: Validate environment variables..."
	@if [ -z "$(TELEGRAM_BOT_TOKEN)" ]; then echo "❌ TELEGRAM_BOT_TOKEN not set"; exit 1; fi
	@if [ -z "$(TELEGRAM_BOT_NAME)" ]; then echo "❌ TELEGRAM_BOT_NAME not set"; exit 1; fi
	@if [ -z "$(TELEGRAM_MINI_APP_ID)" ]; then echo "❌ TELEGRAM_MINI_APP_ID not set"; exit 1; fi
	@if [ "$(ENV)" = "prod" ]; then \
		DOMAIN=$$(grep -E '^DOMAIN=' .env 2>/dev/null | cut -d'=' -f2 | tr -d '"' | tr -d "'"); \
		if [ -z "$$DOMAIN" ]; then echo "❌ DOMAIN not set (required for prod)"; exit 1; fi; \
		echo "✅ DOMAIN: $$DOMAIN"; \
	fi
	@echo "✅ Environment variables validated"
	@echo ""
	@echo "Step 4: Installing Python dependencies..."
	@uv sync
	@echo "✅ Python dependencies installed"
	@echo ""
	@echo "Step 5: Check Ollama (optional LLM support)..."
	@MODEL=$$(grep -E '^OLLAMA_MODEL=' .env 2>/dev/null | cut -d'=' -f2 | tr -d '"' | tr -d "'"); \
	if [ -z "$$MODEL" ]; then \
		echo "⚠️  OLLAMA_MODEL not set - LLM features disabled"; \
	else \
		if command -v ollama >/dev/null 2>&1; then \
			echo "Model: $$MODEL"; \
			ollama pull "$$MODEL" && echo "✅ Ollama model ready"; \
		else \
			echo "⚠️  Ollama not installed - LLM features disabled"; \
			echo "   Install: curl -fsSL https://ollama.com/install.sh | sh"; \
		fi; \
	fi
	@if [ "$(ENV)" = "prod" ]; then \
		echo ""; \
		echo "Step 6: Check Caddy installed (prod only)..."; \
		command -v caddy >/dev/null 2>&1 || \
			(echo "❌ Caddy not found. Install: apt install caddy"; exit 1); \
		echo "✅ Caddy installed"; \
		echo ""; \
		echo "Step 7: Validate database (prod only)..."; \
		if [ ! -f sosenki.db ]; then \
			echo "❌ Database not found (sosenki.db). Run 'make restore' to restore from backup."; exit 1; \
		fi; \
		echo "✅ Database exists: sosenki.db"; \
		echo ""; \
		echo "Step 8: Verify Alembic migrations (prod only)..."; \
		uv run alembic current > /dev/null 2>&1 || (echo "❌ Alembic migration check failed"; exit 1); \
		echo "✅ Alembic migrations verified"; \
		echo ""; \
		echo "Step 9: Running test suite (prod only)..."; \
		uv run pytest tests/ -q --tb=short > /tmp/preflight-tests.log 2>&1 || \
			(echo "❌ Test suite failed. Details:"; tail -50 /tmp/preflight-tests.log; exit 1); \
		echo "✅ All tests passed"; \
	fi
	@echo ""
	@echo "====== Preflight Complete ======"

# Full production installation
# Step order:
# 1. Run preflight manually: make preflight ENV=prod
# 2. Run install: sudo make install
#    - This installs systemd service and configures Caddy
#    - Preflight must be run first to ensure uv sync and ollama pull are done
install:
	@echo ""
	@echo "====== SOSenki Production Install ======"
	@echo ""
	@echo "Step 1/2: Installing systemd service (requires sudo)..."
	@INSTALL_DIR=$$(pwd); \
	OWNER=$$(stat -c '%U' . 2>/dev/null || stat -f '%Su' .); \
	sed -e "s|\$${INSTALL_DIR}|$$INSTALL_DIR|g" \
	    -e "s|\$${USER}|$$OWNER|g" \
	    deploy/sosenki.service.template > /tmp/sosenki.service; \
	sudo cp /tmp/sosenki.service /etc/systemd/system/sosenki.service; \
	sudo systemctl daemon-reload; \
	sudo systemctl enable sosenki
	@echo "✅ Systemd service installed"
	@echo ""
	@echo "Step 2/2: Configuring domain and URLs (requires sudo)..."
	@DOMAIN=$$(grep -E '^DOMAIN=' .env 2>/dev/null | cut -d'=' -f2 | tr -d '"' | tr -d "'"); \
	if [ -z "$$DOMAIN" ]; then \
		echo "❌ DOMAIN not set in .env. Required for Caddy and webhook URLs."; \
		exit 1; \
	fi; \
	echo "Domain: $$DOMAIN"; \
	WEBHOOK_URL="https://$$DOMAIN/webhook/telegram"; \
	MINI_APP_URL="https://$$DOMAIN/mini-app/"; \
	if ! grep -q '^WEBHOOK_URL=' .env 2>/dev/null; then \
		echo "WEBHOOK_URL=$$WEBHOOK_URL" >> .env; \
		echo "  Added WEBHOOK_URL to .env"; \
	fi; \
	if ! grep -q '^MINI_APP_URL=' .env 2>/dev/null; then \
		echo "MINI_APP_URL=$$MINI_APP_URL" >> .env; \
		echo "  Added MINI_APP_URL to .env"; \
	fi; \
	sed -e "s|\$${DOMAIN}|$$DOMAIN|g" deploy/Caddyfile.template > /tmp/sosenki.caddy; \
	sudo mkdir -p /etc/caddy; \
	sudo cp /tmp/sosenki.caddy /etc/caddy/Caddyfile; \
	sudo systemctl reload caddy 2>/dev/null || sudo systemctl restart caddy
	@echo "✅ Caddy configured for $$DOMAIN"
	@echo ""
	@echo "====== Installation Complete ======"
	@echo ""
	@echo "Start the service:"
	@echo "  sudo systemctl start sosenki"
	@echo ""
	@echo "View logs:"
	@echo "  sudo journalctl -u sosenki -f"
	@echo ""

# ============================================================================
# Development Targets
# ============================================================================

# Install Python dependencies (dev)
sync:
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

# ============================================================================
# Development Targets (ENV=dev, sosenki.dev.db)
# ============================================================================

# Database Seeding from Google Sheets (dev only)
# IMPORTANT: Application MUST be offline when running this command
# This command is idempotent: running it multiple times produces the same result
# Logs are written to logs/seed.log and stdout (INFO level)
# Configuration: seeding/config/seeding.json (copy from seeding.json.example)
# Credentials: credentials.json (from Google Cloud service account)
# NOTE: db-reset is a prerequisite and will run automatically
# BLOCKED in production: seed modifies runtime data, only use in dev
seed: db-reset
	@if [ "$(ENV)" = "prod" ]; then \
		echo "❌ seed is blocked in production. Production data is only modified via restore from backup."; \
		exit 1; \
	fi
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

# Drop and recreate database from scratch (dev only)
# IMPORTANT: Application MUST be offline when running this command
# This will delete all data and recreate fresh schema
# BLOCKED in production: use restore from backup instead
db-reset:
	@if [ "$(ENV)" = "prod" ]; then \
		echo "❌ db-reset is blocked in production. Use 'make restore' to restore from backup."; \
		exit 1; \
	fi; \
	DB_FILE=$$([ "$(ENV)" = "prod" ] && echo "sosenki.db" || echo "sosenki.dev.db"); \
	echo "Resetting database: $$DB_FILE"; \
	echo "IMPORTANT: Ensure the application is offline before proceeding"; \
	echo ""; \
	rm -fv $$DB_FILE && ls -lah $$DB_FILE 2>&1 || echo "Database deleted successfully"; \
	echo "Database deleted"; \
	echo ""; \
	echo "Recreating database schema via Alembic..."; \
	uv run alembic upgrade head; \
	echo ""; \
	echo "Database reset complete! Ready for seeding with 'make seed'"

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

# Local Development with Webhook Mode

# Run bot + mini app in webhook mode with ngrok tunnel
# Automatically starts Ollama (if not running), ngrok tunnel, and loads environment variables (dynamic + static from .env)
# Kills any existing process on configured port if address is already in use
serve:
	@echo "🔍 Checking Ollama service..."
	@if ! pgrep -f "ollama serve" > /dev/null; then \
		echo "❌ Ollama is not running. Starting..."; \
		brew services start ollama > /dev/null 2>&1 && echo "✅ Ollama started" || (echo "❌ Failed to start Ollama"; exit 1); \
		sleep 2; \
	else \
		echo "✅ Ollama is running"; \
	fi
	@PORT=$$(grep '^PORT=' .env 2>/dev/null | cut -d'=' -f2 || echo "8000"); \
	if lsof -Pi :$$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then \
		echo "⚠️  Port $$PORT is already in use. Killing existing process..."; \
		PID=$$(lsof -t -i :$$PORT); \
		kill -9 $$PID 2>/dev/null || true; \
		echo "✓ Killed process PID $$PID"; \
		sleep 1; \
	fi
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

# ============================================================================
# Production Targets (ENV=prod, sosenki.db)
# ============================================================================

# Database backup with timestamped filename (prod only)
# Creates backups/sosenki-YYYYMMDD-HHMMSS.db, keeps last 30 backups
# Only creates backup if database differs from last backup (uses diff)
# BLOCKED in dev: dev databases don't need backups (can be reset anytime)
backup:
	@if [ "$(ENV)" != "prod" ]; then \
		echo "⚠️  backup is not needed in dev (database can be reset anytime). Use 'make db-reset' instead."; \
		exit 1; \
	fi
	@DB_FILE=$$([ "$(ENV)" = "prod" ] && echo "sosenki.db" || echo "sosenki.dev.db"); \
	if [ ! -f $$DB_FILE ]; then \
		echo "❌ No database to backup ($$DB_FILE not found)"; \
		exit 1; \
	fi; \
	mkdir -p backups; \
	LAST_BACKUP=$$(ls -t backups/*.db 2>/dev/null | head -1); \
	if [ -n "$$LAST_BACKUP" ] && diff -q "$$DB_FILE" "$$LAST_BACKUP" > /dev/null 2>&1; then \
		echo "✅ Database unchanged since last backup: $$LAST_BACKUP"; \
		echo "   No new backup created."; \
	else \
		BACKUP_FILE="backups/sosenki-$$(date +%Y%m%d-%H%M%S).db"; \
		cp $$DB_FILE "$$BACKUP_FILE" && \
		echo "✅ Backup created: $$BACKUP_FILE" && \
		ls -lh "$$BACKUP_FILE"; \
		echo ""; \
		echo "Cleaning old backups (keeping last 30)..."; \
		cd backups && ls -t *.db 2>/dev/null | tail -n +31 | xargs -r rm -v; \
	fi; \
	echo ""; \
	echo "Current backups:"; \
	ls -lht backups/*.db 2>/dev/null | head -5 || echo "  (none)"

# Restore database from backup (prod only)
# Usage: make restore              (restores latest)\n#        make restore BACKUP=backups/sosenki-20251205-120000.db
# BLOCKED in dev: use 'make db-reset' instead
restore:
	@if [ "$(ENV)" != "prod" ]; then \
		echo "⚠️  restore is not needed in dev. Use 'make db-reset' to reset development database."; \
		exit 1; \
	fi
	@DB_FILE=$$([ "$(ENV)" = "prod" ] && echo "sosenki.db" || echo "sosenki.dev.db"); \
	if [ -n "$(BACKUP)" ]; then \
		BACKUP_FILE="$(BACKUP)"; \
	else \
		BACKUP_FILE=$$(ls -t backups/*.db 2>/dev/null | head -1); \
	fi; \
	if [ -z "$$BACKUP_FILE" ] || [ ! -f "$$BACKUP_FILE" ]; then \
		echo "❌ No backup found"; \
		exit 1; \
	fi; \
	echo "Restoring from: $$BACKUP_FILE"; \
	echo "This will OVERWRITE the current database."; \
	read -p "Continue? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		cp "$$BACKUP_FILE" $$DB_FILE && \
		echo "✅ Database restored from $$BACKUP_FILE"; \
	else \
		echo "Cancelled."; \
	fi



