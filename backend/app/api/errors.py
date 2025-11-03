"""API error handling and response helpers."""

from typing import Any, Dict

from fastapi import HTTPException, status


class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, code: str, http_status: int = 400):
        """Initialize error."""
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(message)


class DuplicateRequestError(AppError):
    """User has already submitted a request."""

    def __init__(self, message: str = "User has already submitted a request"):
        super().__init__(message, "duplicate_request", status.HTTP_400_BAD_REQUEST)


class UserAlreadyExistsError(AppError):
    """User with this telegram_id already exists."""

    def __init__(self, message: str = "User already exists"):
        super().__init__(message, "user_already_exists", status.HTTP_400_BAD_REQUEST)


class InvalidInitDataError(AppError):
    """Invalid or expired initData."""

    def __init__(self, message: str = "Invalid or expired initData"):
        super().__init__(message, "invalid_initdata", status.HTTP_401_UNAUTHORIZED)


class UnauthorizedError(AppError):
    """User is not authorized."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, "unauthorized", status.HTTP_403_FORBIDDEN)


def error_response(error: AppError) -> Dict[str, Any]:
    """Create a standardized error response."""
    return {
        "error": {
            "code": error.code,
            "message": error.message,
        }
    }


def raise_app_error(error: AppError) -> None:
    """Raise an HTTPException from an AppError."""
    raise HTTPException(
        status_code=error.http_status,
        detail=error_response(error),
    )
