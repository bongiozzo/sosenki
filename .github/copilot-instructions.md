# SOSenki Copilot Instructions

DRY/KISS/YAGNI are main principles! Follow repo conventions exactly; if something conflicts or is unclear, stop and ask (don’t guess).

## Big Picture
- Stack: Telegram bot (python-telegram-bot) + FastAPI backend + Telegram Mini App (vanilla JS).
- Key dirs: `src/api/` (FastAPI + webhook + Mini App API + MCP), `src/bot/` (handlers/config), `src/services/` (business logic), `src/static/mini_app/` (Mini App assets + `translations.json`), `alembic/versions/` (migrations), `tests/{unit,contract,integration}`.

## Runtime & Dev Workflows (use these)
- Use: `make sync`, `make serve`, `make stop`, `make test`, `make format`, `make coverage`, `make check-i18n`.
- Targeted tests are OK: `uv run pytest tests/path::test_name -v`.
- Don’t run `uvicorn`/`python`/`pytest` directly for app lifecycle; don’t kill ports manually.

## HTTP/App Layout
- FastAPI app is in `src/api/webhook.py` and uses `mcp_http_app.lifespan` for DB lifecycle.
- Routes/mounts:
	- `POST /webhook/telegram` → converts JSON to `telegram.Update` and calls `_bot_app.process_update()`.
	- `GET /health`.
	- `GET /mini-app/*` → serves static Mini App from `src/static/mini_app/`.
	- `POST /api/mini-app/*` → Mini App API (auth + context + data).
	- `/mcp` → FastMCP HTTP app (see `src/api/mcp_server.py`).
- “Tools” exist in two places: MCP tools are defined in `src/api/mcp_server.py`; LLM tool selection/gating lives in `src/services/llm_service.py` (`get_user_tools()`/`get_admin_tools()` + `execute_tool()` with `ctx.is_admin`).

## Env + Local Dev
- `.env` controls `ENV=dev|prod` and `DATABASE_URL` (dev DB `sosenki.dev.db`, prod `sosenki.db`, tests `test_sosenki.db`).
- `make serve` writes `/tmp/.sosenki-env` with `WEBHOOK_URL`/`MINI_APP_URL` (ngrok in dev). `src/bot/config.py` lazily loads config; instantiate config only after env is loaded.

## Auth & Authorization (Mini App)
- Telegram init data transport order (see `src/services/auth_service.py`):
	- `Authorization: tma <raw>`
	- `X-Telegram-Init-Data`
	- request body fields `initDataRaw|initData|init_data_raw|init_data`
- Signature verification is centralized; endpoints should call `verify_telegram_auth()` → `get_authenticated_user()`.
- Target-user resolution rules: admin context switch (`selected_user_id`) > representation (`representative_id`) > self.
- For account-scoped endpoints, enforce `authorize_account_access*()` instead of hand-rolled checks.

## Service-Layer Conventions
- Keep business logic in `src/services/*_service.py`; handlers/endpoints should be thin.
- Audit logging lives in the service layer: call `AuditService` after `session.flush()` (not in bot handlers/routes).
- Formatting/parsing: use `src/services/locale_service.py` and `src/utils/parsers.py` (no custom currency/decimal parsing).

## i18n (Mini App + API)
- Single source of truth: `src/static/mini_app/translations.json` (flat keys with prefixes like `btn_`, `err_`, `msg_`, etc.).
- Python uses `src/services/localizer.py` `t(key, **kwargs)`; Mini App JS uses `t()` + `data-i18n` in HTML.
- After changing user-facing strings, run `make check-i18n`.

## Migrations & Seeding
- Migrations: `uv run alembic revision --autogenerate -m "msg"` then `uv run alembic upgrade head`.
- After a dev schema change: `uv run alembic upgrade head && make seed`.
- Seeding is separate (`seeding/`) and must run with the app offline: `make seed` (dev only). Uses Google Sheets via `SEEDING_CONFIG_PATH` + `GOOGLE_CREDENTIALS_PATH`.

## Notes / Known TODOs
- Security hardening TODOs are tracked in the Makefile (auth_date expiration, `hmac.compare_digest`, rate limiting, CORS `allow_credentials`). Don’t “fix” them unless requested.

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
