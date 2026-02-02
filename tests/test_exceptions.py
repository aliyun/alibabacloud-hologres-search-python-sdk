"""
Tests for exception classes in Holo Search SDK.

This module contains tests for custom exception handling and error reporting.
"""

import pytest

from holo_search_sdk.exceptions import (
    ConnectionError,
    HoloSearchError,
    QueryError,
    SqlError,
    TableError,
)
from holo_search_sdk.types import ConnectionConfig


class TestHoloSearchError:
    """Test cases for the base HoloSearchError class."""

    def test_basic_error_creation(self):
        """Test creating a basic HoloSearchError."""
        message = "Something went wrong"
        error = HoloSearchError(message)

        assert str(error) == message
        assert error.message == message
        assert error.error_code is None
        assert error.details == {}

    def test_error_with_code(self):
        """Test creating HoloSearchError with error code."""
        message = "Database connection failed"
        error_code = "DB_CONN_001"
        error = HoloSearchError(message, error_code=error_code)

        assert str(error) == f"[{error_code}] {message}"
        assert error.message == message
        assert error.error_code == error_code
        assert error.details == {}

    def test_error_with_details(self):
        """Test creating HoloSearchError with details."""
        message = "Query execution failed"
        details = {"query": "SELECT * FROM users", "timeout": 30}
        error = HoloSearchError(message, details=details)

        assert str(error) == message
        assert error.message == message
        assert error.error_code is None
        assert error.details == details

    def test_error_with_all_parameters(self):
        """Test creating HoloSearchError with all parameters."""
        message = "Complex error occurred"
        error_code = "COMPLEX_001"
        details = {"component": "client", "operation": "connect"}
        error = HoloSearchError(message, error_code=error_code, details=details)

        assert str(error) == f"[{error_code}] {message}"
        assert error.message == message
        assert error.error_code == error_code
        assert error.details == details

    def test_error_inheritance(self):
        """Test that HoloSearchError inherits from Exception."""
        error = HoloSearchError("Test error")
        assert isinstance(error, Exception)
        assert isinstance(error, HoloSearchError)

    def test_error_details_default_empty_dict(self):
        """Test that details defaults to empty dict when None is passed."""
        error = HoloSearchError("Test", details=None)
        assert error.details == {}


class TestConnectionError:
    """Test cases for ConnectionError class."""

    def test_connection_error_creation(self):
        """Test creating a ConnectionError."""
        message = "Failed to connect to database"
        error = ConnectionError(message)

        assert str(error) == "[CONNECTION_ERROR] " + message
        assert error.message == message
        assert error.error_code == "CONNECTION_ERROR"
        assert error.config is None

    def test_connection_error_with_config(self):
        """Test creating ConnectionError with configuration."""
        message = "Connection timeout"
        config = ConnectionConfig(
            host="localhost",
            port=5432,
            database="test_db",
            access_key_id="test_key",
            access_key_secret="test_secret",
        )
        error = ConnectionError(message, config=config)

        assert str(error) == "[CONNECTION_ERROR] " + message
        assert error.message == message
        assert error.error_code == "CONNECTION_ERROR"
        assert error.config == config

    def test_connection_error_inheritance(self):
        """Test ConnectionError inheritance."""
        error = ConnectionError("Test error")
        assert isinstance(error, HoloSearchError)
        assert isinstance(error, ConnectionError)


class TestQueryError:
    """Test cases for QueryError class."""

    def test_query_error_creation(self):
        """Test creating a QueryError."""
        message = "Invalid query syntax"
        error = QueryError(message)

        assert str(error) == "[QUERY_ERROR] " + message
        assert error.message == message
        assert error.error_code == "QUERY_ERROR"
        assert error.query is None

    def test_query_error_with_query(self):
        """Test creating QueryError with query."""
        message = "Query execution failed"
        query = "SELECT * FROM non_existent_table"
        error = QueryError(message, query=query)

        assert str(error) == "[QUERY_ERROR] " + message
        assert error.message == message
        assert error.error_code == "QUERY_ERROR"
        assert error.query == query

    def test_query_error_inheritance(self):
        """Test QueryError inheritance."""
        error = QueryError("Test error")
        assert isinstance(error, HoloSearchError)
        assert isinstance(error, QueryError)


