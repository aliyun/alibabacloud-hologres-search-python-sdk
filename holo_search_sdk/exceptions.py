"""
Exception classes for Holo Search SDK.

Defines custom exceptions used throughout the SDK.
"""

from typing import Any, Dict, Optional

from typing_extensions import override

from .types import ConnectionConfig


class HoloSearchError(Exception):
    """Base exception class for all Holo Search SDK errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            error_code: Optional error code
            details: Optional additional error details
        """
        super().__init__(message)
        self.message: str = message
        self.error_code: Optional[str] = error_code
        self.details: Optional[Dict[str, Any]] = details or {}

    @override
    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class ConnectionError(HoloSearchError):
    """Raised when there are issues with database connections."""

    def __init__(
        self, message: str, config: Optional[ConnectionConfig] = None, **kwargs
    ):
        super().__init__(message, error_code="CONNECTION_ERROR", **kwargs)
        self.config: Optional[ConnectionConfig] = config


class QueryError(HoloSearchError):
    """Raised when there are issues with query execution."""

    def __init__(self, message: str, query: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="QUERY_ERROR", **kwargs)
        self.query: Optional[str] = query


class SqlError(HoloSearchError):
    """Raised when there are issues when generate sql."""

    def __init__(self, message: str, sql: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="SQL_ERROR", **kwargs)
        self.sql: Optional[str] = sql


class TableError(HoloSearchError):
    """Raised when there are issues with table execution."""

    def __init__(self, message: str, table_name: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="TABLE_ERROR", **kwargs)
        self.table_name: Optional[str] = table_name
