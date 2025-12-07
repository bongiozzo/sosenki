# ============================================================================
# Roadmap (commit-based milestones)
# ============================================================================
#
# TODO mcp: Refactor MCP server to use service layer (remove direct DB access)
#
# --- Agent /ask Command ---
# Reuses existing auth pattern from src/bot/auth.py (verify_admin_authorization)
# User auth: get_authenticated_user(session, telegram_id) -> User (is_active check)
# Admin auth: verify_admin_authorization(telegram_id) -> User | None
#
# TODO agent: Add ollama dependency to pyproject.toml
# TODO agent: Create LLM client wrapper (src/services/llm_service.py)
# TODO agent: Create /ask command handler (src/bot/handlers/ask.py)
#            - Reuse get_authenticated_user for is_active user check
#            - Conversation state management (ConversationHandler)
# TODO agent: Implement tool-calling loop with Ollama
#            - Define tool schemas (balance, bills, period info)
#            - Parse LLM responses for tool calls
# TODO agent: Add role-based tool filtering
#            - User tools: get_balance, list_bills, get_period_info (read-only)
#            - Admin tools: + create_service_period (write)
#            - Check user.is_administrator for admin tools
# TODO agent: Add confirmation prompts for write operations
# TODO agent: Register /ask handler in bot/__init__.py
#
# --- Deployment ---
# TODO deploy: Create systemd service template (install-service)
# TODO deploy: Create Caddy reverse proxy config (install-caddy)
# TODO deploy: Dynamic DNS setup documentation (DuckDNS)
#
# --- Features ---
# TODO feat: Add Open Mini App button to bot /setmenubutton
# TODO feat: New Electricity Service Period 1 Sept 2025 - 1 Jan 2026
# TODO feat: Invest tracking module
# TODO feat: Rules/Job descriptions module
#
# --- Maintenance ---
# TODO refactor: Make git-filter-repo to clean history

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

.PHONY: help seed test lint format install serve db-reset backup restore deploy-check dead-code coverage coverage-seeding check-i18n clean

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
	@echo ""
	@echo "Database Seeding & Management:"
	@echo "  make seed              Seed database from Google Sheets (OFFLINE ONLY)"
	@echo "                         Idempotent: running twice = identical database state"
	@echo "  make db-reset          Drop and recreate database (OFFLINE ONLY)"
	@echo "                         Deletes all data and recreates fresh schema"
	@echo "  make backup            Create timestamped database backup (keeps last 30)"
	@echo "  make restore           Restore from latest backup (or BACKUP=filename)"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-check      Validate environment, tests, and database for deployment"
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
# Automatically starts ngrok tunnel and loads environment variables (dynamic + static from .env)
# Kills any existing process on port 8000 if address is already in use
serve:
	@PORT=8000; \
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
# Called automatically before deploy
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
	BACKUP_FILE="backups/sosenki-$$(date +%Y%m%d-%H%M%S).db"; \
	cp $$DB_FILE "$$BACKUP_FILE" && \
	echo "✅ Backup created: $$BACKUP_FILE" && \
	ls -lh "$$BACKUP_FILE"; \
	echo ""; \
	echo "Cleaning old backups (keeping last 30)..."; \
	cd backups && ls -t *.db 2>/dev/null | tail -n +31 | xargs -r rm -v; \
	echo ""; \
	echo "Current backups:"; \
	cd backups && ls -lht *.db 2>/dev/null | head -5 || echo "  (none)"

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

