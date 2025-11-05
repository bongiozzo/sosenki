# Deployment Guide: Client Request Approval Workflow

**Feature**: Client Request Approval Workflow (001-request-approval)  
**Date**: 2025-11-04  
**Target Audience**: DevOps and deployment engineers

## Table of Contents

1. [Production Architecture](#production-architecture)
2. [Environment Setup](#environment-setup)
3. [Database Setup](#database-setup)
4. [Webhook Configuration](#webhook-configuration)
5. [Deployment Process](#deployment-process)
6. [Monitoring & Logging](#monitoring--logging)
7. [Troubleshooting](#troubleshooting)
8. [Rollback Procedures](#rollback-procedures)

---

## Production Architecture

### Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                    Telegram Bot Servers                          │
│                      (Cloud Hosted)                              │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS Webhook POST
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Your Production Server                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              FastAPI Application                         │  │
│  │  POST /webhook/telegram → processes Update → handlers   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│  ┌──────────────────────────┼──────────────────────────────┐   │
│  │                          ▼                              │   │
│  │  ┌──────────────────────────────────────────────────┐  │   │
│  │  │          Bot Handlers (Async)                    │  │   │
│  │  │  - handle_request_command (/request)            │  │   │
│  │  │  - handle_admin_approve (Approve text)          │  │   │
│  │  │  - handle_admin_reject (Reject text)            │  │   │
│  │  └────┬──────────────────────────────────┬──────────┘  │   │
│  │       │                                   │             │   │
│  │  ┌────▼──────────────────────────────────▼──────────┐  │   │
│  │  │             Services Layer                       │  │   │
│  │  │  - RequestService (CRUD)                        │  │   │
│  │  │  - AdminService (approve/reject)               │  │   │
│  │  │  - NotificationService (send messages)          │  │   │
│  │  └────┬──────────────────────────────────┬──────────┘  │   │
│  │       │                                   │             │   │
│  │  ┌────▼──────────────────────────────────▼──────────┐  │   │
│  │  │          SQLAlchemy ORM Layer                    │  │   │
│  │  │  - ClientRequest model                          │  │   │
│  │  │  - Administrator model                          │  │   │
│  │  └────┬──────────────────────────────────┬──────────┘  │   │
│  └───────┼──────────────────────────────────┼──────────────┘   │
│          │                                   │                 │
│  ┌───────▼──────────────────────────────────▼──────────────┐   │
│  │                                                          │   │
│  │  ┌────────────────────────┐  ┌────────────────────────┐ │   │
│  │  │   PostgreSQL (Prod)    │  │   Redis Cache (Opt)    │ │   │
│  │  │   or MySQL             │  │   for session state    │ │   │
│  │  └────────────────────────┘  └────────────────────────┘ │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

- **FastAPI Server**: Webhook endpoint receives Telegram updates (HTTP POST)
- **Bot Application**: python-telegram-bot app processes updates async
- **Service Layer**: Business logic for requests, approvals, notifications
- **Database**: Persistent storage for requests and admin config
- **Telegram Bot API**: External service for sending messages

---

## Environment Setup

### 1. Create Production Environment File

Create `.env.production` with production values:

```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=<production-bot-token>  # Different from dev token
ADMIN_TELEGRAM_ID=<production-admin-id>    # Production admin user ID

# Database Configuration (Production)
DATABASE_URL=postgresql://user:password@prod-db-host:5432/sosekni_prod
# OR for MySQL:
# DATABASE_URL=mysql+pymysql://user:password@prod-db-host:3306/sosekni_prod

# Webhook Configuration
WEBHOOK_URL=https://sosekni.example.com/webhook/telegram
# Must be HTTPS (Telegram requirement)

# Application Configuration
DEBUG=false  # Must be False in production
LOG_LEVEL=INFO  # INFO, WARNING, ERROR (DEBUG only for troubleshooting)
WORKERS=4  # Number of Uvicorn worker processes (2-4 x CPU cores)
```

### 2. Telegram Bot Setup

- Create separate bot in production via @BotFather
- Keep bot token secret (never commit to version control)
- Store in environment variables or secrets management system (AWS Secrets Manager, HashiCorp Vault, etc.)

### 3. Database Preparation

#### PostgreSQL (Recommended for Production)

```bash
# Create database and user
psql -U postgres -c "CREATE DATABASE sosekni_prod;"
psql -U postgres -c "CREATE USER sosekni_user WITH PASSWORD 'strong-password-here';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE sosekni_prod TO sosekni_user;"

# Verify connection
psql -h prod-db-host -U sosekni_user -d sosekni_prod -c "SELECT 1;"
```

#### MySQL (Alternative)

```bash
# Create database and user
mysql -u root -p -e "CREATE DATABASE sosekni_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p -e "CREATE USER 'sosekni_user'@'localhost' IDENTIFIED BY 'strong-password-here';"
mysql -u root -p -e "GRANT ALL PRIVILEGES ON sosekni_prod.* TO 'sosekni_user'@'localhost';"
```

### Server Requirements

**Minimum**:

- Python 3.11+
- 512 MB RAM
- 10 GB disk (for logs, database)
- Network access to Telegram API

**Recommended**:

- Python 3.12+
- 2 GB RAM (for multiple worker processes)
- 50 GB disk (room for growth)
- Dedicated database server
- Redis cache layer
- SSL/TLS certificate (Let's Encrypt free or paid CA)

---

## Database Setup

### 1. Initial Migration

```bash
# Run migrations on production database
export DATABASE_URL="postgresql://user:password@prod-db-host:5432/sosekni_prod"
uv run alembic upgrade head

# Verify tables created
uv run python -c "
from sqlalchemy import create_engine, inspect
import os
engine = create_engine(os.environ['DATABASE_URL'])
inspector = inspect(engine)
print('Tables:', inspector.get_table_names())
print('client_requests columns:', [c['name'] for c in inspector.get_columns('client_requests')])
print('administrators columns:', [c['name'] for c in inspector.get_columns('administrators')])
"
```

### 2. Initialize Admin User

```bash
# Add initial administrator to database
uv run python -c "
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
import os

from src.models import Base
from src.models.admin_config import Administrator

engine = create_engine(os.environ['DATABASE_URL'])
Session = sessionmaker(bind=engine)
session = Session()

# Add production admin
admin = Administrator(
    telegram_id=os.environ['ADMIN_TELEGRAM_ID'],
    name='SOSenki Admin',
    active=True,
    created_at=datetime.now(timezone.utc)
)
session.add(admin)
session.commit()
print(f'Admin {admin.telegram_id} created successfully')
"
```

### 3. Backup Strategy

```bash
# Daily backup of production database
# Add to cron job:
0 2 * * * pg_dump -U sosekni_user sosekni_prod | gzip > /backups/sosekni_prod_\$(date +\%Y\%m\%d).sql.gz

# Keep 30 days of backups
find /backups -name "sosekni_prod_*.sql.gz" -mtime +30 -delete
```

---

## Webhook Configuration

### 1. SSL/TLS Certificate Setup

Telegram webhooks require HTTPS. Obtain a certificate:

```bash
# Using Let's Encrypt (Free)
certbot certonly --standalone -d sosekni.example.com

# Certificate location (after successful renewal):
# /etc/letsencrypt/live/sosekni.example.com/fullchain.pem
# /etc/letsencrypt/live/sosekni.example.com/privkey.pem

# Auto-renewal
certbot renew --quiet  # Add to cron daily
```

### 2. Register Webhook with Telegram

```bash
# After server is running, register webhook
curl -X POST \
  https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook \
  -d "url=https://sosekni.example.com/webhook/telegram" \
  -d "drop_pending_updates=false"

# Verify webhook is set
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo

# Example response:
# {
#   "ok": true,
#   "result": {
#     "url": "https://sosekni.example.com/webhook/telegram",
#     "has_custom_certificate": false,
#     "pending_update_count": 0
#   }
# }
```

### 3. Nginx Reverse Proxy Configuration

```nginx
# /etc/nginx/sites-available/sosekni
upstream sosekni_app {
    # Uvicorn workers (change port if different)
    server localhost:8000;
    server localhost:8001;
    server localhost:8002;
    server localhost:8003;
}

server {
    listen 443 ssl http2;
    server_name sosekni.example.com;

    ssl_certificate /etc/letsencrypt/live/sosekni.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sosekni.example.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://sosekni_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_request_buffering off;  # For real-time updates
    }

    # Telegram IP whitelist (optional but recommended)
    location /webhook/telegram {
        # Telegram uses these IP ranges: Check latest at https://core.telegram.org/bots/webhooks
        allow 91.108.4.0/22;
        allow 91.108.8.0/22;
        allow 91.108.12.0/22;
        # ... add all Telegram IPs
        deny all;

        proxy_pass http://sosekni_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# HTTP redirect to HTTPS
server {
    listen 80;
    server_name sosekni.example.com;
    return 301 https://$server_name$request_uri;
}
```

---

## Deployment Process

### 1. Pre-Deployment Checklist

- [ ] All tests passing locally: `uv run pytest -v`
- [ ] Code linted: `uv run ruff check src/ tests/`
- [ ] Environment variables configured in .env.production
- [ ] Database backups running
- [ ] SSL certificate valid
- [ ] Nginx configuration tested: `nginx -t`

### 2. Deploy to Production

```bash
#!/bin/bash
# deploy.sh - Production deployment script

set -e

# 1. Pull latest code
cd /opt/sosekni
git pull origin main

# 2. Install dependencies
uv sync --no-dev  # Don't install test dependencies in production

# 3. Run database migrations
export DATABASE_URL=$(cat /opt/sosekni/.env.production | grep DATABASE_URL | cut -d= -f2)
uv run alembic upgrade head

# 4. Run tests to verify
TELEGRAM_BOT_TOKEN="test-token" ADMIN_TELEGRAM_ID=0 uv run pytest tests/ -v

# 5. Restart application servers
sudo systemctl restart sosekni-app

# 6. Verify webhook
curl https://api.telegram.org/bot$(cat /opt/sosekni/.env.production | grep TELEGRAM_BOT_TOKEN | cut -d= -f2)/getWebhookInfo

echo "✅ Deployment completed successfully"
```

### 3. Systemd Service File

Create `/etc/systemd/system/sosekni-app.service`:

```ini
[Unit]
Description=SOSenki Bot Application
After=network.target postgresql.service

[Service]
Type=notify
User=sosekni
WorkingDirectory=/opt/sosekni

# Load environment variables
EnvironmentFile=/opt/sosekni/.env.production

# Start command
ExecStart=/opt/sosekni/.venv/bin/uv run uvicorn src.api.webhook:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 4 \
    --access-log \
    --log-level info

# Restart on failure
Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=yes

[Install]
WantedBy=multi-user.target
```

### 4. Start the Service

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable sosekni-app
sudo systemctl start sosekni-app

# Check status
sudo systemctl status sosekni-app

# View logs
journalctl -u sosekni-app -f  # Follow logs in real-time
```

---

## Monitoring & Logging

### 1. Application Logging

Logs should be written to:

```bash
/var/log/sosekni/app.log      # Application logs
/var/log/sosekni/access.log   # Uvicorn access logs
/var/log/sosekni/error.log    # Error logs
```

### 2. Monitor Key Metrics

```bash
# Requests per minute to webhook
grep "POST /webhook/telegram" /var/log/sosekni/access.log | wc -l

# Error rate
grep "ERROR" /var/log/sosekni/app.log | wc -l

# Database connection status
uv run python -c "
from src.services import SessionLocal
db = SessionLocal()
result = db.execute('SELECT 1').fetchone()
print('✅ Database OK' if result else '❌ Database ERROR')
"

# Telegram webhook status
curl -s https://api.telegram.org/bot<TOKEN>/getWebhookInfo | jq '.result'
```

### 3. Health Check Endpoint (Optional)

Add to `src/api/webhook.py`:

```python
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return {"status": "healthy", "database": "ok"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}, 503
```

Then monitor:

```bash
# Periodic health checks
*/5 * * * * curl -f https://sosekni.example.com/health || systemctl restart sosekni-app
```

---

## Troubleshooting

### Problem: Webhook Not Receiving Updates

```bash
# Check webhook status
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo

# Check application logs
journalctl -u sosekni-app -n 50

# Re-register webhook
curl -X POST https://api.telegram.org/bot<TOKEN>/setWebhook \
  -d "url=https://sosekni.example.com/webhook/telegram"
```

### Problem: Database Connection Errors

```bash
# Test connection
uv run python -c "
import os
from sqlalchemy import create_engine
engine = create_engine(os.environ['DATABASE_URL'])
engine.execute('SELECT 1')
print('✅ Connected')
"

# Check credentials
grep DATABASE_URL /opt/sosekni/.env.production
```

### Problem: Admin Not Receiving Messages

```bash
# Verify admin ID is correct
grep ADMIN_TELEGRAM_ID /opt/sosekki/.env.production

# Send test message from bot
curl -X POST https://api.telegram.org/bot<TOKEN>/sendMessage \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\": <ADMIN_ID>, \"text\": \"Test message\"}"
```

---

## Rollback Procedures

### Quick Rollback

```bash
# If latest code breaks everything:
git checkout HEAD~1
sudo systemctl restart sosekni-app
```

### Database Rollback

```bash
# Revert to previous migration
uv run alembic downgrade -1

# Or rollback to specific revision
uv run alembic downgrade <revision-id>
```

### From Backup

```bash
# Stop application
sudo systemctl stop sosekni-app

# Restore database from backup
psql -U sosekni_user sosekni_prod < /backups/sosekni_prod_20251104.sql.gz

# Restart
sudo systemctl start sosekni-app
```

---

## References

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [python-telegram-bot Documentation](https://python-telegram-bot.readthedocs.io/)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [SQLAlchemy PostgreSQL](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html)
- [Uvicorn Configuration](https://www.uvicorn.org/settings/)
