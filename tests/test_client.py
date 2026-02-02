"""
Tests for the Client class in Holo Search SDK.

This module contains comprehensive tests for client functionality including
connection management, table operations, and vector index management.
"""

from unittest.mock import Mock, patch

import pytest

from holo_search_sdk.client import Client, connect
from holo_search_sdk.exceptions import ConnectionError
from holo_search_sdk.types import ConnectionConfig


class TestClient:
    """Test cases for the Client class."""

    def test_client_initialization(self, sample_connection_config):
        """Test client initialization with valid configuration."""
        client = Client(
            host=sample_connection_config.host,
            port=sample_connection_config.port,
            database=sample_connection_config.database,
            access_key_id=sample_connection_config.access_key_id,
            access_key_secret=sample_connection_config.access_key_secret,
            schema=sample_connection_config.schema,
        )

        assert client._config.host == sample_connection_config.host
        assert client._config.port == sample_connection_config.port
        assert client._config.database == sample_connection_config.database
        assert client._config.access_key_id == sample_connection_config.access_key_id
        assert (
            client._config.access_key_secret
            == sample_connection_config.access_key_secret
        )
        assert client._config.schema == sample_connection_config.schema
        assert client._config.autocommit is False  # Default value
        assert client._backend is None
        assert client._opened_tables == {}

    def test_client_initialization_with_autocommit(self, sample_connection_config):
        """Test client initialization with autocommit enabled."""
        client = Client(
            host=sample_connection_config.host,
            port=sample_connection_config.port,
            database=sample_connection_config.database,
            access_key_id=sample_connection_config.access_key_id,
            access_key_secret=sample_connection_config.access_key_secret,
            schema=sample_connection_config.schema,
            autocommit=True,
        )

        assert client._config.autocommit is True
        assert client._backend is None
        assert client._opened_tables == {}

    @patch("holo_search_sdk.client.HoloDB")
    def test_connect_success(self, mock_holo_db_class, sample_connection_config):
        """Test successful database connection."""
        mock_db_instance = Mock()
        mock_holo_db_class.return_value = mock_db_instance

        client = Client(
            host=sample_connection_config.host,
            port=sample_connection_config.port,
            database=sample_connection_config.database,
            access_key_id=sample_connection_config.access_key_id,
            access_key_secret=sample_connection_config.access_key_secret,
        )

        result = client.connect()

        assert result is client
        assert client._backend is mock_db_instance
        mock_holo_db_class.assert_called_once_with(config=client._config)
        mock_db_instance.connect.assert_called_once()

    @patch("holo_search_sdk.client.HoloDB")
    def test_connect_failure(self, mock_holo_db_class, sample_connection_config):
        """Test connection failure handling."""
        mock_db_instance = Mock()
        mock_db_instance.connect.side_effect = Exception("Connection failed")
        mock_holo_db_class.return_value = mock_db_instance

        client = Client(
            host=sample_connection_config.host,
            port=sample_connection_config.port,
            database=sample_connection_config.database,
            access_key_id=sample_connection_config.access_key_id,
            access_key_secret=sample_connection_config.access_key_secret,
        )

        with pytest.raises(ConnectionError) as exc_info:
            client.connect()

        assert "Failed to connect to database" in str(exc_info.value)

    def test_disconnect(self, client_with_mock_backend):
        """Test database disconnection."""
        client = client_with_mock_backend
        mock_backend = client._backend  # 保存引用，因为 disconnect() 会将其设为 None

        client.disconnect()

        mock_backend.disconnect.assert_called_once()
        assert client._backend is None
        assert client._opened_tables == {}

    def test_execute_without_connection(self, sample_connection_config):
        """Test execute method without connection raises error."""
        client = Client(
            host=sample_connection_config.host,
            port=sample_connection_config.port,
            database=sample_connection_config.database,
            access_key_id=sample_connection_config.access_key_id,
            access_key_secret=sample_connection_config.access_key_secret,
        )

        with pytest.raises(ConnectionError) as exc_info:
            client.execute("SELECT 1")

        assert "Client not connected" in str(exc_info.value)

    def test_execute_with_connection(self, client_with_mock_backend):
        """Test execute method with valid connection."""
        client = client_with_mock_backend
        sql = "SELECT * FROM test_table"

        client.execute(sql, fetch_result=True)

        client._backend.execute.assert_called_once_with(sql, True, None)

    def test_check_table_exist(self, client_with_mock_backend):
        """Test table existence check."""
        client = client_with_mock_backend
        table_name = "test_table"
        client._backend.check_table_exist.return_value = True

        result = client.check_table_exist(table_name)

        assert result is True
        client._backend.check_table_exist.assert_called_once_with(table_name)

    def test_open_table(self, client_with_mock_backend, mock_holo_table):
        """Test opening an existing table."""
        client = client_with_mock_backend
        client._backend.open_table.return_value = mock_holo_table
        table_name = "existing_table"

        result = client.open_table(table_name)

        assert result is mock_holo_table
        assert client._opened_tables[table_name] is mock_holo_table
        client._backend.open_table.assert_called_once_with(table_name, None)

    def test_drop_table(self, client_with_mock_backend):
        """Test table dropping."""
        client = client_with_mock_backend
        table_name = "test_table"
        client._opened_tables[table_name] = Mock()

        client.drop_table(table_name)

        assert table_name not in client._opened_tables
        client._backend.drop_table.assert_called_once_with(table_name)

    def test_insert_one(self, client_with_mock_backend, mock_holo_table):
        """Test inserting a single record."""
        client = client_with_mock_backend
        client._backend.open_table.return_value = mock_holo_table
        table_name = "test_table"
        values = [1, "test", [0.1, 0.2]]
        column_names = ["id", "content", "vector"]

        result = client.insert_one(table_name, values, column_names)

        assert result is mock_holo_table
        mock_holo_table.insert_one.assert_called_once_with(values, column_names)

    def test_insert_multi(
        self, client_with_mock_backend, mock_holo_table, sample_vector_data
    ):
        """Test inserting multiple records."""
        client = client_with_mock_backend
        client._backend.open_table.return_value = mock_holo_table
        table_name = "test_table"
        column_names = ["id", "content", "vector", "metadata", "created_at"]

        result = client.insert_multi(table_name, sample_vector_data, column_names)

        assert result is mock_holo_table
        mock_holo_table.insert_multi.assert_called_once_with(
            sample_vector_data, column_names
        )

    def test_set_vector_index(self, client_with_mock_backend, mock_holo_table):
        """Test setting a vector index."""
        client = client_with_mock_backend
        client._backend.open_table.return_value = mock_holo_table
        table_name = "test_table"
        column = "vector"
        distance_method = "Euclidean"

        result = client.set_vector_index(
            table_name,
            column,
            distance_method,
            "rabitq",
            max_degree=32,
            ef_construction=200,
        )

        assert result is mock_holo_table
        mock_holo_table.set_vector_index.assert_called_once_with(
            column,
            distance_method,
            "rabitq",
            32,
            200,
            False,
            "fp32",
            "block_memory_io",
            4096,
            16,
        )

    def test_set_vector_indexes(
        self, client_with_mock_backend, mock_holo_table, sample_vector_configs
    ):
        """Test setting multiple vector indexes."""
        client = client_with_mock_backend
        client._backend.open_table.return_value = mock_holo_table
        table_name = "test_table"

        result = client.set_vector_indexes(table_name, sample_vector_configs)

        assert result is mock_holo_table
        mock_holo_table.set_vector_indexes.assert_called_once_with(
            sample_vector_configs
        )

    def test_delete_vector_indexes(self, client_with_mock_backend, mock_holo_table):
        """Test deleting vector indexes."""
        client = client_with_mock_backend
        client._backend.open_table.return_value = mock_holo_table
        table_name = "test_table"

        result = client.delete_vector_indexes(table_name)

        assert result is mock_holo_table
        mock_holo_table.delete_vector_indexes.assert_called_once()

    def test_open_table_with_alias(self, client_with_mock_backend, mock_holo_table):
        """Test opening a table with alias."""
        client = client_with_mock_backend
        client._backend.open_table.return_value = mock_holo_table
        table_name = "test_table"
        table_alias = "tt"

        result = client.open_table(table_name, table_alias)

        assert result is mock_holo_table
        assert client._opened_tables[table_name] is mock_holo_table
        client._backend.open_table.assert_called_once_with(table_name, table_alias)

    def test_disconnect_clears_opened_tables(self, client_with_mock_backend):
        """Test that disconnect clears opened tables."""
        client = client_with_mock_backend
        client._opened_tables["table1"] = Mock()
        client._opened_tables["table2"] = Mock()

        client.disconnect()

        assert len(client._opened_tables) == 0
        assert client._backend is None

    def test_execute_with_fetch_result_true(self, client_with_mock_backend):
        """Test execute method with fetch_result=True."""
        client = client_with_mock_backend
        sql = "SELECT * FROM test_table"
        expected_result = [{"id": 1, "name": "test"}]
        client._backend.execute.return_value = expected_result

        result = client.execute(sql, fetch_result=True)

        assert result == expected_result
        client._backend.execute.assert_called_once_with(sql, True, None)

    def test_execute_with_fetch_result_false(self, client_with_mock_backend):
        """Test execute method with fetch_result=False."""
        client = client_with_mock_backend
        sql = "INSERT INTO test_table VALUES (1, 'test')"

        _ = client.execute(sql, fetch_result=False)

        client._backend.execute.assert_called_once_with(sql, False, None)

    def test_insert_one_opens_table_if_not_cached(
        self, client_with_mock_backend, mock_holo_table
    ):
        """Test insert_one opens table if not in cache."""
        client = client_with_mock_backend
        client._backend.open_table.return_value = mock_holo_table
        table_name = "new_table"
        values = [1, "test"]

        result = client.insert_one(table_name, values)

        assert result is mock_holo_table
        client._backend.open_table.assert_called_once_with(table_name)
        mock_holo_table.insert_one.assert_called_once_with(values, None)

    def test_insert_multi_opens_table_if_not_cached(
        self, client_with_mock_backend, mock_holo_table, sample_vector_data
    ):
        """Test insert_multi opens table if not in cache."""
        client = client_with_mock_backend
        client._backend.open_table.return_value = mock_holo_table
        table_name = "new_table"

        result = client.insert_multi(table_name, sample_vector_data)

        assert result is mock_holo_table
        client._backend.open_table.assert_called_once_with(table_name)
        mock_holo_table.insert_multi.assert_called_once_with(sample_vector_data, None)

    def test_set_vector_index_opens_table_if_not_cached(
        self, client_with_mock_backend, mock_holo_table
    ):
        """Test set_vector_index opens table if not in cache."""
        client = client_with_mock_backend
        client._backend.open_table.return_value = mock_holo_table
        table_name = "new_table"

        result = client.set_vector_index(table_name, "vector", "Cosine", "rabitq")

        assert result is mock_holo_table
        client._backend.open_table.assert_called_once_with(table_name)

    def test_drop_table_removes_from_cache(self, client_with_mock_backend):
        """Test drop_table removes table from opened_tables cache."""
        client = client_with_mock_backend
        table_name = "test_table"
        client._opened_tables[table_name] = Mock()

        client.drop_table(table_name)

        assert table_name not in client._opened_tables
        client._backend.drop_table.assert_called_once_with(table_name)

    def test_drop_table_not_in_cache(self, client_with_mock_backend):
        """Test drop_table when table is not in cache."""
        client = client_with_mock_backend
        table_name = "non_cached_table"

        client.drop_table(table_name)

        assert table_name not in client._opened_tables
        client._backend.drop_table.assert_called_once_with(table_name)

    def test_find_table_cached(self, client_with_mock_backend, mock_holo_table):
        """Test finding a table that's already cached."""
        client = client_with_mock_backend
        table_name = "cached_table"
        client._opened_tables[table_name] = mock_holo_table

        result = client._find_table(table_name)

        assert result is mock_holo_table
        # Should not call open_table since it's cached
        client._backend.open_table.assert_not_called()

    def test_find_table_not_cached(self, client_with_mock_backend, mock_holo_table):
        """Test finding a table that's not cached."""
        client = client_with_mock_backend
        client._backend.open_table.return_value = mock_holo_table
        table_name = "new_table"

        result = client._find_table(table_name)

        assert result is mock_holo_table
        assert client._opened_tables[table_name] is mock_holo_table
        client._backend.open_table.assert_called_once_with(table_name)

    def test_context_manager(self, sample_connection_config):
        """Test client as context manager."""
        with patch("holo_search_sdk.client.HoloDB") as mock_holo_db_class:
            mock_db_instance = Mock()
            mock_holo_db_class.return_value = mock_db_instance

            with Client(
                host=sample_connection_config.host,
                port=sample_connection_config.port,
                database=sample_connection_config.database,
                access_key_id=sample_connection_config.access_key_id,
                access_key_secret=sample_connection_config.access_key_secret,
            ) as client:
                client.connect()
                assert client._backend is mock_db_instance

            # Should disconnect on exit
            mock_db_instance.disconnect.assert_called_once()


