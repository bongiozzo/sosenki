# 002-telegram-webhook-infra — SDD (draft)

## Goal

Design and implement production-grade Telegram Bot webhook infrastructure for the Seamless Telegram Auth feature. The SDD covers topology, security, delivery guarantees, monitoring, rollout and acceptance criteria.

## Non-goals

- Detailed CI/CD scripts for specific cloud providers (those will be in infra repos)
- Email notifications design (handled in a separate spec)

## Topology

- Incoming webhooks hit a public HTTPS endpoint on the backend service (Ingress / Load Balancer)
- TLS terminated at LB (managed certificate or Let's Encrypt)
- Traffic routed to backend `miniapp` service which validates `initData` and processes messages
- Asynchronous tasks (notifications, heavy processing) are handled by background workers (e.g., Celery / asyncio tasks) to avoid webhook timeouts

## Security

- Secrets (BOT_TOKEN) stored in secret manager (Vault / cloud secrets) and mounted as env vars; never checked into git
- Webhook endpoint protected with IP allowlist (optional) and request validation using Telegram's recommended verification
- RBAC: only specific service accounts may post admin actions to internal endpoints

## Delivery & Reliability

- Webhook handlers must respond within Telegram's timeout (short): process minimal work synchronously, enqueue async work for notifications
- Retries/backoff: implement idempotency for webhook deliveries (dedupe by update_id)
- Instrument retry metrics and alert on high failure rates

## Scaling & Rate Limiting

- Autoscale backend pods based on CPU/requests; use horizontal pod autoscaler
- Introduce rate limiting at edge (Ingress or API gateway) and application level for abusive request endpoints
- Use Redis for distributed counters if per-IP or per-telegram_id limiting is required

## Monitoring & Alerts

- SLIs: webhook success rate, processing latency, queue length for background jobs
- Alerts: webhook failure rate > 1% over 5m, queue backlog > threshold

## Rollout plan

1. Create staging deployment with webhook URL registered to a staging bot
2. Smoke tests: verify webhook receives updates and that notifications are queued and processed
3. Canary deploy to a small subset of traffic (if supported)
4. Full production rollout and monitoring

## Acceptance Criteria

- Webhook endpoint reachable via HTTPS and validated by Telegram
- No dropped updates during a 30-minute load test
- Background worker processes notifications within SLA (e.g., 30s)
- Secrets are stored in secret manager, not in repo

## Dependencies

- TLS certificate automation (Let's Encrypt / cloud provider)
- Secret manager
- Redis (for rate limiting / dedupe) — optional but recommended
- Background worker environment

## Estimated effort

- SDD completion & review: 1–2 days
- Staging infra setup & smoke tests: 1–2 days
- Production rollout: 1–3 days (depends on infra complexity)

## Next steps

- Create issues for: TLS, secrets, Redis, background worker, webhook registration and smoke tests
- Coordinate deployment window and monitoring ownership
