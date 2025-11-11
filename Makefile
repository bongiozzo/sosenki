.PHONY: help seed test lint format install

help:
	@echo "SOSenki Development Commands"
	@echo ""
	@echo "  make help              Show this help message"
	@echo "  make install           Install dependencies via uv"
	@echo "  make test              Run all tests (contract, integration, unit)"
	@echo "  make lint              Check code style with ruff"
	@echo "  make format            Format code with ruff and prettier"
	@echo "  make seed              Seed database from Google Sheets (OFFLINE ONLY)"
	@echo ""
	@echo "Database Seeding:"
	@echo "  make seed              Synchronize local SQLite with canonical Google Sheet"
	@echo "                         Must run when application is OFFLINE"
	@echo "                         Idempotent: running twice = identical database state"
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
	uv run python -m src.cli.seed
	@echo ""
	@echo "Seed complete! Check logs/seed.log for details"