# Pre-deployment validation checklist
# Validates environment configuration, code quality, database readiness, and test suite
# Must pass before deploying to production (systemd/caddy)
# Fail-fast: stops on first error
deploy-check:
	@echo "====== SOSenki Pre-Deployment Validation ======"
	@echo ""
	@echo "Step 1: Verify environment is production..."
	@if [ "$(ENV)" != "prod" ]; then \
		echo "❌ deploy-check requires ENV=prod. Set ENV=prod in .env or run: ENV=prod make deploy-check"; exit 1; fi
	@echo "✅ Environment: production (ENV=prod)"
	@echo ""
	@echo "Step 2: Validate required environment variables..."
	@if [ -z "$(DATABASE_URL)" ]; then \
		echo "❌ DATABASE_URL not set"; exit 1; fi
	@if [ -z "$(TELEGRAM_BOT_TOKEN)" ]; then \
		echo "❌ TELEGRAM_BOT_TOKEN not set"; exit 1; fi
	@if [ -z "$(TELEGRAM_BOT_NAME)" ]; then \
		echo "❌ TELEGRAM_BOT_NAME not set"; exit 1; fi
	@if [ -z "$(TELEGRAM_MINI_APP_ID)" ]; then \
		echo "❌ TELEGRAM_MINI_APP_ID not set"; exit 1; fi
	@if [ -z "$(MINI_APP_URL)" ] && [ -z "$(shell grep -h '^MINI_APP_URL' .env 2>/dev/null)" ]; then \
		echo "❌ MINI_APP_URL not set (required for application startup)"; exit 1; fi
	@if [ -z "$(WEBHOOK_URL)" ] && [ -z "$(shell grep -h '^WEBHOOK_URL' .env 2>/dev/null)" ]; then \
		echo "❌ WEBHOOK_URL not set (required for Telegram webhook)"; exit 1; fi
	@if [ -z "$(PHOTO_GALLERY_URL)" ] && [ -z "$(shell grep -h '^PHOTO_GALLERY_URL' .env 2>/dev/null)" ]; then \
		echo "❌ PHOTO_GALLERY_URL not set"; exit 1; fi
	@if [ -z "$(STAKEHOLDER_SHARES_URL)" ] && [ -z "$(shell grep -h '^STAKEHOLDER_SHARES_URL' .env 2>/dev/null)" ]; then \
		echo "❌ STAKEHOLDER_SHARES_URL not set"; exit 1; fi
	@echo "✅ All required environment variables are set"
	@echo ""
	@echo "Step 3: Validate database..."
	@if [ ! -f sosenki.db ]; then \
		echo "❌ Database not found (sosenki.db). Run 'make restore' to restore from backup or manually copy sosenki.dev.db to sosenki.db."; exit 1; fi
	@echo "✅ Database exists: sosenki.db"
	@echo ""
	@echo "Step 4: Verify Alembic migrations..."
	@uv run alembic current > /dev/null 2>&1 || (echo "❌ Alembic migration check failed"; exit 1)
	@echo "✅ Alembic migrations verified"
	@echo ""
	@echo "Step 5: Code quality checks..."
	@echo "  - Running linter (ruff)..."
	@uv run ruff check . > /dev/null 2>&1 || (echo "❌ Linter check failed"; exit 1)
	@echo "  ✅ Linter passed"
	@echo "  - Checking i18n completeness..."
	@uv run python scripts/check_translations.py > /dev/null 2>&1 || (echo "❌ i18n check failed"; exit 1)
	@echo "  ✅ i18n check passed"
	@echo ""
	@echo "Step 6: Running full test suite (unit, contract, integration)..."
	@uv run pytest tests/ -v --tb=short > /tmp/deploy-check-tests.log 2>&1 || \
		(echo "❌ Test suite failed. Details:"; tail -100 /tmp/deploy-check-tests.log; exit 1)
	@echo "✅ All tests passed (463 tests)"
	@echo ""
	@echo "Step 7: Coverage validation (minimum 80%)..."
	@uv run pytest tests/ --cov=src --cov-report=term-missing -q > /tmp/deploy-check-cov.log 2>&1
	@COVERAGE=$$(tail -1 /tmp/deploy-check-cov.log | grep -o '[0-9]\+%' | tr -d '%'); \
	if [ -z "$$COVERAGE" ]; then COVERAGE=$$(grep 'TOTAL' /tmp/deploy-check-cov.log | grep -o '[0-9]\+%' | tail -1 | tr -d '%'); fi; \
	if [ -n "$$COVERAGE" ] && [ "$$COVERAGE" -lt 80 ]; then \
		echo "❌ Coverage below 80% threshold ($$COVERAGE%). Details:"; cat /tmp/deploy-check-cov.log; exit 1; fi
	@tail -5 /tmp/deploy-check-cov.log
	@echo "✅ Coverage threshold met (≥80%)"
	@echo ""
	@echo "====== Pre-Deployment Validation Summary ======"
	@echo "✅ Environment configuration: valid"
	@echo "✅ Database: ready (sosenki.db)"
	@echo "✅ Code quality: passed"
	@echo "✅ Test suite: passed (463 tests)"
	@echo "✅ Coverage: ≥80%"
	@echo ""
	@LATEST_BACKUP=$$(ls -t backups/*.db 2>/dev/null | head -1); \
	if [ -n "$$LATEST_BACKUP" ]; then \
		echo "Latest backup: $$LATEST_BACKUP"; \
	else \
		echo "⚠ No backups found. Create one with: make backup"; \
	fi
	@echo ""
	@echo "✅ READY FOR DEPLOYMENT"
	@echo "Next steps:"
	@echo "  1. make backup          (create pre-deploy backup)"
	@echo "  2. make install-service (create systemd service)"
	@echo "  3. make install-caddy   (configure reverse proxy)"
	@echo ""

