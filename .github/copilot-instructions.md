## Quick orientation for AI coding agents

This repo implements SOSenki — a Telegram Mini App built with a Python/FastAPI backend and a vanilla-JS frontend. Follow these repository-specific cues to be productive.

- Big picture
  - Backend: `backend/app/main.py` (FastAPI); models in `backend/app/models/`; Pydantic schemas in `backend/app/schemas/`; business logic in `backend/app/services/` (see `bill_service.py`, `bid_service.py`).
  - Frontend: Telegram Mini App UI in `frontend/src/` with `frontend/src/utils/telegram_sdk.js` wrapper and `frontend/src/api/client.js` for HTTP calls.
  - Data flow: frontend -> `frontend/src/api/client.js` -> FastAPI routes in `backend/app/api/routes/*.py` -> services -> PostgreSQL (SQLAlchemy in `backend/app/database.py`). Notifications are sent via `backend/app/services/telegram_bot.py`.

- Important workflows & commands
  - Local dev: `docker-compose.yml` boots backend, db and frontend for local testing.
  - Backend tests: run from project root or `backend/` — prefer `uv run pytest` if `uv` is installed, otherwise `python -m pytest backend/tests/`.
  - Formatting & linting (backend): `black .` and `flake8 app/` (run from `backend/`).
  - Frontend checks: `prettier --write src/` and `eslint src/` (run from `frontend/`).
  - Specs (Specification-Driven Development): `uv run spec-kit check` / `uv run spec-kit report` — specs live in `specs/` and drive feature implementation.

- Project conventions to follow
  - Spec-first: Implement features only when corresponding spec exists under `specs/` (see `specs/core` and `specs/features`).
  - Tests: Add pytest tests next to the backend logic changes in `backend/tests/`. `conftest.py` provides fixtures.
  - Commit & branches: English commit messages, branch name `feature/<short-desc>` and one logical change per commit (see `docs/CONTRIBUTING.md`).
  - API surface: update `specs/api_endpoints.md` for any new endpoint and keep `docs/API.md` consistent.

- Patterns and examples (do this, not that)
  - Business logic lives in `services/`, not in route handlers. Example: `bill_service.py` encapsulates bill calculation — modify service code and add tests rather than changing routes directly.
  - Models -> Schemas: Use SQLAlchemy models in `models/` and Pydantic schemas in `schemas/` for request/response validation.
  - Telegram notifications: Use `telegram_bot.py` service for sending messages; do not hard-code API calls elsewhere.

- Integration points and infra
  - External services: Telegram Bot API, Yandex Cloud for hosting, PostgreSQL as DB. Local credentials are mirrored in `.env.example`.
  - CI: GitHub Actions workflows in `.github/workflows/` run tests and linters; ensure new checks are covered there.

- Where to look for more context
  - Architecture and design decisions: `docs/ARCHITECTURE.md` and `docs/README.md` (high-level PRD).
  - Setup & deployment: `docs/SETUP.md` and `docs/DEPLOYMENT.md`.

If anything above is unclear or you need additional examples (small patch + tests) to illustrate a convention, tell me which area and I'll add a concrete, minimal PR-ready example. 
