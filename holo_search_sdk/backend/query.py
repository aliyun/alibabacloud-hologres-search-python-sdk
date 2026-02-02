"""
Query module for Holo Search SDK.

Provides query builder classes for different types of searches.
"""

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

from psycopg import sql as psql
from typing_extensions import LiteralString

if TYPE_CHECKING:
    from .table import HoloTable

from ..exceptions import SqlError
from ..types import (
    PinyinFilterParamType,
    TextFilterType,
    TextSearchModeType,
    TextSearchOperatorType,
    TokenizerType,
)
from .connection import HoloConnect
from .filter import FilterExpression, LogicalOperator
from .utils.sql_utils import build_text_search_sql, build_tokenize_sql


class QueryBuilder:
    """
    Base query builder class for different types of searches.
    """

    def __init__(
        self,
        connection: HoloConnect,
        table_name: Optional[str] = None,
        table_alias: Optional[str] = None,
    ):
        """
        Initialize base query.

        Args:
            connection: Database connection
            table_name: Name of the primary table
            table_alias: Optional alias for the primary table
        """
        self._connection: HoloConnect = connection
        self._table_name: Optional[str] = table_name
        self._table_alias: Optional[str] = table_alias
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._filters: List[Tuple[LogicalOperator, psql.Composable]] = []
        self._select_fields: list[Tuple[psql.Composable, Optional[psql.Composable]]] = (
            []
        )
        self._order_by: Optional[psql.Composable] = None
        self._group_by: Optional[psql.Composable] = None
        self._sort_order: str = "desc"
        self._distance_column: Optional[str] = None
        self._distance_filter: Optional[psql.Composable] = None
        self._joins: List[Tuple[LiteralString, str, psql.Composable, Optional[str]]] = (
            []
        )

        self._res_columns: Optional[List[str]] = None

    def limit(self, count: int) -> "QueryBuilder":
        """
        Limit the number of results.

        Args:
            count: Maximum number of results

        Returns:
            Self for method chaining
        """
        self._limit = count
        return self

    def offset(self, count: int) -> "QueryBuilder":
        """
        Skip a number of results.

        Args:
            count: Number of results to skip

        Returns:
            Self for method chaining
        """
        self._offset = count
        return self

    def where(
        self, filter: Union[LiteralString, psql.Composable, FilterExpression]
    ) -> "QueryBuilder":
        """
        Add filter conditions. Can accept simple SQL conditions or complex FilterExpression objects.

        Args:
            filter: Filter condition - can be a string, SQL composable, or FilterExpression

        Returns:
            Self for method chaining
        """
        return self.and_where(filter)

    def and_where(
        self, filter: Union[LiteralString, psql.Composable, FilterExpression]
    ) -> "QueryBuilder":
        """
        Add filter conditions and combine it with existing filter conditions using "AND".
        Can accept simple SQL conditions or complex FilterExpression objects.

        Args:
            filter: Filter condition - can be a string, SQL composable, or FilterExpression

        Returns:
            Self for method chaining
        """
        if isinstance(filter, FilterExpression):
            self._filters.append((LogicalOperator.AND, filter.to_sql()))
        elif isinstance(filter, psql.Composable):
            self._filters.append((LogicalOperator.AND, filter))
        else:
            self._filters.append((LogicalOperator.AND, psql.SQL(filter)))
        return self

    def or_where(
        self, filter: Union[LiteralString, psql.Composable, FilterExpression]
    ) -> "QueryBuilder":
        """
        Add filter conditions and combine it with existing filter conditions using "OR".
        Can accept simple SQL conditions or complex FilterExpression objects.

        Args:
            filter: Filter condition - can be a string, SQL composable, or FilterExpression

        Returns:
            Self for method chaining
        """
        if isinstance(filter, FilterExpression):
            self._filters.append((LogicalOperator.OR, filter.to_sql()))
        elif isinstance(filter, psql.Composable):
            self._filters.append((LogicalOperator.OR, filter))
        else:
            self._filters.append((LogicalOperator.OR, psql.SQL(filter)))
        return self

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
        Select specific fields to return.

        Args:
            columns: Column name or list of column names or dictionary mapping column names to aliases to return.

        Returns:
            Self for method chaining
        """
        if isinstance(columns, list):
            for column in columns:
                if isinstance(column, Tuple):
                    name = (
                        psql.SQL(column[0]) if isinstance(column[0], str) else column[0]
                    )
                    alias = (
                        psql.Identifier(column[1])
                        if isinstance(column[1], str)
                        else column[1]
                    )
                    self._select_fields.append((name, alias))
                elif isinstance(column, psql.Composable):
                    self._select_fields.append((column, None))
                else:
                    self._select_fields.append((psql.SQL(column), None))
        elif isinstance(columns, Dict):
            for column, alias in columns.items():
                transferred_alias = (
                    alias
                    if alias is None or isinstance(alias, psql.Composable)
                    else psql.Identifier(alias)
                )
                self._select_fields.append((psql.SQL(column), transferred_alias))
        elif isinstance(columns, Tuple):
            name = psql.SQL(columns[0]) if isinstance(columns[0], str) else columns[0]
            alias = (
                psql.Identifier(columns[1])
                if isinstance(columns[1], str)
                else columns[1]
            )
            self._select_fields.append((name, alias))
        elif isinstance(columns, psql.Composable):
            self._select_fields.append((columns, None))
        else:
            self._select_fields.append((psql.SQL(columns), None))
        return self

    def order_by(
        self, column: Union[LiteralString, psql.Composable], order: str = "desc"
    ) -> "QueryBuilder":
        """
        Order results by a column.

        Args:
            column: Column name to order by
            order: Sort order ("asc" or "desc")

        Returns:
            Self for method chaining
        """
        if isinstance(column, psql.Composable):
            self._order_by = column
        else:
            self._order_by = psql.SQL(column)
        self._sort_order = order
        return self

    def group_by(self, column: Union[LiteralString, psql.Composable]) -> "QueryBuilder":
        """
        Group results by a column.

        Args:
            column: Column name to group by

        Returns:
            Self for method chaining
        """
        if isinstance(column, psql.Composable):
            self._group_by = column
        else:
            self._group_by = psql.SQL(column)
        return self

    def set_distance_column(self, column: str) -> "QueryBuilder":
        """
        Set the column to use for distance calculation.

        Args:
            column: Column name for distance

        Returns:
            Self for method chaining
        """
        self._distance_column = column
        return self

    def min_distance(self, val: float) -> "QueryBuilder":
        """
        Set the minimum distance filter for vector search results.
        Only results with distance >= val will be returned.

        Args:
            val: Minimum distance value

        Returns:
            Self for method chaining
        """
        self._distance_filter = psql.SQL(">= {}").format(val)
        return self

    def max_distance(self, val: float) -> "QueryBuilder":
        """
        Set the maximum distance filter for vector search results.
        Only results with distance <= val will be returned.

        Args:
            val: Maximum distance value

        Returns:
            Self for method chaining
        """
        self._distance_filter = psql.SQL("<= {}").format(val)
        return self

    def select_tokenize(
        self,
        column: Optional[LiteralString] = None,
        text: Optional[str] = None,
        output_name: Optional[str] = None,
        tokenizer: Optional[TokenizerType] = None,
        tokenizer_params: Optional[Dict[str, Union[str, int, bool]]] = None,
        filter_params: Optional[
            "OrderedDict[TextFilterType, Union[str, int, bool, List[str], Dict[PinyinFilterParamType, Union[int, bool]]]]"
        ] = None,
    ) -> "QueryBuilder":
        """
        Show the tokenize effect of a text. Column and text are mutually exclusive.

        Args:
            column (Optional[str]): Column to tokenize.
            text (Optional[str]): Text to tokenize.
            output_name (Optional[str]): Name of the output column.
            tokenizer (Optional[TokenizerType]): Tokenizer to use. Available options are "jieba", "ik", "icu", "whitespace", "standard", "simple", "keyword", "ngram", "pinyin". Defaults to "jieba".
            tokenizer_params (Optional[Dict]): Tokenizer parameters. Defaults to None.
            filter_params (Optional[OrderedDict]): Filter parameters. Defaults to None.
                Available filter param types are: "lowercase", "stop", "stemmer", "length", "removepunct", "pinyin".

        Returns:
            Self for method chaining
        """
        tokenize_clause = build_tokenize_sql(
            column, text, tokenizer, tokenizer_params, filter_params
        )
        self._select_fields.append(
            (tokenize_clause, psql.Identifier(output_name) if output_name else None)
        )
        return self

    def select_text_search(
        self,
        column: LiteralString,
        expression: str,
        output_name: Optional[str] = None,
        mode: Optional[TextSearchModeType] = None,
        operator: Optional[TextSearchOperatorType] = None,
        tokenizer: Optional[TokenizerType] = None,
        tokenizer_params: Optional[Dict[str, Union[str, int, bool]]] = None,
        filter_params: Optional[
            "OrderedDict[TextFilterType, Union[str, int, bool, List[str], Dict[PinyinFilterParamType, Union[int, bool]]]]"
        ] = None,
        **kwargs,
    ) -> "QueryBuilder":
        """
        Search text in a column.

        Args:
            column (str): Column to search.
            expression (str): Text to search for.
            output_name (Optional[str]): Name of the output column.
            mode (Optional[TextSearchModeType]): Text search mode. Available options are "match", "phrase", "natural_language", "term". Defaults to "match".
            operator (Optional[TextSearchOperatorType]): Text search operator. Available options are "AND", "OR".
            tokenizer (Optional[TokenizerType]): Tokenizer to use. Available options are "jieba", "ik", "icu", "whitespace", "standard", "simple", "keyword", "ngram", "pinyin". Defaults to "jieba".
            tokenizer_params (Optional[Dict]): Tokenizer parameters. Defaults to None.
            filter_params (Optional[OrderedDict]): Filter parameters. Defaults to None.
                Available filter param types are: "lowercase", "stop", "stemmer", "length", "removepunct", "pinyin".
            **kwargs: Additional keyword arguments for the text search, such as "slop".

        Returns:
            Self for method chaining
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
        self._select_fields.append(
            (text_search_clause, psql.Identifier(output_name) if output_name else None)
        )
        return self

    def where_text_search(
        self,
        column: LiteralString,
        expression: str,
        min_threshold: float,
        mode: Optional[TextSearchModeType] = None,
        operator: Optional[TextSearchOperatorType] = None,
        tokenizer: Optional[TokenizerType] = None,
        tokenizer_params: Optional[Dict[str, Union[str, int, bool]]] = None,
        filter_params: Optional[
            "OrderedDict[TextFilterType, Union[str, int, bool, List[str], Dict[PinyinFilterParamType, Union[int, bool]]]]"
        ] = None,
        **kwargs,
    ) -> "QueryBuilder":
        """
        Search text in a column and filter rows based on the search results.

        Args:
            column (str): Column to search.
            expression (str): Text to search for.
            min_threshold (float): Minimum score threshold. Only results with score > min_score (exclusive) will be returned.
            mode (Optional[TextSearchModeType]): Text search mode. Available options are "match", "phrase", "natural_language", "term". Defaults to "match".
            operator (Optional[TextSearchOperatorType]): Text search operator. Available options are "AND", "OR".
            tokenizer (Optional[TokenizerType]): Tokenizer to use. Available options are "jieba", "ik", "icu", "whitespace", "standard", "simple", "keyword", "ngram", "pinyin". Defaults to "jieba".
            tokenizer_params (Optional[Dict]): Tokenizer parameters. Defaults to None.
            filter_params (Optional[OrderedDict]): Filter parameters. Defaults to None.
                Available filter param types are: "lowercase", "stop", "stemmer", "length", "removepunct", "pinyin".
            **kwargs: Additional keyword arguments for the text search, such as "slop".

        Returns:
            Self for method chaining
        """
        return self.and_where_text_search(
            column,
            expression,
            min_threshold,
            mode,
            operator,
            tokenizer,
            tokenizer_params,
            filter_params,
            **kwargs,
        )

    def and_where_text_search(
        self,
        column: LiteralString,
        expression: str,
        min_threshold: float,
        mode: Optional[TextSearchModeType] = None,
        operator: Optional[TextSearchOperatorType] = None,
        tokenizer: Optional[TokenizerType] = None,
        tokenizer_params: Optional[Dict[str, Union[str, int, bool]]] = None,
        filter_params: Optional[
            "OrderedDict[TextFilterType, Union[str, int, bool, List[str], Dict[PinyinFilterParamType, Union[int, bool]]]]"
        ] = None,
        **kwargs,
    ) -> "QueryBuilder":
        """
        Search text in a column and filter rows based on the search results in an "AND" condition.

        Args:
            column (str): Column to search.
            expression (str): Text to search for.
            min_threshold (float): Minimum score threshold. Only results with score > min_score (exclusive) will be returned.
            mode (Optional[TextSearchModeType]): Text search mode. Available options are "match", "phrase", "natural_language", "term". Defaults to "match".
            operator (Optional[TextSearchOperatorType]): Text search operator. Available options are "AND", "OR".
            tokenizer (Optional[TokenizerType]): Tokenizer to use. Available options are "jieba", "ik", "icu", "whitespace", "standard", "simple", "keyword", "simple", "keyword", "ngram", "pinyin". Defaults to "jieba".
            tokenizer_params (Optional[Dict]): Tokenizer parameters. Defaults to None.
            filter_params (Optional[OrderedDict]): Filter parameters. Defaults to None.
                Available filter param types are: "lowercase", "stop", "stemmer", "length", "removepunct", "pinyin".
            **kwargs: Additional keyword arguments for the text search, such as "slop".

        Returns:
            Self for method chaining
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
        self._filters.append(
            (
                LogicalOperator.AND,
                psql.SQL("{} > {}").format(text_search_clause, min_threshold),
            )
        )
        return self

    def or_where_text_search(
        self,
        column: LiteralString,
        expression: str,
        min_threshold: float,
        mode: Optional[TextSearchModeType] = None,
        operator: Optional[TextSearchOperatorType] = None,
        tokenizer: Optional[TokenizerType] = None,
        tokenizer_params: Optional[Dict[str, Union[str, int, bool]]] = None,
        filter_params: Optional[
            "OrderedDict[TextFilterType, Union[str, int, bool, List[str], Dict[PinyinFilterParamType, Union[int, bool]]]]"
        ] = None,
        **kwargs,
    ) -> "QueryBuilder":
        """
        Search text in a column and filter rows based on the search results in an "OR" condition.

        Args:
            column (str): Column to search.
            expression (str): Text to search for.
            min_threshold (float): Minimum score threshold. Only results with score > min_score (exclusive) will be returned.
            mode (Optional[TextSearchModeType]): Text search mode. Available options are "match", "phrase", "natural_language", "term". Defaults to "match".
            operator (Optional[TextSearchOperatorType]): Text search operator. Available options are "AND", "OR".
            tokenizer (Optional[TokenizerType]): Tokenizer to use. Available options are "jieba", "ik", "icu", "whitespace", "standard", "simple", "keyword", "ngram", "pinyin". Defaults to "jieba".
            tokenizer_params (Optional[Dict]): Tokenizer parameters. Defaults to None.
            filter_params (Optional[OrderedDict]): Filter parameters. Defaults to None.
                Available filter param types are: "lowercase", "stop", "stemmer", "length", "removepunct", "pinyin".
            **kwargs: Additional keyword arguments for the text search, such as "slop".

        Returns:
            Self for method chaining
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
        self._filters.append(
            (
                LogicalOperator.OR,
                psql.SQL("{} > {}").format(text_search_clause, min_threshold),
            )
        )
        return self

    def join(
        self,
        table: Union[str, "HoloTable"],
        condition: Union[LiteralString, psql.Composable, FilterExpression],
        table_alias: Optional[str] = None,
        join_type: LiteralString = "INNER",
    ) -> "QueryBuilder":
        """
        Add a JOIN clause to the query.

        Args:
            table (Union[str, HoloTable]): Name of the table to join
            condition (Union[LiteralString, psql.Composable, FilterExpression]): JOIN condition
            table_alias (Optional[str]): Optional alias for the joined table
            join_type (LiteralString): Type of join ("INNER", "LEFT", "RIGHT", "FULL", "CROSS"). Defaults to "INNER"

        Returns:
            Self for method chaining
        """
        from .table import HoloTable

        _table_name = table.get_name() if isinstance(table, HoloTable) else table
        _table_alias = (
            table.get_alias()
            if table_alias is None and isinstance(table, HoloTable)
            else table_alias
        )
        if isinstance(condition, psql.Composable):
            self._joins.append((join_type, _table_name, condition, _table_alias))
        elif isinstance(condition, FilterExpression):
            self._joins.append(
                (join_type, _table_name, condition.to_sql(), _table_alias)
            )
        else:
            self._joins.append(
                (join_type, _table_name, psql.SQL(condition), _table_alias)
            )
        return self

    def inner_join(
        self,
        table: Union[str, "HoloTable"],
        condition: Union[LiteralString, psql.Composable, FilterExpression],
        table_alias: Optional[str] = None,
    ) -> "QueryBuilder":
        """
        Add an INNER JOIN clause to the query.

        Args:
            table (Union[str, HoloTable]): Name of the table to join
            condition (Union[LiteralString, psql.Composable, FilterExpression]): JOIN condition
            table_alias (Optional[str]): Optional alias for the joined table

        Returns:
            Self for method chaining
        """
        return self.join(table, condition, table_alias, "INNER")

    def left_join(
        self,
        table: Union[str, "HoloTable"],
        condition: Union[LiteralString, psql.Composable, FilterExpression],
        table_alias: Optional[str] = None,
    ) -> "QueryBuilder":
        """
        Add a LEFT JOIN clause to the query.

        Args:
            table (Union[str, HoloTable]): Name of the table to join
            condition (Union[LiteralString, psql.Composable, FilterExpression]): JOIN condition
            table_alias (Optional[str]): Optional alias for the joined table

        Returns:
            Self for method chaining
        """
        return self.join(table, condition, table_alias, "LEFT")

    def right_join(
        self,
        table: Union[str, "HoloTable"],
        condition: Union[LiteralString, psql.Composable, FilterExpression],
        table_alias: Optional[str] = None,
    ) -> "QueryBuilder":
        """
        Add a RIGHT JOIN clause to the query.

        Args:
            table (Union[str, HoloTable]): Name of the table to join
            condition (Union[LiteralString, psql.Composable, FilterExpression]): JOIN condition
            table_alias (Optional[str]): Optional alias for the joined table

        Returns:
            Self for method chaining
        """
        return self.join(table, condition, table_alias, "RIGHT")

    def full_join(
        self,
        table: Union[str, "HoloTable"],
        condition: Union[LiteralString, psql.Composable, FilterExpression],
        table_alias: Optional[str] = None,
    ) -> "QueryBuilder":
        """
        Add a FULL OUTER JOIN clause to the query.

        Args:
            table (Union[str, HoloTable]): Name of the table to join
            condition (Union[LiteralString, psql.Composable, FilterExpression]): JOIN condition
            table_alias (Optional[str]): Optional alias for the joined table

        Returns:
            Self for method chaining
        """
        return self.join(table, condition, table_alias, "FULL")

    def cross_join(
        self,
        table: Union[str, "HoloTable"],
        condition: Union[LiteralString, psql.Composable, FilterExpression],
        table_alias: Optional[str] = None,
    ) -> "QueryBuilder":
        """
        Add a CROSS JOIN clause to the query.

        Args:
            table (Union[str, HoloTable]): Name of the table to join
            condition (Union[LiteralString, psql.Composable, FilterExpression]): JOIN condition
            table_alias (Optional[str]): Optional alias for the joined table

        Returns:
            Self for method chaining
        """
        return self.join(table, condition, table_alias, "CROSS")

    def set_table_alias(self, alias: str) -> "QueryBuilder":
        """
        Set the table alias.

        Args:
            alias (str): Table alias

        Returns:
            Self for method chaining
        """
        self._table_alias = alias
        return self

    def _generate_sql(self):
        """
        Generate SQL query.
        """
        if len(self._select_fields) == 0:
            raise SqlError("Select fields is not set")
        select_list: list[psql.Composable] = []
        for column, alias in self._select_fields:
            if alias:
                select_list.append(column + psql.SQL(" AS ") + alias)
            else:
                select_list.append(column)
        sql = psql.Composed([psql.SQL("SELECT "), psql.SQL(", ").join(select_list)])

        # Build FROM clause with optional table alias
        if self._table_name is not None:
            if self._table_alias:
                sql += psql.SQL(" FROM {} {}").format(
                    psql.Identifier(self._table_name),
                    psql.Identifier(self._table_alias),
                )
            else:
                sql += psql.SQL(" FROM {}").format(psql.Identifier(self._table_name))

        # Add JOIN clauses
        for join_type, table_name, on_condition, table_alias in self._joins:
            sql += psql.SQL(" {} JOIN {}").format(
                psql.SQL(join_type), psql.Identifier(table_name)
            )
            if table_alias:
                sql += psql.SQL(" {}").format(psql.Identifier(table_alias))
            sql += psql.SQL(" ON ") + on_condition

        if len(self._filters) > 0:
            for i in range(len(self._filters)):
                if i == 0:
                    sql += psql.SQL(" WHERE ")
                else:
                    sql += psql.SQL(" {} ").format(psql.SQL(self._filters[i][0].value))
                filter_item = self._filters[i][1]
                sql += filter_item

        if self._group_by is not None:
            sql += psql.SQL(" GROUP BY ") + self._group_by
        if self._order_by is not None:
            sql += psql.SQL(" ORDER BY ") + self._order_by
            if self._sort_order.upper() == "DESC":
                sql += psql.SQL(" DESC")
            else:
                sql += psql.SQL(" ASC")
        if self._limit is not None:
            sql += psql.SQL(" LIMIT {}").format(self._limit)
        if self._offset is not None:
            sql += psql.SQL(" OFFSET {}").format(self._offset)

        if self._distance_filter is not None:
            if self._distance_column is None:
                raise SqlError("Distance column is required when using distance filter")
            # Wrap the current query in a subquery and apply distance filter
            sql = psql.SQL("SELECT * FROM ({}) WHERE {} {}").format(
                sql, psql.Identifier(self._distance_column), self._distance_filter
            )

        sql += psql.SQL(";")
        return sql

    def to_string(self) -> str:
        """
        Generate SQL query and return as string.
        """
        return self._generate_sql().as_string()

    def submit(self):
        """Execute the query without return results."""
        sql = self._generate_sql()
        self._connection.execute(sql)
        self._res_columns = self._connection.get_result_columns()

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        """Execute the query and return one result."""
        sql = self._generate_sql()
        res = self._connection.fetchone(sql)
        self._res_columns = self._connection.get_result_columns()
        return res

    def fetchall(self) -> List[Tuple[Any, ...]]:
        """Execute the query and return all results."""
        sql = self._generate_sql()
        res = self._connection.fetchall(sql)
        self._res_columns = self._connection.get_result_columns()
        return res

    def fetchmany(self, size: int = 0) -> List[Tuple[Any, ...]]:
        """
        Execute the query and return a number of results.

        Args:
            size: Number of results to return.
        """
        sql = self._generate_sql()
        res = self._connection.fetchmany(sql, params=None, size=size)
        self._res_columns = self._connection.get_result_columns()
        return res

    def explain(self) -> List[Tuple[Any, ...]]:
        """Execute the query and return explain results."""
        sql = psql.SQL("EXPLAIN ") + self._generate_sql()
        return self._connection.fetchall(sql)

    def explain_analyze(self) -> List[Tuple[Any, ...]]:
        """Execute the query and return explain analyze results."""
        sql = psql.SQL("EXPLAIN ANALYZE ") + self._generate_sql()
        return self._connection.fetchall(sql)

    def get_result_columns(self) -> Optional[List[str]]:
        """Get the result columns"""
        return self._res_columns
