# Title: feat(001): Seamless Telegram Auth — MVP onboarding + admin flow

Summary

This PR merges the `001-seamless-telegram-auth` feature branch into `main`. It implements the MVP Telegram Mini App onboarding flow and admin review/approval for access requests.

What changed

- Implemented `POST /miniapp/auth` initData verification
- Implemented request creation (`POST /requests`) and admin endpoints (`GET /admin/requests`, `POST /admin/requests/{id}/action`)
- Added models: `TelegramUserCandidate`, `AdminAction` audit log
- Notification plumbing with a `MockTransport` for tests
- OpenAPI contract: `specs/001-seamless-telegram-auth/contracts/openapi.yaml` (bumped to `openapi: 3.1.0` and validated)
- Tests: unit, contract, and integration tests covering main flows (50 tests, all passing locally)

CI / Validation

- All tests pass locally: 50 passed
- OpenAPI validation (Redocly) succeeded: 0 errors, 0 warnings
- Spectral linting should be run in CI. I attempted running locally with the Spectral CLI; please ensure CI provides a spectral ruleset (e.g., `spectral:oas`) or add a `.spectral.yaml` file.

Files of note

- `specs/001-seamless-telegram-auth/contracts/openapi.yaml` — API contract (now OpenAPI 3.1.0)
- `specs/001-seamless-telegram-auth/SEAMLESS-TELEGRAM-AUTH.md` — feature guide and next steps
- `backend/app/*` — backend implementation (models, services, routes)
- `backend/tests/*` — unit/integration/contract tests

Next steps / Infra

This PR intentionally defers infra-specific tasks to a separate SDD and feature(s). Suggested infra items (tracked separately):

- Deploy to Telegram Bot webhook (production integration)
- Add email notifications (optional)
- Rate limiting and scaling considerations

See `specs/features/002-telegram-webhook-infra/TELEGRAM-WEBHOOK-INFRA-SDD.md` (draft) for the infra plan.

How to test locally

Run tests and validators locally:

```bash
uv run pytest backend/tests/ -v
npx @redocly/openapi-cli validate specs/001-seamless-telegram-auth/contracts/openapi.yaml
npx -y @stoplight/spectral lint --ruleset spectral:oas specs/001-seamless-telegram-auth/contracts/openapi.yaml
```

Suggested PR description checklist

- [ ] CI: unit, integration, contract tests (pytest)
- [ ] CI: OpenAPI validation (openapi-cli)
- [ ] Reviewer: verify API contract and tests
- [ ] Merge: rebase onto `main` and merge when green

Notes

If you'd like, I can push the branch tip (rebased) and prepare a `gh pr create` command text for you to run, and/or create issues for the infra tasks.
