"""
Backend module for Holo Search SDK.

Provides table backend implementations and factory functions.
"""

from .database import HoloDB
from .filter import AndFilter, Filter, NotFilter, OrFilter, TextSearchFilter
from .table import HoloTable

__all__ = [
    "HoloDB",
    "HoloTable",
    "AndFilter",
    "Filter",
    "NotFilter",
    "OrFilter",
    "TextSearchFilter",
]
