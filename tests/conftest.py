"""
Test configuration and fixtures for Holo Search SDK tests.

This module provides common test fixtures and configuration for pytest.
"""

from unittest.mock import Mock

import pytest

from holo_search_sdk.backend import HoloDB, HoloTable
from holo_search_sdk.client import Client
from holo_search_sdk.types import ConnectionConfig


@pytest.fixture
def sample_connection_config():
    """Provide a sample connection configuration for testing."""
    return ConnectionConfig(
        host="localhost",
        port=80,
        database="test_db",
        access_key_id="test_key_id",
        access_key_secret="test_key_secret",
        schema="public",
    )


@pytest.fixture
def mock_holo_db():
    """Provide a mock HoloDB instance for testing."""
    mock_db = Mock(spec=HoloDB)
    mock_db.connect = Mock()
    mock_db.disconnect = Mock()
    mock_db.execute = Mock()
    # mock_db.create_table = Mock()
    mock_db.open_table = Mock()
    mock_db.drop_table = Mock()
    mock_db.check_table_exist = Mock(return_value=True)
    return mock_db


@pytest.fixture
def mock_holo_table():
    """Provide a mock HoloTable instance for testing."""
    mock_table = Mock(spec=HoloTable)
    # Configure methods to return the mock_table itself (fluent interface)
    mock_table.insert_one = Mock(return_value=mock_table)
    mock_table.insert_multi = Mock(return_value=mock_table)
    mock_table.set_vector_index = Mock(return_value=mock_table)
    mock_table.set_vector_indexes = Mock(return_value=mock_table)
    mock_table.delete_vector_indexes = Mock(return_value=mock_table)
    return mock_table


@pytest.fixture
def client_with_mock_backend(sample_connection_config, mock_holo_db):
    """Provide a client instance with mocked backend for testing."""
    client = Client(
        host=sample_connection_config.host,
        port=sample_connection_config.port,
        database=sample_connection_config.database,
        access_key_id=sample_connection_config.access_key_id,
        access_key_secret=sample_connection_config.access_key_secret,
        schema=sample_connection_config.schema,
    )
    client._backend = mock_holo_db
    return client


@pytest.fixture
def sample_table_columns():
    """Provide sample table column definitions for testing."""
    return {
        "id": ("INTEGER", "PRIMARY KEY"),
        "content": "TEXT",
        "vector": "FLOAT8[]",
        "metadata": "JSONB",
        "created_at": "TIMESTAMP DEFAULT NOW()",
    }


@pytest.fixture
def sample_vector_data():
    """Provide sample vector data for testing."""
    return [
        [
            1,
            "Hello world",
            [0.1, 0.2, 0.3],
            {"category": "greeting"},
            "2023-01-01 00:00:00",
        ],
        [2, "Python SDK", [0.4, 0.5, 0.6], {"category": "tech"}, "2023-01-02 00:00:00"],
        [
            3,
            "Vector search",
            [0.7, 0.8, 0.9],
            {"category": "search"},
            "2023-01-03 00:00:00",
        ],
    ]


@pytest.fixture
def sample_vector_configs():
    """Provide sample vector index configurations for testing."""
    return {
        "vector": {
            "distance_method": "Cosine",
            "max_degree": 64,
            "ef_construction": 400,
            "use_reorder": False,
            "precise_quantization_type": "fp32",
            "precise_io_type": "block_memory_io",
        }
    }


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks before each test."""
    yield
    # This fixture runs after each test to ensure clean state
