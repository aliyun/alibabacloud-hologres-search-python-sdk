"""
Client module for Holo Search SDK.

Provides the main client interface for connecting to and managing database connections.
"""

from typing import Any, Dict, List, Mapping, Optional, Union

from psycopg.abc import Query
from typing_extensions import LiteralString

from holo_search_sdk.backend.query import QueryBuilder

from .backend import HoloDB, HoloTable
from .exceptions import ConnectionError
from .types import (
    BaseQuantizationType,
    ConnectionConfig,
    DistanceType,
    PreciseIOType,
    PreciseQuantizationType,
)


class Client:
    """
    Main client class for Holo Search SDK.

    Provides methods to connect to databases, manage collections,
    and perform database-level operations.
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        access_key_id: str,
        access_key_secret: str,
        schema: str = "public",
        autocommit: bool = False,
    ):
        """
        Initialize the client with database URI and configuration.

        Args:
            host (str): Hostname of the database.
            port (int): Port of the database.
            database (str): Name of the database.
            access_key_id (str): Access key ID for database authentication.
            access_key_secret (str): Access key secret for database authentication.
            schema (str): Schema of the database.
            autocommit (bool): Whether to enable autocommit mode. If True, don't start transactions automatically.
        """
        self._config: ConnectionConfig = ConnectionConfig(
            host, port, database, access_key_id, access_key_secret, schema, autocommit
        )
        self._backend: Optional[HoloDB] = None
        self._opened_tables: Dict[str, HoloTable] = {}

    def connect(self) -> "Client":
        """Establish connection to the database."""
        try:
            self._backend = HoloDB(config=self._config)
            self._backend.connect()
            return self
        except Exception as e:
            raise ConnectionError(f"Failed to connect to database: {str(e)}")

    def disconnect(self) -> None:
        """Close the database connection."""
        if self._backend:
            self._backend.disconnect()
            self._backend = None
            self._opened_tables.clear()

    def execute(
        self,
        sql: Query,
        fetch_result: bool = False,
        use_transaction: Optional[bool] = None,
    ):
        """
        Execute a SQL query.

        Args:
            sql: SQL query to execute
            fetch_result: Whether to fetch the result of the query
            use_transaction: Whether to execute query in a transaction. If None, use the connection's autocommit mode.
        """
        if not self._backend:
            raise ConnectionError("Client not connected. Call connect() first.")
        return self._backend.execute(sql, fetch_result, use_transaction)

    # def create_table(
    #     self,
    #     table_name: str,
    #     columns: Mapping[str, Union[str, Tuple[str, str]]],
    #     exist_ok: bool = True,
    # ) -> HoloTable:
    #     """
    #     Create a new table in Hologres database.
    #     Args:
    #         table_name (str): The name of the table to be created
    #         columns (Dict[str, Union[str, Tuple[str, str]]]): Dictionary of column definitions
    #             - Dictionary key is the column name
    #             - Dictionary value can be one of the following formats:
    #                 * str: Column type only, e.g., 'VARCHAR(255)', 'TEXT', 'INTEGER'
    #                 * Tuple[str, str]: (column_type, constraints), e.g., ('VARCHAR(255)', 'PRIMARY KEY')
    #         exist_ok: If True, do not raise an error if the table already exists.
    #     """
    #     if not self._backend:
    #         raise ConnectionError("Client not connected. Call connect() first.")
    #     table = self._backend.create_table(table_name, columns, exist_ok)
    #     self._opened_tables[table_name] = table
    #     return table

    def check_table_exist(self, table_name: str) -> bool:
        """
        Check if the table exists.

        Args:
            table_name (str): Name of the table.
        """
        if not self._backend:
            raise ConnectionError("Client not connected. Call connect() first.")
        return self._backend.check_table_exist(table_name)

    def open_table(
        self, table_name: str, table_alias: Optional[str] = None
    ) -> HoloTable:
        """
        Open an existing table in Hologres database.

        Args:
            table_name: Table name
            table_alias: Alias for the table. Defaults to None.

        Returns:
            HoloTable: Table instance
        """
        if not self._backend:
            raise ConnectionError("Client not connected. Call connect() first.")
        table = self._backend.open_table(table_name, table_alias)
        self._opened_tables[table_name] = table
        return table

    def drop_table(self, table_name: str) -> None:
        """
        Drop a table if it exists.

        Args:
            table_name: Table name
        """
        if not self._backend:
            raise ConnectionError("Client not connected. Call connect() first.")
        if table_name in self._opened_tables:
            del self._opened_tables[table_name]
        self._backend.drop_table(table_name)

    def insert_one(
        self,
        table_name: str,
        values: List[Any],
        column_names: Optional[List[str]] = None,
    ) -> HoloTable:
        """
        Insert one record into the table.

        Args:
            table_name (str): Table name
            values (List[Any]): Values to insert.
            column_names ([List[str]]): Column names. Defaults to None.
        """
        table = self._find_table(table_name)
        return table.insert_one(values, column_names)

    def insert_multi(
        self,
        table_name: str,
        values: List[List[Any]],
        column_names: Optional[List[str]] = None,
    ) -> HoloTable:
        """
        Insert multiple records into the table.

        Args:
            table_name (str): Table name.
            values (List[List[Any]]): Values to insert.
            column_names ([List[str]]): Column names. Defaults to None.
        """
        table = self._find_table(table_name)
        return table.insert_multi(values, column_names)

    def set_vector_index(
        self,
        table_name: str,
        column: str,
        distance_method: DistanceType,
        base_quantization_type: BaseQuantizationType,
        max_degree: int = 64,
        ef_construction: int = 400,
        use_reorder: bool = False,
        precise_quantization_type: PreciseQuantizationType = "fp32",
        precise_io_type: PreciseIOType = "block_memory_io",
        max_total_size_to_merge_mb: int = 4096,
        build_thread_count: int = 16,
    ) -> HoloTable:
        """
        Set a vector index for a column.

        Args:
            table_name (str): Table name.
            column (str): Column name.
            distance_method (str): Distance method. Available options are "Euclidean", "InnerProduct", "Cosine".
            base_quantization_type (str): Base quantization type. Available options are "sq8", "sq8_uniform", "fp16", "fp32", "rabitq".
            max_degree (int): During the graph construction process, each vertex will attempt to connect to its nearest max_degree vertices.
            ef_construction (int): Used to control the search depth during the graph construction process.
            use_reorder (bool): Whether to use the HGraph high-precision index.
            precise_quantization_type (str): Precise quantization type. Available options are "sq8", "sq8_uniform", "fp16", "fp32".
            precise_io_type (str): Precise IO type. Available options are "block_memory_io", "reader_io".
            max_total_size_to_merge_mb (int): Maximum file size of data when it is merged on the disk, in MB.
            build_thread_count (int): The number of threads used during the index building process.
        """
        table = self._find_table(table_name)
        return table.set_vector_index(
            column,
            distance_method,
            base_quantization_type,
            max_degree,
            ef_construction,
            use_reorder,
            precise_quantization_type,
            precise_io_type,
            max_total_size_to_merge_mb,
            build_thread_count,
        )

    def set_vector_indexes(
        self, table_name: str, column_configs: Dict[str, Mapping[str, Union[str, int]]]
    ) -> HoloTable:
        """
        Set multiple vector indexes with different configurations.

        Args:
            table_name (str): Table name.
            column_configs (Dict[str, Dict]): Dictionary mapping column names to their index configurations.
                                              Each config should contain 'distance_method' and 'base_quantization_type'.

        Example:
            table.set_vector_indexes({
                "column_name": {
                    "distance_method": "Cosine",
                    "base_quantization_type": "rabitq",
                    "max_degree": 64,
                    "ef_construction": 400,
                    "use_reorder": False,
                    "precise_quantization_type": "fp32",
                    "precise_io_type": "block_memory_io",
                    "max_total_size_to_merge_mb": 4096,
                    "build_thread_count": 16
                }
            })
        """
        table = self._find_table(table_name)
        return table.set_vector_indexes(column_configs)

    def delete_vector_indexes(self, table_name: str) -> HoloTable:
        """
        Delete all vector indexes.

        Args:
            table_name (str): Table name.
        """
        table = self._find_table(table_name)
        return table.delete_vector_indexes()

    def set_guc(self, guc: LiteralString, value: Any, db_level: bool = False) -> None:
        """
        Set GUC (Global User Configuration) for the database.

        Args:
            guc: GUC name
            value: GUC value
            db_level: Whether to set the GUC at the database level. Defaults to False.
        """
        if not self._backend:
            raise ConnectionError("Client not connected. Call connect() first.")
        self._backend.set_guc(guc, value, db_level)

    def set_guc_on(self, guc: LiteralString, db_level: bool = False) -> None:
        """
        Set GUC (Global User Configuration) "on" for the database.

        Args:
            guc: GUC name
            db_level: Whether to set the GUC at the database level. Defaults to False.
        """
        if not self._backend:
            raise ConnectionError("Client not connected. Call connect() first.")
        self._backend.set_guc_on(guc, db_level)

    def set_guc_off(self, guc: LiteralString, db_level: bool = False) -> None:
        """
        Set GUC (Global User Configuration) "off" for the database.

        Args:
            guc: GUC name
            db_level: Whether to set the GUC at the database level. Defaults to False.
        """
        if not self._backend:
            raise ConnectionError("Client not connected. Call connect() first.")
        self._backend.set_guc_off(guc, db_level)

    def show_guc(self, guc: LiteralString) -> Any:
        """
        Show GUC (Global User Configuration) for the database.

        Args:
            guc: GUC name

        Returns:
            Any: GUC value
        """
        if not self._backend:
            raise ConnectionError("Client not connected. Call connect() first.")
        self._backend.show_guc(guc)

    def build_query(
        self, table_name: Optional[str] = None, table_alias: Optional[str] = None
    ) -> QueryBuilder:
        """
        Build a query for the database.

        Args:
            table_name: Table name. Defaults to None.
            table_alias: Alias for the table. Defaults to None.

        Returns:
            QueryBuilder: Query builder instance
        """
        if not self._backend:
            raise ConnectionError("Client not connected. Call connect() first.")
        return self._backend.build_query(table_name, table_alias)

    def _find_table(self, table_name: str) -> HoloTable:
        if not self._backend:
            raise ConnectionError("Client not connected. Call connect() first.")
        if table_name not in self._opened_tables:
            table = self._backend.open_table(table_name)
            self._opened_tables[table_name] = table
        else:
            table = self._opened_tables[table_name]
        return table

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


def connect(
    host: str,
    port: int,
    database: str,
    access_key_id: str,
    access_key_secret: str,
    schema: str = "public",
) -> Client:
    """
    Create and return a new client instance.

    Args:
        host (str): Hostname of the database.
        port (int): Port of the database.
        database (str): Name of the database.
        access_key_id (str): Access key ID for database authentication.
        access_key_secret (str): Access key secret for database authentication.
        schema (str): Schema of the database.

    Returns:
        Client instance
    """
    return Client(
        host, port, database, access_key_id, access_key_secret, schema
    ).connect()
