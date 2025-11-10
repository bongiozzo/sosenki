"""Custom exception classes for database seeding.

Provides domain-specific exceptions for clear error handling and reporting.
"""


class SeedError(Exception):
    """Base exception for seeding errors."""

    pass


class ConfigError(SeedError):
    """Configuration loading or validation error."""

    pass


class CredentialsError(ConfigError):
    """Credentials file not found or invalid."""

    pass


class APIError(SeedError):
    """Google Sheets API error (authentication, network, etc.)."""

    pass


class DataValidationError(SeedError):
    """Data validation error (empty name, invalid format, etc.)."""

    pass


class DatabaseError(SeedError):
    """Database operation error (connection, constraint violation, etc.)."""

    pass


class TransactionError(DatabaseError):
    """Database transaction error (rollback needed)."""

    pass
