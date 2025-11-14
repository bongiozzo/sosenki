# SOSenki Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-04

## Active Technologies
- Python 3.11+ (per constitution) + FastAPI (API serving), python-telegram-bot (Telegram integration), Telegram Web App API (Mini App client-side) (002-welcome-mini-app)
- SQLite (development) + SQLAlchemy ORM, Alembic migrations (per constitution) (002-welcome-mini-app)
- Python 3.11+ (backend), HTML5/CSS3/JavaScript (frontend) + FastAPI (existing), python-telegram-bot (existing), WebApp API (Telegram platform) (005-mini-app-dashboard)
- SQLite (existing User model, no schema changes) (005-mini-app-dashboard)

- Python 3.11+ + `python-telegram-bot` library (async webhooks), FastAPI (request handling), SQLAlchemy (ORM), Alembic (migrations) (001-request-approval)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 005-mini-app-dashboard: Added Python 3.11+ (backend), HTML5/CSS3/JavaScript (frontend) + FastAPI (existing), python-telegram-bot (existing), WebApp API (Telegram platform)
- 002-welcome-mini-app: Added Python 3.11+ (per constitution) + FastAPI (API serving), python-telegram-bot (Telegram integration), Telegram Web App API (Mini App client-side)

- 001-request-approval: Added Python 3.11+ + `python-telegram-bot` library (async webhooks), FastAPI (request handling), SQLAlchemy (ORM), Alembic (migrations)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
