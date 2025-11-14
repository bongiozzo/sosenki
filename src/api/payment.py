"""Payment management API endpoints - TEMPORARILY DISABLED.

Handles financial operations:
- Service period management (OPEN/CLOSED)
- Contribution recording and tracking
- Expense tracking with payer attribution
- Balance calculations and reporting

STATUS: Payment API implementation disabled for now - will implement later
"""

from fastapi import APIRouter

# All payment endpoints are temporarily commented out
# Export empty router to prevent import errors
router = APIRouter(prefix="/api/payments", tags=["payments"])
