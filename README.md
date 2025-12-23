# SOSenki

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Shared-Goals/SOSenki)

**Shared property management for small communities** — Telegram bot + Mini App for tracking bills, balances, and service periods.

## Presentation (5 slides, ~5 min)

- Live docs site: https://sosenki-docs.sharedgoals.ru/
- Live slides: https://sosenki-docs.sharedgoals.ru/presentation/
- Slides (Markdown source in repo): `docs/presentation/slides.md`
- Slides (HTML viewer in repo): `docs/presentation/index.html`

## Goals

- Make shared expenses transparent for co-owners/stakeholders.
- Keep it self-hosted and simple (YAGNI/KISS): SQLite + Python + Telegram as the UI.
- Prefer auditable workflows over complex dashboards.

## Project principles

- Open source and practical: small pieces, clear boundaries, minimal moving parts.
- Telegram-first UX: bot + Mini App, no separate “web product”.

## Architecture (quick map)

- FastAPI app: `src/api/webhook.py`
	- `POST /webhook/telegram` — Telegram webhook updates
	- `GET /health` — health check
	- `GET /mini-app/*` — serves static Mini App
	- `POST /api/mini-app/*` — Mini App API
	- `/mcp` — FastMCP HTTP app (tools)
- Service layer (business logic): `src/services/*_service.py`
- Mini App assets: `src/static/mini_app/` (`index.html`, `app.js`, `translations.json`)

## Development (recommended workflow)

Use the Makefile targets; don’t run app lifecycle commands directly.

```bash
make sync
make serve
```

Run tests:

```bash
make test
```

Formatting:

```bash
make format
```

## Deployment (production)

See the Makefile help for the full workflow:

```bash
make help
```

## Seeding (dev only)

- Seeding lives in `seeding/` and is intentionally separate from runtime code.
- Reads data from Google Sheets; see `seeding/README.md`.
- Run with the application offline:

```bash
make seed
```

## Notes for contributors and AI agents

- Repo-specific conventions are documented in `.github/copilot-instructions.md`.

## Documentation

Live docs site: https://sosenki-docs.sharedgoals.ru/

Auto-generated docs: [DeepWiki](https://deepwiki.com/Shared-Goals/SOSenki)