class TestSqlError:
    """Test cases for SqlError class."""

    def test_sql_error_creation(self):
        """Test creating a SqlError."""
        message = "SQL generation failed"
        error = SqlError(message)

        assert str(error) == "[SQL_ERROR] " + message
        assert error.message == message
        assert error.error_code == "SQL_ERROR"
        assert error.sql is None

    def test_sql_error_with_sql(self):
        """Test creating SqlError with SQL statement."""
        message = "Invalid SQL syntax"
        sql = "SELCT * FROM users"  # Intentional typo
        error = SqlError(message, sql=sql)

        assert str(error) == "[SQL_ERROR] " + message
        assert error.message == message
        assert error.error_code == "SQL_ERROR"
        assert error.sql == sql

    def test_sql_error_inheritance(self):
        """Test SqlError inheritance."""
        error = SqlError("Test error")
        assert isinstance(error, HoloSearchError)
        assert isinstance(error, SqlError)


class TestTableError:
    """Test cases for TableError class."""

    def test_table_error_creation(self):
        """Test creating a TableError."""
        message = "Table operation failed"
        error = TableError(message)

        assert str(error) == "[TABLE_ERROR] " + message
        assert error.message == message
        assert error.error_code == "TABLE_ERROR"
        assert error.table_name is None

    def test_table_error_with_table_name(self):
        """Test creating TableError with table name."""
        message = "Table not found"
        table_name = "users"
        error = TableError(message, table_name=table_name)

        assert str(error) == "[TABLE_ERROR] " + message
        assert error.message == message
        assert error.error_code == "TABLE_ERROR"
        assert error.table_name == table_name

    def test_table_error_inheritance(self):
        """Test TableError inheritance."""
        error = TableError("Test error")
        assert isinstance(error, HoloSearchError)
        assert isinstance(error, TableError)


class TestExceptionIntegration:
    """Integration tests for exception handling."""

    def test_exception_chaining(self):
        """Test exception chaining with custom exceptions."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise ConnectionError("Connection failed") from e
        except ConnectionError as conn_error:
            assert str(conn_error) == "[CONNECTION_ERROR] Connection failed"
            assert isinstance(conn_error.__cause__, ValueError)
            assert str(conn_error.__cause__) == "Original error"

    def test_exception_with_complex_details(self):
        """Test exception with complex details dictionary."""
        details = {
            "host": "localhost",
            "port": 5432,
            "timeout": 30,
            "retry_count": 3,
            "last_error": "Connection refused",
            "metadata": {"client_version": "1.0.0", "protocol": "postgresql"},
        }

        error = HoloSearchError("Complex error", error_code="COMPLEX", details=details)

        assert error.details == details
        assert error.details["host"] == "localhost"
        assert error.details["metadata"]["client_version"] == "1.0.0"

    def test_all_exceptions_have_correct_error_codes(self):
        """Test that all exception types have correct error codes."""
        connection_error = ConnectionError("test")
        query_error = QueryError("test")
        sql_error = SqlError("test")
        table_error = TableError("test")

        assert connection_error.error_code == "CONNECTION_ERROR"
        assert query_error.error_code == "QUERY_ERROR"
        assert sql_error.error_code == "SQL_ERROR"
        assert table_error.error_code == "TABLE_ERROR"

    def test_exception_str_formatting_consistency(self):
        """Test consistent string formatting across all exception types."""
        exceptions = [
            ConnectionError("Connection failed"),
            QueryError("Query failed"),
            SqlError("SQL failed"),
            TableError("Table failed"),
        ]

        for exc in exceptions:
            str_repr = str(exc)
            assert str_repr.startswith("[")
            assert "] " in str_repr
            assert exc.error_code in str_repr
            assert exc.message in str_repr

    def test_raising_and_catching_exceptions(self):
        """Test raising and catching different exception types."""
        # Test ConnectionError
        with pytest.raises(ConnectionError) as exc_info:
            raise ConnectionError("Connection test")
        assert "Connection test" in str(exc_info.value)

        # Test QueryError
        with pytest.raises(QueryError) as exc_info:
            raise QueryError("Query test")
        assert "Query test" in str(exc_info.value)

        # Test SqlError
        with pytest.raises(SqlError) as exc_info:
            raise SqlError("SQL test")
        assert "SQL test" in str(exc_info.value)

        # Test TableError
        with pytest.raises(TableError) as exc_info:
            raise TableError("Table test")
        assert "Table test" in str(exc_info.value)

    def test_catching_base_exception(self):
        """Test catching specific exceptions as base HoloSearchError."""
        exceptions_to_test = [
            ConnectionError("Connection error"),
            QueryError("Query error"),
            SqlError("SQL error"),
            TableError("Table error"),
        ]

        for exc in exceptions_to_test:
            with pytest.raises(HoloSearchError):
                raise exc