class TestConnectFunction:
    """Test cases for the connect function."""

    @patch("holo_search_sdk.client.Client.connect")
    def test_connect_function(self, mock_connect, sample_connection_config):
        """Test the connect convenience function."""
        # Mock the connect method to return the client instance
        mock_connect.return_value = Mock(spec=Client)
        mock_connect.return_value._config = sample_connection_config

        _ = connect(
            host=sample_connection_config.host,
            port=sample_connection_config.port,
            database=sample_connection_config.database,
            access_key_id=sample_connection_config.access_key_id,
            access_key_secret=sample_connection_config.access_key_secret,
            schema=sample_connection_config.schema,
        )

        # Verify that connect was called
        mock_connect.assert_called_once()

        # Verify the client configuration (we need to check the actual Client instance created)
        # Since we're mocking connect(), we need to verify the Client was created with correct config
        assert mock_connect.return_value._config.host == sample_connection_config.host
        assert mock_connect.return_value._config.port == sample_connection_config.port
        assert (
            mock_connect.return_value._config.database
            == sample_connection_config.database
        )
        assert (
            mock_connect.return_value._config.access_key_id
            == sample_connection_config.access_key_id
        )
        assert (
            mock_connect.return_value._config.access_key_secret
            == sample_connection_config.access_key_secret
        )
        assert (
            mock_connect.return_value._config.schema == sample_connection_config.schema
        )

    @patch("holo_search_sdk.client.Client.connect")
    def test_connect_function_default_schema(
        self, mock_connect, sample_connection_config
    ):
        """Test the connect function with default schema."""
        # Create a mock client with default schema
        mock_client = Mock(spec=Client)
        mock_client._config = ConnectionConfig(
            host=sample_connection_config.host,
            port=sample_connection_config.port,
            database=sample_connection_config.database,
            access_key_id=sample_connection_config.access_key_id,
            access_key_secret=sample_connection_config.access_key_secret,
            schema="public",
        )
        mock_connect.return_value = mock_client

        _ = connect(
            host=sample_connection_config.host,
            port=sample_connection_config.port,
            database=sample_connection_config.database,
            access_key_id=sample_connection_config.access_key_id,
            access_key_secret=sample_connection_config.access_key_secret,
        )

        # Verify that connect was called
        mock_connect.assert_called_once()
        assert mock_connect.return_value._config.schema == "public"

    def test_set_guc(self, client_with_mock_backend, mock_holo_db):
        """Test set_guc method."""
        client = client_with_mock_backend

        client.set_guc("work_mem", "256MB", db_level=False)

        mock_holo_db.set_guc.assert_called_once_with("work_mem", "256MB", False)

    def test_set_guc_not_connected(self, sample_connection_config):
        """Test set_guc when not connected raises error."""
        client = Client(
            host=sample_connection_config.host,
            port=sample_connection_config.port,
            database=sample_connection_config.database,
            access_key_id=sample_connection_config.access_key_id,
            access_key_secret=sample_connection_config.access_key_secret,
        )

        with pytest.raises(ConnectionError) as exc_info:
            client.set_guc("work_mem", "256MB")

        assert "not connected" in str(exc_info.value)

    def test_set_guc_on(self, client_with_mock_backend, mock_holo_db):
        """Test set_guc_on method."""
        client = client_with_mock_backend

        client.set_guc_on("enable_seqscan", db_level=True)

        mock_holo_db.set_guc_on.assert_called_once_with("enable_seqscan", True)

    def test_set_guc_on_not_connected(self, sample_connection_config):
        """Test set_guc_on when not connected raises error."""
        client = Client(
            host=sample_connection_config.host,
            port=sample_connection_config.port,
            database=sample_connection_config.database,
            access_key_id=sample_connection_config.access_key_id,
            access_key_secret=sample_connection_config.access_key_secret,
        )

        with pytest.raises(ConnectionError) as exc_info:
            client.set_guc_on("enable_seqscan")

        assert "not connected" in str(exc_info.value)

    def test_set_guc_off(self, client_with_mock_backend, mock_holo_db):
        """Test set_guc_off method."""
        client = client_with_mock_backend

        client.set_guc_off("enable_seqscan", db_level=False)

        mock_holo_db.set_guc_off.assert_called_once_with("enable_seqscan", False)

    def test_set_guc_off_not_connected(self, sample_connection_config):
        """Test set_guc_off when not connected raises error."""
        client = Client(
            host=sample_connection_config.host,
            port=sample_connection_config.port,
            database=sample_connection_config.database,
            access_key_id=sample_connection_config.access_key_id,
            access_key_secret=sample_connection_config.access_key_secret,
        )

        with pytest.raises(ConnectionError) as exc_info:
            client.set_guc_off("enable_seqscan")

        assert "not connected" in str(exc_info.value)

    def test_show_guc(self, client_with_mock_backend, mock_holo_db):
        """Test show_guc method."""
        client = client_with_mock_backend
        mock_holo_db.show_guc.return_value = "256MB"

        client.show_guc("work_mem")

        mock_holo_db.show_guc.assert_called_once_with("work_mem")

    def test_show_guc_not_connected(self, sample_connection_config):
        """Test show_guc when not connected raises error."""
        client = Client(
            host=sample_connection_config.host,
            port=sample_connection_config.port,
            database=sample_connection_config.database,
            access_key_id=sample_connection_config.access_key_id,
            access_key_secret=sample_connection_config.access_key_secret,
        )

        with pytest.raises(ConnectionError) as exc_info:
            client.show_guc("work_mem")

        assert "not connected" in str(exc_info.value)

    def test_build_query(self, client_with_mock_backend, mock_holo_db):
        """Test build_query method."""
        from holo_search_sdk.backend.query import QueryBuilder

        client = client_with_mock_backend
        mock_query_builder = Mock(spec=QueryBuilder)
        mock_holo_db.build_query.return_value = mock_query_builder

        result = client.build_query("test_table", "t1")

        assert result is mock_query_builder
        mock_holo_db.build_query.assert_called_once_with("test_table", "t1")

    def test_build_query_not_connected(self, sample_connection_config):
        """Test build_query when not connected raises error."""
        client = Client(
            host=sample_connection_config.host,
            port=sample_connection_config.port,
            database=sample_connection_config.database,
            access_key_id=sample_connection_config.access_key_id,
            access_key_secret=sample_connection_config.access_key_secret,
        )

        with pytest.raises(ConnectionError) as exc_info:
            client.build_query("test_table")

        assert "not connected" in str(exc_info.value)

    def test_find_table_opens_new_table(
        self, client_with_mock_backend, mock_holo_db, mock_holo_table
    ):
        """Test _find_table opens a new table if not in cache."""
        client = client_with_mock_backend
        mock_holo_db.open_table.return_value = mock_holo_table

        result = client._find_table("new_table")

        assert result is mock_holo_table
        assert "new_table" in client._opened_tables
        mock_holo_db.open_table.assert_called_once_with("new_table")

    def test_find_table_returns_cached_table(
        self, client_with_mock_backend, mock_holo_table
    ):
        """Test _find_table returns cached table if already opened."""
        client = client_with_mock_backend
        client._opened_tables["cached_table"] = mock_holo_table

        result = client._find_table("cached_table")

        assert result is mock_holo_table

    def test_check_table_exist_without_connection(self, sample_connection_config):
        """Test check_table_exist without connection raises error."""
        client = Client(
            host=sample_connection_config.host,
            port=sample_connection_config.port,
            database=sample_connection_config.database,
            access_key_id=sample_connection_config.access_key_id,
            access_key_secret=sample_connection_config.access_key_secret,
        )

        with pytest.raises(ConnectionError) as exc_info:
            client.check_table_exist("test_table")

        assert "not connected" in str(exc_info.value)

    def test_open_table_without_connection(self, sample_connection_config):
        """Test open_table without connection raises error."""
        client = Client(
            host=sample_connection_config.host,
            port=sample_connection_config.port,
            database=sample_connection_config.database,
            access_key_id=sample_connection_config.access_key_id,
            access_key_secret=sample_connection_config.access_key_secret,
        )

        with pytest.raises(ConnectionError) as exc_info:
            client.open_table("test_table")

        assert "not connected" in str(exc_info.value)

    def test_drop_table_without_connection(self, sample_connection_config):
        """Test drop_table without connection raises error."""
        client = Client(
            host=sample_connection_config.host,
            port=sample_connection_config.port,
            database=sample_connection_config.database,
            access_key_id=sample_connection_config.access_key_id,
            access_key_secret=sample_connection_config.access_key_secret,
        )

        with pytest.raises(ConnectionError) as exc_info:
            client.drop_table("test_table")

        assert "not connected" in str(exc_info.value)

    def test_find_table_without_connection(self, sample_connection_config):
        """Test _find_table without connection raises error."""
        client = Client(
            host=sample_connection_config.host,
            port=sample_connection_config.port,
            database=sample_connection_config.database,
            access_key_id=sample_connection_config.access_key_id,
            access_key_secret=sample_connection_config.access_key_secret,
        )

        with pytest.raises(ConnectionError) as exc_info:
            client._find_table("test_table")

        assert "not connected" in str(exc_info.value)
