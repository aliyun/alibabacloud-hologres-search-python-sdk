"""
Holo Search SDK - A Python SDK for database search operations.

This SDK provides a unified interface for vector search and full-text search.
"""

from importlib.metadata import version

from .backend.filter import AndFilter, Filter, NotFilter, OrFilter, TextSearchFilter
from .client import Client, connect
from .exceptions import (
    ConnectionError,
    HoloSearchError,
    QueryError,
    SqlError,
    TableError,
)
from .types import ConnectionConfig

__version__ = version("holo-search-sdk")
__author__ = "Tiancheng YANG"
__email__ = "yangtiancheng.ytc@alibaba-inc.com"

__all__ = [
    # Core functions
    "connect",
    # Main classes
    "Client",
    # Types
    "ConnectionConfig",
    # Filters
    "Filter",
    "AndFilter",
    "OrFilter",
    "NotFilter",
    "TextSearchFilter",
    # Exceptions
    "HoloSearchError",
    "ConnectionError",
    "QueryError",
    "SqlError",
    "TableError",
]
