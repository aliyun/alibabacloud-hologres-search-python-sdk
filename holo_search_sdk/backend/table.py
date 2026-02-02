"""
Hologres backend implementation for Holo Search SDK.

Provides integration with Hologres for full-text and vector search.
"""

import json
from collections import OrderedDict
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union, cast

from psycopg import sql as psql
from typing_extensions import LiteralString, Self

from ..exceptions import SqlError
from ..types import (
    BaseQuantizationType,
    DistanceType,
    PinyinFilterParamType,
    PreciseIOType,
    PreciseQuantizationType,
    TextFilterType,
    TextSearchModeType,
    TextSearchOperatorType,
    TokenizerType,
    VectorSearchFunction,
)
from .connection import HoloConnect
from .filter import FilterExpression
from .query import QueryBuilder
from .utils.sql_utils import (
    build_analyzer_params_sql,
    build_text_search_sql,
    build_tokenize_sql,
)


class HoloTable:
    """
    Table class for Holo Search SDK.
    """

    def __init__(self, db: HoloConnect, name: str, alias: Optional[str] = None):
        """
        Initialize the Table instance.

        Args:
            db (HoloConnect): Database connection.
            name (str): Name of the table.
        """
        self._db: HoloConnect = db
        self._name: str = name
        self._alias: Optional[str] = alias
        self._column_distance_methods: Dict[str, DistanceType] = {}
        self._columns: List[str] = []

    def get_name(self) -> str:
        """
        Get the name of the table.

        Returns:
            str: Name of the table.
        """
        return self._name

    def get_alias(self) -> Optional[str]:
        """
        Get the alias of the table.

        Returns:
            Optional[str]: Alias of the table.
        """
        return self._alias

    def vacuum(self) -> Self:
        """
        Vacuum the table.
        """
        sql = psql.SQL("VACUUM {};").format(psql.Identifier(self._name))
        self._db.execute(sql, use_transaction=False)
        return self

    def get_all_column_names(self) -> List[str]:
        """
        Get all column names of the table.

        Returns:
            List[str]: List of column names.
        """
        sql = psql.SQL(
            """
            SELECT column_name FROM information_schema.columns 
            WHERE table_catalog = {} and table_schema = {} and table_name = {} 
            ORDER BY ordinal_position ASC ;
            """
        ).format(
            psql.Literal(self._db.get_config().database),
            psql.Literal(self._db.get_config().schema),
            psql.Literal(self._name),
        )
        res = self._db.fetchall(sql)
        self._columns = [row[0] for row in res]

        return self._columns

    def insert_one(
        self, values: List[Any], column_names: Optional[List[str]] = None
    ) -> Self:
        """
        Insert one record into the table.

        Args:
            values (List[Any]): Values to insert.
            column_names ([List[str]]): Column names. Defaults to None.
        """
        sql = psql.SQL("INSERT INTO {} ").format(psql.Identifier(self._name))
        if column_names:
            sql += psql.SQL("({}) ").format(
                psql.SQL(", ").join(map(psql.Identifier, column_names))
            )
        sql += psql.SQL("VALUES ({});").format(
            psql.SQL(", ").join(psql.Placeholder() * len(values))
        )
        params = tuple(values)
        self._db.execute(sql, params)
        return self

    def insert_multi(
        self, values: List[List[Any]], column_names: Optional[List[str]] = None
    ) -> Self:
        """
        Insert multiple records into the table.

        Args:
            values (List[List[Any]]): Values to insert.
            column_names ([List[str]]): Column names. Defaults to None.
        """
        if not values:
            return self

        sql = psql.SQL("INSERT INTO {} ").format(psql.Identifier(self._name))
        if column_names:
            sql += psql.SQL("({}) ").format(
                psql.SQL(", ").join(map(psql.Identifier, column_names))
            )

        params: tuple[Any] = tuple()
        rows_sql: list[psql.Composed] = list()
        for row in values:
            params += tuple(row)
            rows_sql.append(
                psql.SQL("({})").format(
                    psql.SQL(", ").join(psql.Placeholder() * len(row))
                )
            )
        sql += psql.SQL("VALUES {};").format(psql.SQL(", ").join(rows_sql))

        self._db.execute(sql, params)
        return self

    def upsert_one(
        self,
        index_column: str,
        values: List[Any],
        column_names: Optional[List[str]] = None,
        update: bool = False,
        update_columns: Optional[List[str]] = None,
        update_action: Optional[str] = None,
        update_condition: Optional[LiteralString] = None,
    ) -> Self:
        """
        Insert one record into the table using ON CONFLICT clause.
        If a record with the same index_column value exists:
        - If update=True: update the existing record
        - If update=False: do nothing (ignore the conflict)

        Update action priority (when update=True):
        1. If update_action is provided, use it as the custom update action
        2. If update_columns is provided, update only the specified columns
        3. If column_names is provided, update the columns specified in column_names
        4. If none of the above, update all columns in the table

        Args:
            index_column (str): Column name to check for conflicts (typically a primary key or unique constraint column).
            values (List[Any]): Values to insert.
            column_names (Optional[List[str]]): Column names corresponding to the values. Defaults to None.
            update (bool): Whether to update on conflict. If False, ignore conflicts. Defaults to False.
            update_columns (Optional[List[str]]): Specific columns to update on conflict. Defaults to None.
            update_action (Optional[str]): Custom SQL update action. Defaults to None.
            update_condition (Optional[LiteralString]): Additional WHERE condition for the update. Defaults to None.
        """
        sql = psql.SQL("INSERT INTO {} ").format(psql.Identifier(self._name))
        if column_names:
            sql += psql.SQL("({}) ").format(
                psql.SQL(", ").join(map(psql.Identifier, column_names))
            )
        sql += psql.SQL("VALUES ({})").format(
            psql.SQL(", ").join(psql.Placeholder() * len(values))
        )
        params = tuple(values)

        if update:
            sql += psql.SQL(" ON CONFLICT ({}) DO UPDATE SET").format(
                psql.Identifier(index_column)
            )
            if update_action:
                sql += psql.SQL(" {}").format(psql.Identifier(update_action))
            elif update_columns:
                sql += psql.SQL(" {}").format(
                    psql.SQL(", ").join(
                        psql.SQL("{} = EXCLUDED.{}").format(
                            psql.Identifier(update_columns[i]),
                            psql.Identifier(update_columns[i]),
                        )
                        for i in range(len(update_columns))
                    )
                )
            elif column_names:
                sql += psql.SQL(" {}").format(
                    psql.SQL(", ").join(
                        psql.SQL("{} = EXCLUDED.{}").format(
                            psql.Identifier(column_names[i]),
                            psql.Identifier(column_names[i]),
                        )
                        for i in range(len(column_names))
                    )
                )
            else:
                if len(self._columns) == 0:
                    _ = self.get_all_column_names()
                sql += psql.SQL(" {}").format(
                    psql.SQL(", ").join(
                        psql.SQL("{} = EXCLUDED.{}").format(
                            psql.Identifier(self._columns[i]),
                            psql.Identifier(self._columns[i]),
                        )
                        for i in range(len(self._columns))
                    )
                )
            if update_condition:
                sql += psql.SQL(" WHERE {}").format(psql.SQL(update_condition))
        else:
            sql += psql.SQL(" ON CONFLICT ({}) DO NOTHING").format(
                psql.Identifier(index_column)
            )
        sql += psql.SQL(";")
        self._db.execute(sql, params)
        return self

    def upsert_multi(
        self,
        index_column: str,
        values: List[List[Any]],
        column_names: Optional[List[str]] = None,
        update: bool = False,
        update_columns: Optional[List[str]] = None,
        update_action: Optional[str] = None,
        update_condition: Optional[LiteralString] = None,
    ) -> Self:
        """
        Insert multiple records into the table using ON CONFLICT clause.
        If a record with the same index_column value exists:
        - If update=True: update the existing record
        - If update=False: do nothing (ignore the conflict)

        Update action priority (when update=True):
        1. If update_action is provided, use it as the custom update action
        2. If update_columns is provided, update only the specified columns
        3. If column_names is provided, update the columns specified in column_names
        4. If none of the above, update all columns in the table

        Args:
            index_column (str): Column name to check for conflicts (typically a primary key or unique constraint column).
            values (List[List[Any]]): List of value lists to insert.
            column_names (Optional[List[str]]): Column names corresponding to the values. Defaults to None.
            update (bool): Whether to update on conflict. If False, ignore conflicts. Defaults to False.
            update_columns (Optional[List[str]]): Specific columns to update on conflict. Defaults to None.
            update_action (Optional[str]): Custom SQL update action. Defaults to None.
            update_condition (Optional[LiteralString]): Additional WHERE condition for the update. Defaults to None.
        """
        sql = psql.SQL("INSERT INTO {} ").format(psql.Identifier(self._name))
        if column_names:
            sql += psql.SQL("({}) ").format(
                psql.SQL(", ").join(map(psql.Identifier, column_names))
            )
        params: tuple[Any] = tuple()
        rows_sql: list[psql.Composed] = list()
        for row in values:
            params += tuple(row)
            rows_sql.append(
                psql.SQL("({})").format(
                    psql.SQL(", ").join(psql.Placeholder() * len(row))
                )
            )
        sql += psql.SQL("VALUES {}").format(psql.SQL(", ").join(rows_sql))

        if update:
            sql += psql.SQL(" ON CONFLICT ({}) DO UPDATE SET").format(
                psql.Identifier(index_column)
            )
            if update_action:
                sql += psql.SQL(" {}").format(psql.Identifier(update_action))
            elif update_columns:
                sql += psql.SQL(" {}").format(
                    psql.SQL(", ").join(
                        psql.SQL("{} = EXCLUDED.{}").format(
                            psql.Identifier(update_columns[i]),
                            psql.Identifier(update_columns[i]),
                        )
                        for i in range(len(update_columns))
                    )
                )
            elif column_names:
                sql += psql.SQL(" {}").format(
                    psql.SQL(", ").join(
                        psql.SQL("{} = EXCLUDED.{}").format(
                            psql.Identifier(column_names[i]),
                            psql.Identifier(column_names[i]),
                        )
                        for i in range(len(column_names))
                    )
                )
            else:
                if len(self._columns) == 0:
                    _ = self.get_all_column_names()
                sql += psql.SQL(" {}").format(
                    psql.SQL(", ").join(
                        psql.SQL("{} = EXCLUDED.{}").format(
                            psql.Identifier(self._columns[i]),
                            psql.Identifier(self._columns[i]),
                        )
                        for i in range(len(self._columns))
                    )
                )
            if update_condition:
                sql += psql.SQL(" WHERE {}").format(psql.SQL(update_condition))
        else:
            sql += psql.SQL(" ON CONFLICT ({}) DO NOTHING").format(
                psql.Identifier(index_column)
            )
        sql += psql.SQL(";")
        self._db.execute(sql, params)
        return self

    def overwrite(
        self,
        values: Optional[List[List[Any]]] = None,
        values_expression: Optional[Union[LiteralString, QueryBuilder]] = None,
    ) -> Self:
        """
        Overwrite all data in the table using INSERT OVERWRITE statement.
        This operation will replace all existing data in the table with the new data.
        Either values or values_expression must be provided, but not both.

        Args:
            values (Optional[List[List[Any]]]): List of value lists to insert. Defaults to None.
            values_expression (Optional[Union[LiteralString, QueryBuilder]]):
                SQL query or QueryBuilder to select data from. Defaults to None.
        """
        if values is None and values_expression is None:
            raise SqlError("Either values or values_expression must be provided.")
        if values is not None and values_expression is not None:
            raise SqlError("Only one of values or values_expression can be provided.")
        sql = psql.SQL("INSERT OVERWRITE {} ").format(psql.Identifier(self._name))
        if values is not None:
            params: tuple[Any] = tuple()
            rows_sql: list[psql.Composed] = list()
            for row in values:
                params += tuple(row)
                rows_sql.append(
                    psql.SQL("({})").format(
                        psql.SQL(", ").join(psql.Placeholder() * len(row))
                    )
                )
            sql += psql.SQL("VALUES {};").format(psql.SQL(", ").join(rows_sql))
            self._db.execute(sql, params)
        elif values_expression is not None:
            if isinstance(values_expression, QueryBuilder):
                sql += values_expression._generate_sql()
            else:
                sql += psql.SQL(values_expression)
                sql += psql.SQL(";")
            self._db.execute(sql)
        return self

    def update(
        self,
        columns: List[str],
        values: List[Any],
        table_alias: Optional[str] = None,
        from_table: Optional[str] = None,
        from_alias: Optional[str] = None,
        condition: Optional[
            Union[LiteralString, psql.Composable, FilterExpression]
        ] = None,
    ) -> Self:
        """
        Update records in the table that match the specified condition.
        Supports updating with JOIN using FROM clause.

        Args:
            columns (List[str]): Column names to update.
            values (List[Any]): Values to set for the corresponding columns.
            table_alias (Optional[str]): Alias for the target table. Defaults to None.
            from_table (Optional[str]): Table name to join with in FROM clause. Defaults to None.
            from_alias (Optional[str]): Alias for the FROM table. Defaults to None.
            condition (Optional[Union[LiteralString, psql.Composable, FilterExpression]]):
                WHERE condition to filter records to update. Defaults to None.
        """
        sql = psql.SQL("UPDATE {}").format(psql.Identifier(self._name))
        if table_alias:
            sql += psql.SQL(" {}").format(psql.Identifier(table_alias))
        elif self._alias:
            sql += psql.SQL(" {}").format(psql.Identifier(self._alias))
        sql += psql.SQL(" SET ")
        sql += psql.SQL(", ").join(
            psql.SQL("{} = {}").format(psql.Identifier(columns[i]), psql.Placeholder())
            for i in range(len(columns))
        )
        if from_table:
            sql += psql.SQL(" FROM {}").format(psql.Identifier(from_table))
            if from_alias:
                sql += psql.SQL(" {}").format(psql.Identifier(from_alias))

        if condition:
            if isinstance(condition, FilterExpression):
                sql += psql.SQL(" WHERE {}").format(condition.to_sql())
            elif isinstance(condition, psql.Composable):
                sql += psql.SQL(" WHERE {}").format(condition)
            else:
                sql += psql.SQL(" WHERE {}").format(psql.SQL(condition))
        sql += psql.SQL(";")
        self._db.execute(sql, tuple(values))
        return self

    def delete(self, condition: LiteralString) -> Self:
        """
        Delete records from the table that match the specified condition.

        Args:
            condition (LiteralString): WHERE condition to filter records to delete.
        """
        sql = psql.SQL("DELETE FROM {} WHERE {};").format(
            psql.Identifier(self._name), psql.SQL(condition)
        )
        self._db.execute(sql)
        return self

    def truncate(self) -> Self:
        """
        Remove all records from the table while preserving the table structure.
        """
        sql = psql.SQL("TRUNCATE TABLE {};").format(psql.Identifier(self._name))
        self._db.execute(sql)
        return self

    def drop(self):
        """
        Drop (delete) the table from the database.
        This operation removes the table and all its data permanently.
        Uses DROP TABLE IF EXISTS to avoid errors if the table doesn't exist.
        """
        sql = psql.SQL("DROP TABLE IF EXISTS {};").format(psql.Identifier(self._name))
        self._db.execute(sql)

    def set_vector_index(
        self,
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
    ) -> Self:
        """
        Set a vector index for a column.

        Args:
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
        builder_params = psql.SQL(
            '{{"max_degree": {}, "ef_construction": {}, "base_quantization_type": {}, "use_reorder": {}, "precise_quantization_type": {}, "precise_io_type": {}, "max_total_size_to_merge_mb": {}, "build_thread_count": {}}}'
        ).format(
            psql.Literal(max_degree),
            psql.Literal(ef_construction),
            psql.Identifier(base_quantization_type),
            psql.Literal(use_reorder),
            psql.Identifier(precise_quantization_type),
            psql.Identifier(precise_io_type),
            psql.Literal(max_total_size_to_merge_mb),
            psql.Literal(build_thread_count),
        )
        sql = psql.SQL(
            "CALL set_table_property({}, 'vectors', '{{{}: {{"
            + '"algorithm": "HGraph", "distance_method": {}, "builder_params": {}'
            + "}}}}');"
        ).format(
            psql.Literal(self._name),
            psql.Identifier(column),
            psql.Identifier(distance_method),
            builder_params,
        )
        self._db.execute(sql)
        self._column_distance_methods.clear()
        self._column_distance_methods[column] = distance_method
        return self

    def set_vector_indexes(
        self, column_configs: Mapping[str, Mapping[str, Union[str, int, bool]]]
    ) -> Self:
        """
        Set multiple vector indexes with different configurations.

        Args:
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
        vectors_config = None

        for column, config in column_configs.items():
            builder_params = psql.SQL(
                '{{"max_degree": {}, "ef_construction": {}, "base_quantization_type": {}, "use_reorder": {}, "precise_quantization_type": {}, "precise_io_type": {}, "max_total_size_to_merge_mb": {}, "build_thread_count": {}}}'
            ).format(
                psql.Literal(config.get("max_degree", 64)),
                psql.Literal(config.get("ef_construction", 400)),
                psql.Identifier(str(config["base_quantization_type"])),
                psql.Literal(config.get("use_reorder", False)),
                psql.Identifier(str(config.get("precise_quantization_type", "fp32"))),
                psql.Identifier(str(config.get("precise_io_type", "block_memory_io"))),
                psql.Literal(config.get("max_total_size_to_merge_mb", 4096)),
                psql.Literal(config.get("build_thread_count", 16)),
            )
            single_config = psql.SQL(
                '{}: {{"algorithm": "HGraph", "distance_method": {}, "builder_params": {}}}'
            ).format(
                psql.Identifier(column),
                psql.Identifier(str(config["distance_method"])),
                builder_params,
            )
            if vectors_config is None:
                vectors_config = single_config
            else:
                vectors_config += psql.SQL(", ") + single_config

        sql = psql.SQL(
            """
            CALL set_table_property(
                {},
                'vectors',
                '{{{}}}');
            """
        ).format(psql.Literal(self._name), vectors_config)
        self._db.execute(sql)
        self._column_distance_methods.clear()
        for column, config in column_configs.items():
            self._column_distance_methods[column] = cast(
                DistanceType, config["distance_method"]
            )
        return self

    def delete_vector_indexes(self) -> Self:
        """
        Delete all vector indexes.
        """
        sql = psql.SQL(
            """
        CALL set_table_property(
            {},
            'vectors',
            '{{}}');
        """
        ).format(psql.Literal(self._name))
        self._db.execute(sql)
        self._column_distance_methods.clear()
        return self

    def get_vector_index_info(self) -> Optional[Dict[Any, Any]]:
        """
        Get vector index information.
        """
        sql = psql.SQL(
            "SELECT property_value FROM hologres.hg_table_properties WHERE table_namespace = {} and table_name = {} and property_key = 'vectors';"
        ).format(psql.Literal(self._db.get_config().schema), psql.Literal(self._name))
        res = self._db.fetchone(sql)
        if res is None:
            return None
        else:
            try:
                return json.loads(res[0])
            except:
                return None

    def _get_column_distance_method(self, column: str) -> Optional[DistanceType]:
        index_info = self.get_vector_index_info()
        if index_info is None:
            return None
        else:
            try:
                distance_method = cast(
                    DistanceType, index_info[column]["distance_method"]
                )
                self._column_distance_methods[column] = distance_method
                return distance_method
            except:
                return None

    def search_vector(
        self,
        vector: Sequence[Union[str, float]],
        column: str,
        output_name: Optional[LiteralString] = None,
        distance_method: Optional[DistanceType] = None,
    ) -> QueryBuilder:
        """
        Search for vectors in the table.

        Args:
            vector (Union[str, float]): Vector to search for.
            column (str): Column to search in.
            output_name (str): Name of the output column.
            distance_method (DistanceType): Distance method to use.

        Returns:
            QueryBuilder: QueryBuilder object.
        """
        if distance_method is not None:
            _distance_method = distance_method
        elif column in self._column_distance_methods:
            _distance_method = self._column_distance_methods[column]
        else:
            _distance_method = self._get_column_distance_method(column)
        if _distance_method is None:
            raise SqlError(f"Distance method must be set for column {column}")
        search_func = VectorSearchFunction[_distance_method]
        vector_array = "{" + ",".join(map(str, vector)) + "}"
        sql = psql.SQL("{}({}, {})").format(
            psql.SQL(search_func), psql.Identifier(column), psql.Literal(vector_array)
        )

        qb = QueryBuilder(self._db, self._name, self._alias)
        if output_name:
            qb = qb.select((sql, output_name))
            qb = qb.set_distance_column(output_name)
        else:
            qb = qb.select(sql)
            qb = qb.set_distance_column(search_func)

        return qb

    def select(
        self,
        columns: Union[
            LiteralString,
            psql.Composable,
            List[
                Union[
                    LiteralString,
                    psql.Composable,
                    Tuple[
                        Union[LiteralString, psql.Composable],
                        Optional[Union[str, psql.Composable]],
                    ],
                ]
            ],
            Dict[LiteralString, Optional[Union[str, psql.Composable]]],
            Tuple[
                Union[LiteralString, psql.Composable],
                Optional[Union[str, psql.Composable]],
            ],
        ],
    ) -> "QueryBuilder":
        """
        Select columns from the table.

        Args:
            columns (Union[LiteralString, psql.Composable, List, Dict, Tuple]): Columns to select.

        Returns:
                QueryBuilder: QueryBuilder object.
        """

        query_builder = QueryBuilder(self._db, self._name, self._alias)
        query_builder = query_builder.select(columns)
        return query_builder

    def set_table_alias(self, alias: str) -> "QueryBuilder":
        """
        Set table alias.

        Args:
            alias (str): Alias to set.

        Returns:
            QueryBuilder: QueryBuilder object.
        """
        self._alias = alias
        return QueryBuilder(self._db, self._name, alias)

    def get_by_key(
        self,
        key_column: str,
        key_value: Any,
        return_columns: Optional[
            Union[
                LiteralString,
                psql.Composable,
                List[
                    Union[
                        LiteralString,
                        psql.Composable,
                        Tuple[
                            Union[LiteralString, psql.Composable],
                            Optional[Union[str, psql.Composable]],
                        ],
                    ]
                ],
                Dict[LiteralString, Optional[Union[str, psql.Composable]]],
                Tuple[
                    Union[LiteralString, psql.Composable],
                    Optional[Union[str, psql.Composable]],
                ],
            ]
        ] = None,
    ) -> QueryBuilder:
        """
        Get record by a specific key and key value.

        Args:
            key_column (str): Name of the key column.
            key_value (Any): Key value to search for.
            return_columns (Optional[Union[LiteralString, psql.Composable, List, Dict, Tuple]]): Specific columns to select. If None, selects all columns.

        Returns:
            QueryBuilder: QueryBuilder object.
        """
        query_builder = QueryBuilder(self._db, self._name, self._alias)

        # Select columns (all columns if not specified)
        if return_columns:
            query_builder = query_builder.select(return_columns)
        else:
            query_builder = query_builder.select("*")

        # Add WHERE condition for key name and key value
        where_condition = psql.SQL("{} = {}").format(
            psql.Identifier(key_column),
            psql.Literal(key_value),
        )
        query_builder = query_builder.where(where_condition)

        return query_builder

    def get_multi_by_keys(
        self,
        key_column: str,
        key_values: List[Any],
        return_columns: Optional[
            Union[
                LiteralString,
                psql.Composable,
                List[
                    Union[
                        LiteralString,
                        psql.Composable,
                        Tuple[
                            Union[LiteralString, psql.Composable],
                            Optional[Union[str, psql.Composable]],
                        ],
                    ]
                ],
                Dict[LiteralString, Optional[Union[str, psql.Composable]]],
                Tuple[
                    Union[LiteralString, psql.Composable],
                    Optional[Union[str, psql.Composable]],
                ],
            ]
        ] = None,
    ) -> QueryBuilder:
        """
        Get multiple records by a key and key value list.

        Args:
            key_column (str): Name of the key column.
            key_values (List[Any]): List of key values to search for.
            return_columns (Optional[Union[LiteralString, psql.Composable, List, Dict, Tuple]]): Specific columns to select. If None, selects all columns.

        Returns:
            QueryBuilder: QueryBuilder object.
        """
        query_builder = QueryBuilder(self._db, self._name, self._alias)

        # Select columns (all columns if not specified)
        if return_columns:
            query_builder = query_builder.select(return_columns)
        else:
            query_builder = query_builder.select("*")

        # Add WHERE condition for key IN clause
        where_condition = psql.SQL("{} IN ({})").format(
            psql.Identifier(key_column),
            psql.SQL(", ").join(psql.Literal(value) for value in key_values),
        )
        query_builder = query_builder.where(where_condition)

        return query_builder

    def create_text_index(
        self,
        index_name: str,
        column: str,
        tokenizer: Optional[TokenizerType] = None,
        tokenizer_params: Optional[Dict[str, Union[str, int, bool]]] = None,
        filter_params: Optional[
            "OrderedDict[TextFilterType, Union[str, int, bool, List[str], Dict[PinyinFilterParamType, Union[int, bool]]]]"
        ] = None,
    ) -> Self:
        """
        Create a text index for a column.

        Args:
            index_name (str): Name of the index.
            column (str): Name of the column to index.
            tokenizer (Optional[TokenizerType]): Tokenizer to use. Available options are "jieba", "ik", "icu", "whitespace", "standard", "simple", "keyword", "ngram", "pinyin". Defaults to "jieba".
            tokenizer_params (Optional[Dict]): Tokenizer parameters. Defaults to None.
            filter_params (Optional[OrderedDict]): Filter parameters. Defaults to None.
                Available filter param types are: "lowercase", "stop", "stemmer", "length", "removepunct", "pinyin".
        """
        sql = psql.SQL(
            "CREATE INDEX IF NOT EXISTS {} ON {} USING FULLTEXT ({})"
        ).format(
            psql.Identifier(index_name),
            psql.Identifier(self._name),
            psql.Identifier(column),
        )

        storage_parameter: list[psql.Composable] = []
        if tokenizer:
            storage_parameter.append(
                psql.SQL("tokenizer = {}").format(psql.Literal(tokenizer))
            )
        analyzer_params = build_analyzer_params_sql(
            tokenizer, tokenizer_params, filter_params
        )
        if analyzer_params:
            storage_parameter.append(
                psql.SQL("analyzer_params = {}").format(analyzer_params)
            )

        if len(storage_parameter) > 0:
            sql += (
                psql.SQL(" WITH (")
                + psql.SQL(", ").join(storage_parameter)
                + psql.SQL(")")
            )

        sql += psql.SQL(";")
        self._db.execute(sql)

        return self

    def set_text_index(
        self,
        index_name: str,
        tokenizer: TokenizerType,
        tokenizer_params: Optional[Dict[str, Union[str, int, bool]]] = None,
        filter_params: Optional[
            "OrderedDict[TextFilterType, Union[str, int, bool, List[str], Dict[PinyinFilterParamType, Union[int, bool]]]]"
        ] = None,
    ) -> Self:
        """
        Adjust a text index.

        Args:
            index_name (str): Name of the index.
            tokenizer (Optional[TokenizerType]): Tokenizer to use. Available options are "jieba", "ik", "icu", "whitespace", "standard", "simple", "keyword", "ngram", "pinyin". Defaults to "jieba".
            tokenizer_params (Optional[Dict]): Tokenizer parameters. Defaults to None.
            filter_params (Optional[OrderedDict]): Filter parameters. Defaults to None.
                Available filter param types are: "lowercase", "stop", "stemmer", "length", "removepunct", "pinyin".
        """

        storage_parameter: list[psql.Composable] = []
        storage_parameter.append(
            psql.SQL("tokenizer = {}").format(psql.Literal(tokenizer))
        )
        analyzer_params = build_analyzer_params_sql(
            tokenizer, tokenizer_params, filter_params
        )
        if analyzer_params:
            storage_parameter.append(
                psql.SQL("analyzer_params = {}").format(analyzer_params)
            )

        sql = psql.SQL("ALTER INDEX {} SET ({});").format(
            psql.Identifier(index_name), psql.SQL(", ").join(storage_parameter)
        )
        self._db.execute(sql)

        return self

    def reset_text_index(
        self, index_name: str, only_reset_analyzer_params: bool = False
    ) -> Self:
        """
        Reset a text index to default settings.

        Args:
            index_name (str): Name of the index.
            only_reset_analyzer_params (bool): Whether to only reset the analyzer parameters. Defaults to False.
                If True, only the analyzer parameters will be reset according to the tokenizer type.
        """
        if only_reset_analyzer_params:
            sql = psql.SQL("ALTER INDEX {} RESET (analyzer_params);").format(
                psql.Identifier(index_name)
            )
        else:
            sql = psql.SQL("ALTER INDEX {} RESET (tokenizer);").format(
                psql.Identifier(index_name)
            )
        self._db.execute(sql)

        return self

    def drop_text_index(self, index_name: str) -> Self:
        """
        Drop a text index.

        Args:
            index_name (str): Name of the index.
        """
        sql = psql.SQL("DROP INDEX IF EXISTS {};").format(psql.Identifier(index_name))
        self._db.execute(sql)

        return self

    def get_index_properties(
        self,
        return_index_id: bool = True,
        return_table_namespace: bool = True,
        return_table_name: bool = True,
        return_index_name: bool = True,
        return_property_key: bool = True,
        return_property_value: bool = True,
    ) -> List[Tuple[Any, ...]]:
        sql = psql.SQL("SELECT ")
        select_list: list[psql.SQL] = []
        if return_index_id:
            select_list.append(psql.SQL("index_id"))
        if return_table_namespace:
            select_list.append(psql.SQL("table_namespace"))
        if return_table_name:
            select_list.append(psql.SQL("table_name"))
        if return_index_name:
            select_list.append(psql.SQL("index_name"))
        if return_property_key:
            select_list.append(psql.SQL("property_key"))
        if return_property_value:
            select_list.append(psql.SQL("property_value"))
        sql += psql.SQL(", ").join(select_list)
        sql += psql.SQL(" FROM hologres.hg_index_properties;")
        return self._db.fetchall(sql)

    def show_tokenize_effect(
        self,
        column: Optional[LiteralString] = None,
        text: Optional[str] = None,
        tokenizer: TokenizerType = "jieba",
        tokenizer_params: Optional[Dict[str, Union[str, int, bool]]] = None,
        filter_params: Optional[
            "OrderedDict[TextFilterType, Union[str, int, bool, List[str], Dict[PinyinFilterParamType, Union[int, bool]]]]"
        ] = None,
    ) -> Optional[List[str]]:
        """
        Show the tokenize effect of a text. Column and text are mutually exclusive.

        Args:
            column (str): Column to tokenize.
            text (str): Text to tokenize.
            tokenizer (Optional[TokenizerType]): Tokenizer to use. Available options are "jieba", "ik", "icu", "whitespace", "standard", "simple", "keyword", "ngram", "pinyin". Defaults to "jieba".
            tokenizer_params (Optional[Dict]): Tokenizer parameters. Defaults to None.
            filter_params (Optional[OrderedDict]): Filter parameters. Defaults to None.
                Available filter param types are: "lowercase", "stop", "stemmer", "length", "removepunct", "pinyin".

        Returns:
            Optional[List[str]]: List of tokens.
        """
        tokenize_clause = build_tokenize_sql(
            column, text, tokenizer, tokenizer_params, filter_params
        )
        sql = psql.SQL("SELECT ") + tokenize_clause + psql.SQL(";")
        res = self._db.fetchone(sql)
        if res:
            return res[0]
        else:
            return None

    def search_text(
        self,
        column: LiteralString,
        expression: str,
        min_threshold: float = 0,
        return_score: bool = True,
        return_all_columns: bool = False,
        return_score_name: str = "text_search",
        mode: Optional[TextSearchModeType] = None,
        operator: Optional[TextSearchOperatorType] = None,
        tokenizer: Optional[TokenizerType] = None,
        tokenizer_params: Optional[Dict[str, Union[str, int, bool]]] = None,
        filter_params: Optional[
            "OrderedDict[TextFilterType, Union[str, int, bool, List[str], Dict[PinyinFilterParamType, Union[int, bool]]]]"
        ] = None,
        **kwargs,
    ) -> QueryBuilder:
        """
        Search text in a column.

        Args:
            column (str): Column to search.
            expression (str): Text to search for.
            min_threshold (float): Minimum score threshold. Only results with score > min_score (exclusive) will be returned. Defaults to 0.
            return_score (bool): Whether to return the score of the match. Defaults to True.
            return_all_columns (bool): Whether to return all columns. Defaults to False.
            return_score_name (str): Name of the score column to return. Defaults to "text_search"
            mode (Optional[TextSearchModeType]): Text search mode. Available options are "match", "phrase", "natural_language", "term". Defaults to "match".
            operator (Optional[TextSearchOperatorType]): Text search operator. Available options are "AND", "OR".
            tokenizer (Optional[TokenizerType]): Tokenizer to use. Available options are "jieba", "ik", "icu", "whitespace", "standard", "simple", "keyword", "ngram", "pinyin". Defaults to "jieba".
            tokenizer_params (Optional[Dict]): Tokenizer parameters. Defaults to None.
            filter_params (Optional[OrderedDict]): Filter parameters. Defaults to None.
                Available filter param types are: "lowercase", "stop", "stemmer", "length", "removepunct", "pinyin".
            **kwargs: Additional keyword arguments for the text search, such as "slop".
        """

        text_search_clause = build_text_search_sql(
            column,
            expression,
            mode,
            operator,
            tokenizer,
            tokenizer_params,
            filter_params,
            **kwargs,
        )
        query_builder = QueryBuilder(self._db, self._name, self._alias)
        if return_all_columns:
            query_builder = query_builder.select("*")
        elif return_score:
            query_builder = query_builder.select(
                (text_search_clause, return_score_name)
            )
        query_builder = query_builder.where(
            psql.SQL("{} > {}").format(text_search_clause, min_threshold)
        )

        return query_builder
