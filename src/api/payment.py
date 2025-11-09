"""Payment API endpoints for managing financial transactions.

Endpoints:
- POST /periods - Create service period
- GET /periods - List periods
- GET /periods/{id} - Get period details
- POST /periods/{id}/close - Close period (calculate balances)
- PATCH /periods/{id} - Reopen period

- POST /periods/{id}/contributions - Record contribution
- GET /periods/{id}/contributions - List contributions

- POST /periods/{id}/expenses - Record expense
- GET /periods/{id}/expenses - List expenses

- GET /periods/{id}/balance-sheet - Generate balance sheet
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["payments"])


# TODO: Implement endpoints
