"""
Hologres backend implementation for Holo Search SDK.

Provides database backend implementations and factory functions.
"""

from typing import Any, Optional

from psycopg import sql as psql
from psycopg.abc import Query
from typing_extensions import LiteralString

from holo_search_sdk.backend.query import QueryBuilder

from ..exceptions import ConnectionError, QueryError, TableError
from ..types import ConnectionConfig
from .connection import HoloConnect
from .table import HoloTable


class HoloDB:
    """
    Hologres backend implementation.

    Provides database backend implementations and factory functions.
    """

    def __init__(self, config: ConnectionConfig):
        """Initialize the Hologres database backend."""
        self._connection: Optional[HoloConnect] = None
        self._config: ConnectionConfig = config
        self._connected: bool = False
        self._name: str = config.database

    def connect(self) -> None:
        """Establish connection to Hologres database."""
        self._connection = HoloConnect(self._config).connect()
        self._connected = True

    def disconnect(self) -> None:
        """Close connection to Hologres database."""
        if self._connection:
            self._connection.close()
            self._connection = None
        self._connected = False

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
        if not self._connected or not self._connection:
            raise ConnectionError("Database is not connected. Call connect() first.")
        if fetch_result:
            return self._connection.fetchall(sql)
        else:
            return self._connection.execute(sql, use_transaction=use_transaction)

    # def create_table(
    #     self,
    #     table_name: str,
    #     columns: Mapping[str, Union[str, Tuple[str, str]]],
    #     exist_ok: bool = True,
    # ) -> HoloTable:
    #     """
    #     Create a new table in Hologres database.

    #     Args:
    #         table_name: Table name
    #         columns (Dict[str, Union[str, Tuple[str, str]]]): Dictionary of column definitions
    #             - Dictionary key is the column name
    #             - Dictionary value can be one of the following formats:
    #                 * str: Column type only, e.g., 'VARCHAR(255)', 'TEXT', 'INTEGER'
    #                 * Tuple[str, str]: (column_type, constraints), e.g., ('VARCHAR(255)', 'PRIMARY KEY')
    #         exist_ok: If True, do not raise an error if the table already exists.
    #     """
    #     if not self._connected or not self._connection:
    #         raise ConnectionError("Database not connected. Call connect() first.")
    #     if not exist_ok and self.check_table_exist(table_name):
    #         raise TableError(f"Table {table_name} already exists")
    #     sql = f"CREATE TABLE IF NOT EXISTS {table_name} ("
    #     for column_name, column_config in columns.items():
    #         if isinstance(column_config, str):
    #             sql += f"{column_name} {column_config}, "
    #         else:
    #             sql += f"{column_name} {column_config[0]} {column_config[1]}, "
    #     sql = sql[:-2] + ");"
    #     self._connection.execute(sql)
    #     return HoloTable(self._connection, table_name)

    def check_table_exist(self, table_name: str) -> bool:
        """
        Check if the table exists.

        Args:
            table_name (str): Name of the table.
        """
        if not self._connected or not self._connection:
            raise ConnectionError("Database not connected. Call connect() first.")

        sql = psql.SQL(
            """
        SELECT EXISTS(
            SELECT 1
            FROM pg_tables
            WHERE schemaname = {}
            AND tablename = {}
        );
        """
        ).format(psql.Literal(self._config.schema), psql.Literal(table_name))
        res = self._connection.fetchone(sql)
        if not res:
            raise QueryError("Error executing SQL query")
        elif res[0] is True:
            return True
        elif res[0] is False:
            return False
        else:
            raise QueryError("Unexpected result from query")

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
        if not self._connected or not self._connection:
            raise ConnectionError("Database not connected. Call connect() first.")

        is_exist = self.check_table_exist(table_name)
        if is_exist:
            return HoloTable(self._connection, table_name, table_alias)
        else:
            raise TableError(f"Table {table_name} does not exist")

    def drop_table(self, table_name: str) -> None:
        """
        Drop a table if it exists.

        Args:
            table_name: Table name
        """
        if not self._connected or not self._connection:
            raise ConnectionError("Database not connected. Call connect() first.")

        self._connection.execute(
            psql.SQL("DROP TABLE IF EXISTS {};").format(psql.Identifier(table_name))
        )

    def set_guc(self, guc: LiteralString, value: Any, db_level: bool = False) -> None:
        """
        Set GUC (Global User Configuration) for the database.

        Args:
            guc: GUC name
            value: GUC value
            db_level: Whether to set the GUC at the database level. Defaults to False.
        """
        if not self._connected or not self._connection:
            raise ConnectionError("Database not connected. Call connect() first.")

        if db_level:
            self._connection.execute(
                psql.SQL("ALTER database {} SET {} = {};").format(
                    psql.Identifier(self._name), psql.SQL(guc), psql.Literal(value)
                )
            )
        else:
            self._connection.execute(
                psql.SQL("SET {} = {};").format(psql.SQL(guc), psql.Literal(value))
            )

    def set_guc_on(self, guc: LiteralString, db_level: bool = False) -> None:
        """
        Set GUC (Global User Configuration) "on" for the database.

        Args:
            guc: GUC name
            db_level: Whether to set the GUC at the database level. Defaults to False.
        """
        if not self._connected or not self._connection:
            raise ConnectionError("Database not connected. Call connect() first.")

        if db_level:
            self._connection.execute(
                psql.SQL("ALTER database {} SET {} = on;").format(
                    psql.Identifier(self._name), psql.SQL(guc)
                )
            )
        else:
            self._connection.execute(psql.SQL("SET {} = on;").format(psql.SQL(guc)))

    def set_guc_off(self, guc: LiteralString, db_level: bool = False) -> None:
        """
        Set GUC (Global User Configuration) "off" for the database.

        Args:
            guc: GUC name
            db_level: Whether to set the GUC at the database level. Defaults to False.
        """
        if not self._connected or not self._connection:
            raise ConnectionError("Database not connected. Call connect() first.")

        if db_level:
            self._connection.execute(
                psql.SQL("ALTER database {} SET {} = off;").format(
                    psql.Identifier(self._name), psql.SQL(guc)
                )
            )
        else:
            self._connection.execute(psql.SQL("SET {} = off;").format(psql.SQL(guc)))

    def show_guc(self, guc: LiteralString) -> Any:
        """
        Show GUC (Global User Configuration) for the database.

        Args:
            guc: GUC name

        Returns:
            Any: GUC value
        """
        if not self._connected or not self._connection:
            raise ConnectionError("Database not connected. Call connect() first.")

        res = self._connection.fetchone(psql.SQL("SHOW {};").format(psql.SQL(obj=guc)))
        return res[0] if res else None

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
        if not self._connected or not self._connection:
            raise ConnectionError("Database not connected. Call connect() first.")

        return QueryBuilder(self._connection, table_name, table_alias)
