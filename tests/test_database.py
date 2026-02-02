"""
Tests for HoloDB class in Holo Search SDK.

This module contains comprehensive tests for the HoloDB database class.
"""

from unittest.mock import Mock, patch

import pytest

from holo_search_sdk.backend import HoloDB, HoloTable
from holo_search_sdk.backend.connection import HoloConnect
from holo_search_sdk.backend.query import QueryBuilder
from holo_search_sdk.exceptions import ConnectionError, QueryError, TableError


class TestHoloDB:
    """Test cases for the HoloDB class."""

    def test_holo_db_initialization(self, sample_connection_config):
        """Test HoloDB initialization."""
        db = HoloDB(sample_connection_config)

        assert db._config == sample_connection_config
        assert db._connection is None
        assert db._connected is False

    @patch("holo_search_sdk.backend.database.HoloConnect")
    def test_connect_success(self, mock_holo_connect_class, sample_connection_config):
        """Test successful database connection."""
        mock_connection = Mock(spec=HoloConnect)
        mock_holo_connect_instance = Mock()
        mock_holo_connect_instance.connect.return_value = mock_connection
        mock_holo_connect_class.return_value = mock_holo_connect_instance

        db = HoloDB(sample_connection_config)
        db.connect()

        assert db._connection is mock_connection
        assert db._connected is True
        mock_holo_connect_class.assert_called_once_with(sample_connection_config)
        mock_holo_connect_instance.connect.assert_called_once()

    def test_disconnect(self, sample_connection_config):
        """Test database disconnection."""
        mock_connection = Mock(spec=HoloConnect)
        db = HoloDB(sample_connection_config)
        db._connection = mock_connection
        db._connected = True

        db.disconnect()

        assert db._connection is None
        assert db._connected is False
        mock_connection.close.assert_called_once()

    def test_execute_without_connection(self, sample_connection_config):
        """Test execute method without connection raises error."""
        db = HoloDB(sample_connection_config)

        with pytest.raises(ConnectionError) as exc_info:
            db.execute("SELECT 1")

        assert "Database is not connected" in str(exc_info.value)

    def test_execute_with_fetch_result(self, sample_connection_config):
        """Test execute method with fetch_result=True."""
        mock_connection = Mock(spec=HoloConnect)
        mock_connection.fetchall.return_value = [{"id": 1, "name": "test"}]

        db = HoloDB(sample_connection_config)
        db._connection = mock_connection
        db._connected = True

        result = db.execute("SELECT * FROM test", fetch_result=True)

        assert result == [{"id": 1, "name": "test"}]
        mock_connection.fetchall.assert_called_once_with("SELECT * FROM test")

    def test_execute_without_fetch_result(self, sample_connection_config):
        """Test execute method with fetch_result=False."""
        mock_connection = Mock(spec=HoloConnect)
        mock_connection.execute.return_value = None

        db = HoloDB(sample_connection_config)
        db._connection = mock_connection
        db._connected = True

        _ = db.execute("INSERT INTO test VALUES (1, 'test')", fetch_result=False)

        mock_connection.execute.assert_called_once_with(
            "INSERT INTO test VALUES (1, 'test')", use_transaction=None
        )

    def test_check_table_exist_true(self, sample_connection_config):
        """Test check_table_exist returns True when table exists."""
        mock_connection = Mock(spec=HoloConnect)
        mock_connection.fetchone.return_value = (True,)

        db = HoloDB(sample_connection_config)
        db._connection = mock_connection
        db._connected = True

        result = db.check_table_exist("existing_table")

        assert result is True
        mock_connection.fetchone.assert_called_once()

    def test_check_table_exist_false(self, sample_connection_config):
        """Test check_table_exist returns False when table doesn't exist."""
        mock_connection = Mock(spec=HoloConnect)
        mock_connection.fetchone.return_value = (False,)

        db = HoloDB(sample_connection_config)
        db._connection = mock_connection
        db._connected = True

        result = db.check_table_exist("non_existing_table")

        assert result is False

    def test_check_table_exist_query_error(self, sample_connection_config):
        """Test check_table_exist raises QueryError when fetchone returns None."""
        mock_connection = Mock(spec=HoloConnect)
        mock_connection.fetchone.return_value = None

        db = HoloDB(sample_connection_config)
        db._connection = mock_connection
        db._connected = True

        with pytest.raises(QueryError) as exc_info:
            db.check_table_exist("test_table")

        assert "Error executing SQL query" in str(exc_info.value)

    @patch("holo_search_sdk.backend.database.HoloTable")
    def test_open_table_success(self, mock_holo_table_class, sample_connection_config):
        """Test successful table opening."""
        mock_connection = Mock(spec=HoloConnect)
        mock_table = Mock(spec=HoloTable)
        mock_holo_table_class.return_value = mock_table

        db = HoloDB(sample_connection_config)
        db._connection = mock_connection
        db._connected = True
        db.check_table_exist = Mock(return_value=True)

        result = db.open_table("existing_table")

        assert result is mock_table
        db.check_table_exist.assert_called_once_with("existing_table")
        mock_holo_table_class.assert_called_once_with(
            mock_connection, "existing_table", None
        )

    def test_open_table_not_exist(self, sample_connection_config):
        """Test opening non-existing table raises TableError."""
        mock_connection = Mock(spec=HoloConnect)
        db = HoloDB(sample_connection_config)
        db._connection = mock_connection
        db._connected = True
        db.check_table_exist = Mock(return_value=False)

        with pytest.raises(TableError) as exc_info:
            db.open_table("non_existing_table")

        assert "does not exist" in str(exc_info.value)

    def test_drop_table(self, sample_connection_config):
        """Test table dropping."""
        mock_connection = Mock(spec=HoloConnect)
        db = HoloDB(sample_connection_config)
        db._connection = mock_connection
        db._connected = True

        db.drop_table("test_table")

        # Verify that execute was called with a Composed object
        mock_connection.execute.assert_called_once()
        call_args = mock_connection.execute.call_args[0]
        sql_str = call_args[0].as_string()
        assert sql_str == 'DROP TABLE IF EXISTS "test_table";'

    def test_set_guc_session_level(self, sample_connection_config):
        """Test set_guc at session level."""
        mock_connection = Mock(spec=HoloConnect)
        db = HoloDB(sample_connection_config)
        db._connection = mock_connection
        db._connected = True

        db.set_guc("work_mem", "256MB", db_level=False)

        mock_connection.execute.assert_called_once()
        call_args = mock_connection.execute.call_args[0]
        sql_str = call_args[0].as_string()
        assert "SET work_mem = '256MB';" in sql_str

    def test_set_guc_database_level(self, sample_connection_config):
        """Test set_guc at database level."""
        mock_connection = Mock(spec=HoloConnect)
        db = HoloDB(sample_connection_config)
        db._connection = mock_connection
        db._connected = True
        db._name = "test_db"

        db.set_guc("work_mem", "256MB", db_level=True)

        mock_connection.execute.assert_called_once()
        call_args = mock_connection.execute.call_args[0]
        sql_str = call_args[0].as_string()
        assert "ALTER database" in sql_str
        assert "work_mem = '256MB'" in sql_str

    def test_set_guc_without_connection(self, sample_connection_config):
        """Test set_guc without connection raises error."""
        db = HoloDB(sample_connection_config)

        with pytest.raises(ConnectionError) as exc_info:
            db.set_guc("work_mem", "256MB")

        assert "Database not connected" in str(exc_info.value)

    def test_set_guc_on_session_level(self, sample_connection_config):
        """Test set_guc_on at session level."""
        mock_connection = Mock(spec=HoloConnect)
        db = HoloDB(sample_connection_config)
        db._connection = mock_connection
        db._connected = True

        db.set_guc_on("enable_seqscan", db_level=False)

        mock_connection.execute.assert_called_once()
        call_args = mock_connection.execute.call_args[0]
        sql_str = call_args[0].as_string()
        assert "SET enable_seqscan = on;" in sql_str

    def test_set_guc_on_database_level(self, sample_connection_config):
        """Test set_guc_on at database level."""
        mock_connection = Mock(spec=HoloConnect)
        db = HoloDB(sample_connection_config)
        db._connection = mock_connection
        db._connected = True
        db._name = "test_db"

        db.set_guc_on("enable_seqscan", db_level=True)

        mock_connection.execute.assert_called_once()
        call_args = mock_connection.execute.call_args[0]
        sql_str = call_args[0].as_string()
        assert "ALTER database" in sql_str
        assert "enable_seqscan = on;" in sql_str

    def test_set_guc_on_without_connection(self, sample_connection_config):
        """Test set_guc_on without connection raises error."""
        db = HoloDB(sample_connection_config)

        with pytest.raises(ConnectionError) as exc_info:
            db.set_guc_on("enable_seqscan")

        assert "Database not connected" in str(exc_info.value)

    def test_set_guc_off_session_level(self, sample_connection_config):
        """Test set_guc_off at session level."""
        mock_connection = Mock(spec=HoloConnect)
        db = HoloDB(sample_connection_config)
        db._connection = mock_connection
        db._connected = True

        db.set_guc_off("enable_seqscan", db_level=False)

        mock_connection.execute.assert_called_once()
        call_args = mock_connection.execute.call_args[0]
        sql_str = call_args[0].as_string()
        assert "SET enable_seqscan = off;" in sql_str

    def test_set_guc_off_database_level(self, sample_connection_config):
        """Test set_guc_off at database level."""
        mock_connection = Mock(spec=HoloConnect)
        db = HoloDB(sample_connection_config)
        db._connection = mock_connection
        db._connected = True
        db._name = "test_db"

        db.set_guc_off("enable_seqscan", db_level=True)

        mock_connection.execute.assert_called_once()
        call_args = mock_connection.execute.call_args[0]
        sql_str = call_args[0].as_string()
        assert "ALTER database" in sql_str
        assert "enable_seqscan = off;" in sql_str

    def test_set_guc_off_without_connection(self, sample_connection_config):
        """Test set_guc_off without connection raises error."""
        db = HoloDB(sample_connection_config)

        with pytest.raises(ConnectionError) as exc_info:
            db.set_guc_off("enable_seqscan")

        assert "Database not connected" in str(exc_info.value)

    def test_show_guc_success(self, sample_connection_config):
        """Test show_guc returns GUC value."""
        mock_connection = Mock(spec=HoloConnect)
        mock_connection.fetchone.return_value = ("256MB",)

        db = HoloDB(sample_connection_config)
        db._connection = mock_connection
        db._connected = True

        result = db.show_guc("work_mem")

        assert result == "256MB"
        mock_connection.fetchone.assert_called_once()

    def test_show_guc_returns_none(self, sample_connection_config):
        """Test show_guc returns None when no result."""
        mock_connection = Mock(spec=HoloConnect)
        mock_connection.fetchone.return_value = None

        db = HoloDB(sample_connection_config)
        db._connection = mock_connection
        db._connected = True

        result = db.show_guc("work_mem")

        assert result is None

    def test_show_guc_without_connection(self, sample_connection_config):
        """Test show_guc without connection raises error."""
        db = HoloDB(sample_connection_config)

        with pytest.raises(ConnectionError) as exc_info:
            db.show_guc("work_mem")

        assert "Database not connected" in str(exc_info.value)

    @patch("holo_search_sdk.backend.database.QueryBuilder")
    def test_build_query_success(
        self, mock_query_builder_class, sample_connection_config
    ):
        """Test build_query returns QueryBuilder instance."""
        mock_connection = Mock(spec=HoloConnect)
        mock_query_builder = Mock(spec=QueryBuilder)
        mock_query_builder_class.return_value = mock_query_builder

        db = HoloDB(sample_connection_config)
        db._connection = mock_connection
        db._connected = True

        result = db.build_query("test_table", "t")

        assert result is mock_query_builder
        mock_query_builder_class.assert_called_once_with(
            mock_connection, "test_table", "t"
        )

    def test_build_query_without_connection(self, sample_connection_config):
        """Test build_query without connection raises error."""
        db = HoloDB(sample_connection_config)

        with pytest.raises(ConnectionError) as exc_info:
            db.build_query("test_table")

        assert "Database not connected" in str(exc_info.value)

    def test_check_table_exist_without_connection(self, sample_connection_config):
        """Test check_table_exist without connection raises error."""
        db = HoloDB(sample_connection_config)

        with pytest.raises(ConnectionError) as exc_info:
            db.check_table_exist("test_table")

        assert "Database not connected" in str(exc_info.value)

    def test_check_table_exist_unexpected_result(self, sample_connection_config):
        """Test check_table_exist with unexpected result raises QueryError."""
        mock_connection = Mock(spec=HoloConnect)
        mock_connection.fetchone.return_value = ("unexpected",)

        db = HoloDB(sample_connection_config)
        db._connection = mock_connection
        db._connected = True

        with pytest.raises(QueryError) as exc_info:
            db.check_table_exist("test_table")

        assert "Unexpected result" in str(exc_info.value)

    def test_open_table_without_connection(self, sample_connection_config):
        """Test open_table without connection raises error."""
        db = HoloDB(sample_connection_config)

        with pytest.raises(ConnectionError) as exc_info:
            db.open_table("test_table")

        assert "Database not connected" in str(exc_info.value)

    def test_drop_table_without_connection(self, sample_connection_config):
        """Test drop_table without connection raises error."""
        db = HoloDB(sample_connection_config)

        with pytest.raises(ConnectionError) as exc_info:
            db.drop_table("test_table")

        assert "Database not connected" in str(exc_info.value)
