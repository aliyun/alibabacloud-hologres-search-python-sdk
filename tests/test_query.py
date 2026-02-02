"""
Tests for QueryBuilder class in Holo Search SDK.

This module contains comprehensive tests for QueryBuilder functionality including
query construction, method chaining, and SQL generation.
"""

from unittest.mock import Mock, patch

import pytest
from psycopg import sql as psql

from holo_search_sdk.backend.connection import HoloConnect
from holo_search_sdk.backend.filter import LogicalOperator
from holo_search_sdk.backend.query import QueryBuilder
from holo_search_sdk.exceptions import SqlError


class TestQueryBuilder:
    """Test cases for the QueryBuilder class."""

    def test_query_builder_initialization(self):
        """Test QueryBuilder initialization."""
        mock_connection = Mock(spec=HoloConnect)
        table_name = "test_table"

        query_builder = QueryBuilder(mock_connection, table_name)

        assert query_builder._connection is mock_connection
        assert query_builder._table_name == table_name
        assert query_builder._limit is None
        assert query_builder._offset is None
        assert query_builder._filters == []
        assert query_builder._select_fields == []
        assert query_builder._order_by is None
        assert query_builder._group_by is None
        assert query_builder._sort_order == "desc"

    def test_limit_method(self):
        """Test limit method."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.limit(10)

        assert result is query_builder  # Method chaining
        assert query_builder._limit == 10

    def test_offset_method(self):
        """Test offset method."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.offset(5)

        assert result is query_builder  # Method chaining
        assert query_builder._offset == 5

    def test_where_method(self):
        """Test where method."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.where("id > 10")

        assert result is query_builder  # Method chaining
        assert len(query_builder._filters) == 1
        assert query_builder._filters[0][1].as_string() == "id > 10"

    def test_where_method_multiple_filters(self):
        """Test where method with multiple filters."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        query_builder.where("id > 10").where("name = 'test'")

        assert len(query_builder._filters) == 2
        expected_filters = [
            "id > 10",
            "name = 'test'",
        ]
        assert all(
            any(
                f in filter_tuple[1].as_string()
                for filter_tuple in query_builder._filters
            )
            for f in expected_filters
        )

    def test_select_method_with_string(self):
        """Test select method with string column."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.select("id")

        assert result is query_builder  # Method chaining
        assert len(query_builder._select_fields) == 1
        assert query_builder._select_fields[0] == (psql.SQL("id"), None)

    def test_select_method_with_list(self):
        """Test select method with list of columns."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.select(["id", "name", "email"])

        assert result is query_builder  # Method chaining
        assert len(query_builder._select_fields) == 3
        expected_fields = [
            (psql.SQL("id"), None),
            (psql.SQL("name"), None),
            (psql.SQL("email"), None),
        ]
        assert query_builder._select_fields == expected_fields

    def test_select_method_with_dict(self):
        """Test select method with dictionary (column aliases)."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.select({"id": "user_id", "name": "user_name"})

        assert result is query_builder  # Method chaining
        assert len(query_builder._select_fields) == 2
        # Check that fields contain SQL objects with correct aliases
        # Note: psql.Identifier wraps identifiers in quotes, so as_string() returns quoted strings
        field_strs = [
            (f[0].as_string(), f[1].as_string() if f[1] else None)
            for f in query_builder._select_fields
        ]
        assert ("id", '"user_id"') in field_strs and (
            "name",
            '"user_name"',
        ) in field_strs

    def test_select_method_multiple_calls(self):
        """Test select method with multiple calls."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        query_builder.select("id").select(["name", "email"]).select({"age": "user_age"})

        assert len(query_builder._select_fields) == 4
        # Check that all fields are present
        # Note: psql.Identifier wraps identifiers in quotes, so as_string() returns quoted strings
        field_strs = [
            (f[0].as_string(), f[1].as_string() if f[1] else None)
            for f in query_builder._select_fields
        ]
        assert ("id", None) in field_strs
        assert ("name", None) in field_strs
        assert ("email", None) in field_strs
        assert ("age", '"user_age"') in field_strs

    def test_order_by_method_default_desc(self):
        """Test order_by method with default desc order."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.order_by("created_at")

        assert result is query_builder  # Method chaining
        assert query_builder._order_by.as_string() == "created_at"
        assert query_builder._sort_order == "desc"

    def test_order_by_method_with_asc_order(self):
        """Test order_by method with asc order."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.order_by("name", "asc")

        assert result is query_builder  # Method chaining
        assert query_builder._order_by.as_string() == "name"
        assert query_builder._sort_order == "asc"

    def test_group_by_method(self):
        """Test group_by method."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.group_by("category")

        assert result is query_builder  # Method chaining
        assert query_builder._group_by.as_string() == "category"

    def test_generate_sql_simple_select(self):
        """Test SQL generation for simple select."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        query_builder.select(["id", "name"])
        sql = query_builder._generate_sql()
        assert sql.as_string() == 'SELECT id, name FROM "test_table";'

    def test_generate_sql_with_aliases(self):
        """Test SQL generation with column aliases."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        query_builder.select({"id": "user_id", "name": "user_name"})
        sql = query_builder._generate_sql()
        # Note: psql.Identifier wraps identifiers in quotes
        assert (
            sql.as_string()
            == 'SELECT id AS "user_id", name AS "user_name" FROM "test_table";'
        )

    def test_generate_sql_with_where_clause(self):
        """Test SQL generation with WHERE clause."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        query_builder.select(["id", "name"]).where("id > 10").where("status = 'active'")
        sql = query_builder._generate_sql()
        assert (
            sql.as_string()
            == "SELECT id, name FROM \"test_table\" WHERE id > 10 AND status = 'active';"
        )

    def test_generate_sql_with_group_by(self):
        """Test SQL generation with GROUP BY clause."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        query_builder.select(["category", "COUNT(*)"]).group_by("category")
        sql = query_builder._generate_sql()
        assert (
            sql.as_string()
            == 'SELECT category, COUNT(*) FROM "test_table" GROUP BY category;'
        )

    def test_generate_sql_with_order_by(self):
        """Test SQL generation with ORDER BY clause."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        query_builder.select(["id", "name"]).order_by("created_at", "desc")
        sql = query_builder._generate_sql()
        assert (
            sql.as_string()
            == 'SELECT id, name FROM "test_table" ORDER BY created_at DESC;'
        )

    def test_generate_sql_with_limit_and_offset(self):
        """Test SQL generation with LIMIT and OFFSET."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        query_builder.select(["id", "name"]).limit(10).offset(20)
        sql = query_builder._generate_sql()
        assert (
            sql.as_string() == 'SELECT id, name FROM "test_table" LIMIT 10 OFFSET 20;'
        )

    def test_set_distance_column(self):
        """Test set_distance_column method."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.set_distance_column("distance")

        assert result is query_builder  # Method chaining
        assert query_builder._distance_column == "distance"

    def test_order_by_method_invalid_order(self):
        """Test order_by method with invalid sort order defaults to desc."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        # Even with invalid order, it should still work (might default to desc)
        result = query_builder.order_by("created_at", "invalid")

        assert result is query_builder  # Method chaining
        assert query_builder._order_by.as_string() == "created_at"

    def test_select_method_with_empty_list(self):
        """Test select method with empty list."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.select([])

        assert result is query_builder  # Method chaining
        assert len(query_builder._select_fields) == 0

    def test_select_method_with_empty_dict(self):
        """Test select method with empty dictionary."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.select({})

        assert result is query_builder  # Method chaining
        assert len(query_builder._select_fields) == 0

    def test_where_method_with_empty_string(self):
        """Test where method with empty string."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.where("")

        assert result is query_builder  # Method chaining
        assert len(query_builder._filters) == 1

    def test_limit_method_with_zero(self):
        """Test limit method with zero."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.limit(0)

        assert result is query_builder  # Method chaining
        assert query_builder._limit == 0

    def test_offset_method_with_zero(self):
        """Test offset method with zero."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.offset(0)

        assert result is query_builder  # Method chaining
        assert query_builder._offset == 0

    def test_generate_sql_with_only_limit(self):
        """Test SQL generation with only LIMIT clause."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        query_builder.select("*").limit(5)
        sql = query_builder._generate_sql()
        assert sql.as_string() == 'SELECT * FROM "test_table" LIMIT 5;'

    def test_generate_sql_with_only_offset(self):
        """Test SQL generation with only OFFSET clause."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        query_builder.select("*").offset(10)
        sql = query_builder._generate_sql()
        assert sql.as_string() == 'SELECT * FROM "test_table" OFFSET 10;'

    def test_generate_sql_no_select_fields(self):
        """Test SQL generation without explicit select fields raises error."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        with pytest.raises(SqlError) as exc_info:
            _ = query_builder._generate_sql()

        assert "Select fields is not set" in str(exc_info.value)

    def test_method_chaining_comprehensive(self):
        """Test comprehensive method chaining."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = (
            query_builder.select(["id", "name"])
            .where("id > 0")
            .where("status = 'active'")
            .order_by("created_at", "desc")
            .limit(20)
            .offset(10)
            .group_by("category")
        )

        # All methods should return the same instance
        assert result is query_builder
        assert len(query_builder._select_fields) == 2
        assert len(query_builder._filters) == 2
        assert query_builder._limit == 20
        assert query_builder._offset == 10
        assert query_builder._order_by is not None
        assert query_builder._group_by is not None

    def test_select_with_special_characters(self):
        """Test select method with column names containing special characters."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.select(["user_id", "created_at", "updated_at"])

        assert result is query_builder
        assert len(query_builder._select_fields) == 3

    def test_where_with_complex_conditions(self):
        """Test where method with complex SQL conditions."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        query_builder.where("age BETWEEN 18 AND 65").where(
            "email LIKE '%@example.com'"
        ).where("status IN ('active', 'pending')")

        assert len(query_builder._filters) == 3

    def test_order_by_with_asc_order(self):
        """Test order_by method explicitly with asc order."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.order_by("price", "asc")

        assert result is query_builder
        assert query_builder._order_by.as_string() == "price"
        assert query_builder._sort_order == "asc"

    def test_generate_sql_with_group_by_and_order_by(self):
        """Test SQL generation with both GROUP BY and ORDER BY."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        query_builder.select(["category", "COUNT(*) as count"]).group_by(
            "category"
        ).order_by("count", "desc")

        sql = query_builder._generate_sql()
        sql_str = sql.as_string()

        assert "GROUP BY category" in sql_str
        assert "ORDER BY count DESC" in sql_str

    def test_min_distance(self):
        """Test min_distance method."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.min_distance(0.5)

        assert result is query_builder  # Method chaining
        assert query_builder._distance_filter is not None
        assert query_builder._distance_filter.as_string() == ">= 0.5"

    def test_max_distance(self):
        """Test max_distance method."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.max_distance(0.8)

        assert result is query_builder  # Method chaining
        assert query_builder._distance_filter is not None
        assert query_builder._distance_filter.as_string() == "<= 0.8"

    def test_generate_sql_complex_query(self):
        """Test SQL generation for complex query with all clauses."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "users")

        query_builder.select(
            {"id": "user_id", "name": "user_name", "email": None}
        ).where("age > 18").where("status = 'active'").group_by("department").order_by(
            "created_at", "asc"
        ).limit(
            50
        ).offset(
            100
        )

        sql = query_builder._generate_sql()
        # Note: psql.Identifier wraps identifiers in quotes
        assert (
            sql.as_string()
            == 'SELECT id AS "user_id", name AS "user_name", email FROM "users" WHERE age > 18 AND status = \'active\' GROUP BY department ORDER BY created_at ASC LIMIT 50 OFFSET 100;'
        )

    def test_generate_sql_no_select_fields_raises_error(self):
        """Test that SQL generation raises error when no select fields are set."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        with pytest.raises(SqlError) as exc_info:
            query_builder._generate_sql()

        assert "Select fields is not set" in str(exc_info.value)

    def test_submit_method(self):
        """Test submit method."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        query_builder.select(["id", "name"])
        query_builder.submit()

        mock_connection.execute.assert_called_once()
        call_args = mock_connection.execute.call_args[0]
        expected_sql = 'SELECT id, name FROM "test_table";'
        assert call_args[0].as_string() == expected_sql

    def test_fetchone_method(self):
        """Test fetchone method."""
        mock_connection = Mock(spec=HoloConnect)
        mock_connection.fetchone.return_value = (1, "test_name")
        query_builder = QueryBuilder(mock_connection, "test_table")

        query_builder.select(["id", "name"])
        _ = query_builder.fetchone()

        mock_connection.fetchone.assert_called_once()
        call_args = mock_connection.fetchone.call_args[0]
        expected_sql = 'SELECT id, name FROM "test_table";'
        assert call_args[0].as_string() == expected_sql

    def test_fetchall_method(self):
        """Test fetchall method."""
        mock_connection = Mock(spec=HoloConnect)
        mock_connection.fetchall.return_value = [(1, "test1"), (2, "test2")]
        query_builder = QueryBuilder(mock_connection, "test_table")

        query_builder.select(["id", "name"])
        _ = query_builder.fetchall()

        mock_connection.fetchall.assert_called_once()
        call_args = mock_connection.fetchall.call_args[0]
        expected_sql = 'SELECT id, name FROM "test_table";'
        assert call_args[0].as_string() == expected_sql

    def test_fetchmany_method_default_size(self):
        """Test fetchmany method with default size."""
        mock_connection = Mock(spec=HoloConnect)
        mock_connection.fetchmany.return_value = [(1, "test1"), (2, "test2")]
        query_builder = QueryBuilder(mock_connection, "test_table")

        query_builder.select(["id", "name"])
        result = query_builder.fetchmany()

        # Verify that fetchmany was called with correct parameters
        mock_connection.fetchmany.assert_called_once()
        call_args = mock_connection.fetchmany.call_args
        expected_sql = 'SELECT id, name FROM "test_table";'
        assert call_args[0][0].as_string() == expected_sql
        assert call_args[1]["params"] is None
        assert call_args[1]["size"] == 0
        assert result == [(1, "test1"), (2, "test2")]

    def test_fetchmany_method_with_size(self):
        """Test fetchmany method with specific size."""
        mock_connection = Mock(spec=HoloConnect)
        mock_connection.fetchmany.return_value = [(1, "test1")]
        query_builder = QueryBuilder(mock_connection, "test_table")

        query_builder.select(["id", "name"])
        result = query_builder.fetchmany(size=1)

        # Verify that fetchmany was called with correct parameters
        mock_connection.fetchmany.assert_called_once()
        call_args = mock_connection.fetchmany.call_args
        expected_sql = 'SELECT id, name FROM "test_table";'
        assert call_args[0][0].as_string() == expected_sql
        assert call_args[1]["params"] is None
        assert call_args[1]["size"] == 1
        assert result == [(1, "test1")]

    def test_method_chaining(self):
        """Test method chaining functionality."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        # Test that all methods return self for chaining
        result = (
            query_builder.select(["id", "name"])
            .where("id > 10")
            .order_by("name", "asc")
            .group_by("category")
            .limit(20)
            .offset(10)
        )

        assert result is query_builder
        assert len(query_builder._select_fields) == 2
        expected_fields = [(psql.SQL("id"), None), (psql.SQL("name"), None)]
        assert all(f in query_builder._select_fields for f in expected_fields)
        assert len(query_builder._filters) == 1
        assert query_builder._filters[0][1].as_string() == "id > 10"
        assert query_builder._order_by.as_string() == "name"
        assert query_builder._sort_order == "asc"
        assert query_builder._group_by.as_string() == "category"
        assert query_builder._limit == 20
        assert query_builder._offset == 10

    def test_limit_with_zero(self):
        """Test limit method with zero value."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.limit(0)

        assert result is query_builder
        assert query_builder._limit == 0

    def test_offset_with_zero(self):
        """Test offset method with zero value."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.offset(0)

        assert result is query_builder
        assert query_builder._offset == 0

    def test_select_empty_list(self):
        """Test select method with empty list."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.select([])

        assert result is query_builder
        assert query_builder._select_fields == []

    def test_select_empty_dict(self):
        """Test select method with empty dictionary."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.select({})

        assert result is query_builder
        assert query_builder._select_fields == []

    def test_order_by_with_invalid_order(self):
        """Test order_by method with custom order value."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        result = query_builder.order_by("name", "custom_order")

        assert result is query_builder
        assert query_builder._order_by.as_string() == "name"
        assert query_builder._sort_order == "custom_order"

    def test_sql_generation_with_special_characters_in_filters(self):
        """Test SQL generation with special characters in filter conditions."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        query_builder.select(["id", "name"]).where("name LIKE '%test%'").where(
            "id IN (1,2,3)"
        )
        sql = query_builder._generate_sql()
        assert (
            sql.as_string()
            == """SELECT id, name FROM "test_table" WHERE name LIKE '%test%' AND id IN (1,2,3);"""
        )

    def test_or_where_with_string(self):
        """Test or_where method with string filter."""
        mock_connection = Mock(spec=HoloConnect)
        qb = QueryBuilder(mock_connection, "test_table")

        qb.where("id > 10").or_where("status = 'active'")

        assert len(qb._filters) == 2
        assert qb._filters[1][0] == LogicalOperator.OR

    def test_or_where_with_filter_expression(self):
        """Test or_where method with FilterExpression."""
        from holo_search_sdk.backend.filter import FilterExpression

        mock_connection = Mock(spec=HoloConnect)
        qb = QueryBuilder(mock_connection, "test_table")

        filter_expr = FilterExpression("id > 10")
        qb.where("status = 'active'").or_where(filter_expr)

        assert len(qb._filters) == 2
        assert qb._filters[1][0] == LogicalOperator.OR

    @patch("holo_search_sdk.backend.query.build_tokenize_sql")
    def test_select_tokenize_with_column(self, mock_build_tokenize):
        """Test select_tokenize with column parameter."""
        from psycopg import sql as psql

        mock_connection = Mock(spec=HoloConnect)
        mock_build_tokenize.return_value = psql.SQL("tokenize_result")

        qb = QueryBuilder(mock_connection, "test_table")
        result = qb.select_tokenize(column="content", output_name="tokens")

        assert result is qb
        mock_build_tokenize.assert_called_once_with("content", None, None, None, None)
        assert len(qb._select_fields) == 1

    @patch("holo_search_sdk.backend.query.build_tokenize_sql")
    def test_select_tokenize_with_text(self, mock_build_tokenize):
        """Test select_tokenize with text parameter."""
        from psycopg import sql as psql

        mock_connection = Mock(spec=HoloConnect)
        mock_build_tokenize.return_value = psql.SQL("tokenize_result")

        qb = QueryBuilder(mock_connection, "test_table")
        result = qb.select_tokenize(
            text="hello world", output_name="tokens", tokenizer="jieba"
        )

        assert result is qb
        mock_build_tokenize.assert_called_once_with(
            None, "hello world", "jieba", None, None
        )

    @patch("holo_search_sdk.backend.query.build_text_search_sql")
    def test_select_text_search_basic(self, mock_build_text_search):
        """Test select_text_search with basic parameters."""
        from psycopg import sql as psql

        mock_connection = Mock(spec=HoloConnect)
        mock_build_text_search.return_value = psql.SQL("text_search_result")

        qb = QueryBuilder(mock_connection, "test_table")
        result = qb.select_text_search("content", "search query", output_name="score")

        assert result is qb
        mock_build_text_search.assert_called_once()
        assert len(qb._select_fields) == 1

    @patch("holo_search_sdk.backend.query.build_text_search_sql")
    def test_select_text_search_with_options(self, mock_build_text_search):
        """Test select_text_search with additional options."""
        from psycopg import sql as psql

        mock_connection = Mock(spec=HoloConnect)
        mock_build_text_search.return_value = psql.SQL("text_search_result")

        qb = QueryBuilder(mock_connection, "test_table")
        result = qb.select_text_search(
            "content",
            "search query",
            output_name="score",
            mode="phrase",
            operator="AND",
            tokenizer="jieba",
        )

        assert result is qb
        mock_build_text_search.assert_called_once()

    @patch("holo_search_sdk.backend.query.build_text_search_sql")
    def test_where_text_search(self, mock_build_text_search):
        """Test where_text_search method."""
        from psycopg import sql as psql

        mock_connection = Mock(spec=HoloConnect)
        mock_build_text_search.return_value = psql.SQL("text_search_result")

        qb = QueryBuilder(mock_connection, "test_table")
        result = qb.where_text_search("content", "search query", 0.5)

        assert result is qb
        assert len(qb._filters) == 1
        assert qb._filters[0][0] == LogicalOperator.AND

    @patch("holo_search_sdk.backend.query.build_text_search_sql")
    def test_and_where_text_search(self, mock_build_text_search):
        """Test and_where_text_search method."""
        from psycopg import sql as psql

        mock_connection = Mock(spec=HoloConnect)
        mock_build_text_search.return_value = psql.SQL("text_search_result")

        qb = QueryBuilder(mock_connection, "test_table")
        result = qb.and_where_text_search("content", "search query", 0.5)

        assert result is qb
        assert len(qb._filters) == 1
        assert qb._filters[0][0] == LogicalOperator.AND

    @patch("holo_search_sdk.backend.query.build_text_search_sql")
    def test_or_where_text_search(self, mock_build_text_search):
        """Test or_where_text_search method."""
        from psycopg import sql as psql

        mock_connection = Mock(spec=HoloConnect)
        mock_build_text_search.return_value = psql.SQL("text_search_result")

        qb = QueryBuilder(mock_connection, "test_table")
        qb.where("id > 10")
        result = qb.or_where_text_search("content", "search query", 0.5)

        assert result is qb
        assert len(qb._filters) == 2
        assert qb._filters[1][0] == LogicalOperator.OR

    def test_join_with_string_table(self):
        """Test join method with string table name."""
        mock_connection = Mock(spec=HoloConnect)
        qb = QueryBuilder(mock_connection, "test_table")

        result = qb.join("other_table", "test_table.id = other_table.test_id")

        assert result is qb
        assert len(qb._joins) == 1
        assert qb._joins[0][0] == "INNER"
        assert qb._joins[0][1] == "other_table"

    def test_join_with_table_object(self):
        """Test join method with HoloTable object."""
        from holo_search_sdk.backend.table import HoloTable

        mock_connection = Mock(spec=HoloConnect)
        qb = QueryBuilder(mock_connection, "test_table")

        other_table = HoloTable(mock_connection, "other_table", "ot")
        result = qb.join(other_table, "test_table.id = ot.test_id")

        assert result is qb
        assert len(qb._joins) == 1
        assert qb._joins[0][1] == "other_table"
        assert qb._joins[0][3] == "ot"

    def test_join_with_filter_expression(self):
        """Test join method with FilterExpression."""
        from holo_search_sdk.backend.filter import FilterExpression

        mock_connection = Mock(spec=HoloConnect)
        qb = QueryBuilder(mock_connection, "test_table")

        condition = FilterExpression("test_table.id = other_table.test_id")
        result = qb.join("other_table", condition)

        assert result is qb
        assert len(qb._joins) == 1

    def test_inner_join(self):
        """Test inner_join method."""
        mock_connection = Mock(spec=HoloConnect)
        qb = QueryBuilder(mock_connection, "test_table")

        result = qb.inner_join("other_table", "test_table.id = other_table.test_id")

        assert result is qb
        assert len(qb._joins) == 1
        assert qb._joins[0][0] == "INNER"

    def test_left_join(self):
        """Test left_join method."""
        mock_connection = Mock(spec=HoloConnect)
        qb = QueryBuilder(mock_connection, "test_table")

        result = qb.left_join("other_table", "test_table.id = other_table.test_id")

        assert result is qb
        assert len(qb._joins) == 1
        assert qb._joins[0][0] == "LEFT"

    def test_right_join(self):
        """Test right_join method."""
        mock_connection = Mock(spec=HoloConnect)
        qb = QueryBuilder(mock_connection, "test_table")

        result = qb.right_join("other_table", "test_table.id = other_table.test_id")

        assert result is qb
        assert len(qb._joins) == 1
        assert qb._joins[0][0] == "RIGHT"

    def test_join_with_table_alias(self):
        """Test join with custom table alias."""
        mock_connection = Mock(spec=HoloConnect)
        qb = QueryBuilder(mock_connection, "test_table")

        result = qb.join("other_table", "test_table.id = ot.test_id", table_alias="ot")

        assert result is qb
        assert qb._joins[0][3] == "ot"

    def test_full_join(self):
        """Test FULL OUTER JOIN."""
        mock_connection = Mock(spec=HoloConnect)
        qb = QueryBuilder(mock_connection, "table1")

        result = qb.full_join("table2", "table1.id = table2.id")

        assert result is qb
        assert len(qb._joins) == 1
        assert qb._joins[0][0] == "FULL"

    def test_cross_join(self):
        """Test CROSS JOIN."""
        mock_connection = Mock(spec=HoloConnect)
        qb = QueryBuilder(mock_connection, "table1")

        result = qb.cross_join("table2", "table1.id = table2.id")

        assert result is qb
        assert len(qb._joins) == 1
        assert qb._joins[0][0] == "CROSS"

    def test_set_table_alias(self):
        """Test setting table alias."""
        mock_connection = Mock(spec=HoloConnect)
        qb = QueryBuilder(mock_connection, "test_table")

        result = qb.set_table_alias("t1")

        assert result is qb
        assert qb._table_alias == "t1"

    def test_generate_sql_with_distance_filter_no_column(self):
        """Test SQL generation with distance filter but no distance column raises error."""
        mock_connection = Mock(spec=HoloConnect)
        qb = QueryBuilder(mock_connection, "test_table")
        qb.select("*")
        qb._distance_filter = psql.SQL("<= 0.5")

        with pytest.raises(SqlError) as exc_info:
            qb._generate_sql()

        assert "Distance column is required" in str(exc_info.value)

    def test_generate_sql_with_distance_filter_and_column(self):
        """Test SQL generation with distance filter and column."""
        mock_connection = Mock(spec=HoloConnect)
        qb = QueryBuilder(mock_connection, "test_table")
        qb.select("*")
        qb._distance_column = "distance"
        qb._distance_filter = psql.SQL("<= 0.5")

        sql = qb._generate_sql()
        sql_str = sql.as_string()

        assert "SELECT * FROM" in sql_str
        assert "WHERE" in sql_str
        assert '"distance"' in sql_str

    def test_explain(self):
        """Test EXPLAIN query."""
        mock_connection = Mock(spec=HoloConnect)
        mock_connection.fetchall.return_value = [("Seq Scan on test_table",)]

        qb = QueryBuilder(mock_connection, "test_table")
        qb.select("*")

        result = qb.explain()

        assert result == [("Seq Scan on test_table",)]
        mock_connection.fetchall.assert_called_once()

    def test_explain_analyze(self):
        """Test EXPLAIN ANALYZE query."""
        mock_connection = Mock(spec=HoloConnect)
        mock_connection.fetchall.return_value = [
            ("Seq Scan on test_table (cost=0.00..1.00)",)
        ]

        qb = QueryBuilder(mock_connection, "test_table")
        qb.select("*")

        result = qb.explain_analyze()

        assert result == [("Seq Scan on test_table (cost=0.00..1.00)",)]
        mock_connection.fetchall.assert_called_once()

    def test_generate_sql_with_joins(self):
        """Test SQL generation with JOIN clauses."""
        mock_connection = Mock(spec=HoloConnect)
        qb = QueryBuilder(mock_connection, "table1")
        qb.select("*")
        qb.inner_join("table2", "table1.id = table2.id", table_alias="t2")

        sql = qb._generate_sql()
        sql_str = sql.as_string()

        assert "FROM" in sql_str
        assert "INNER JOIN" in sql_str
        assert '"table2"' in sql_str
        assert '"t2"' in sql_str
        assert "ON" in sql_str

    def test_generate_sql_with_table_alias(self):
        """Test SQL generation with table alias."""
        mock_connection = Mock(spec=HoloConnect)
        qb = QueryBuilder(mock_connection, "test_table", table_alias="t1")
        qb.select("*")

        sql = qb._generate_sql()
        sql_str = sql.as_string()

        assert '"test_table"' in sql_str
        assert '"t1"' in sql_str

    def test_generate_sql_order_by_asc(self):
        """Test SQL generation with ORDER BY ASC."""
        mock_connection = Mock(spec=HoloConnect)
        qb = QueryBuilder(mock_connection, "test_table")
        qb.select("*")
        qb.order_by("name", order="asc")

        sql = qb._generate_sql()
        sql_str = sql.as_string()

        assert "ORDER BY" in sql_str
        assert "ASC" in sql_str

    def test_to_string(self):
        """Test to_string method."""
        mock_connection = Mock(spec=HoloConnect)
        qb = QueryBuilder(mock_connection, "test_table")
        qb.select("id, name")

        sql_str = qb.to_string()

        assert isinstance(sql_str, str)
        assert "SELECT" in sql_str
        assert "FROM" in sql_str

    def test_select_with_tuple_in_list(self):
        """Test select method with tuple in list (covers line 182-190)."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        # Test with tuple containing string column and string alias
        result = query_builder.select([("id", "user_id"), ("name", "user_name")])

        assert result is query_builder
        assert len(query_builder._select_fields) == 2
        # Check that tuples are properly converted
        field_strs = [
            (f[0].as_string(), f[1].as_string() if f[1] else None)
            for f in query_builder._select_fields
        ]
        assert ("id", '"user_id"') in field_strs
        assert ("name", '"user_name"') in field_strs

    def test_select_with_tuple_composable_in_list(self):
        """Test select method with tuple containing Composable in list."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        # Test with tuple containing Composable column and Composable alias
        col_sql = psql.SQL("COUNT(*)")
        alias_sql = psql.Identifier("total")
        result = query_builder.select([(col_sql, alias_sql)])

        assert result is query_builder
        assert len(query_builder._select_fields) == 1
        assert query_builder._select_fields[0][0] is col_sql
        assert query_builder._select_fields[0][1] is alias_sql

    def test_select_with_mixed_list(self):
        """Test select method with mixed types in list."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        # Mix of string, tuple, and Composable
        composable_col = psql.SQL("email")
        result = query_builder.select(["id", ("name", "user_name"), composable_col])

        assert result is query_builder
        assert len(query_builder._select_fields) == 3

    def test_select_with_single_tuple(self):
        """Test select method with single tuple parameter (covers line 204-210)."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        # Test with single tuple containing string column and string alias
        result = query_builder.select(("id", "user_id"))

        assert result is query_builder
        assert len(query_builder._select_fields) == 1
        field_str = (
            query_builder._select_fields[0][0].as_string(),
            (
                query_builder._select_fields[0][1].as_string()
                if query_builder._select_fields[0][1]
                else None
            ),
        )
        assert field_str == ("id", '"user_id"')

    def test_select_with_single_tuple_composable(self):
        """Test select method with single tuple containing Composable."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        # Test with tuple containing Composable column and Composable alias
        col_sql = psql.SQL("MAX(score)")
        alias_sql = psql.Identifier("max_score")
        result = query_builder.select((col_sql, alias_sql))

        assert result is query_builder
        assert len(query_builder._select_fields) == 1
        assert query_builder._select_fields[0][0] is col_sql
        assert query_builder._select_fields[0][1] is alias_sql

    def test_select_with_single_tuple_none_alias(self):
        """Test select method with single tuple with None alias."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        # Test with tuple where alias is None
        result = query_builder.select(("id", None))

        assert result is query_builder
        assert len(query_builder._select_fields) == 1
        assert query_builder._select_fields[0][1] is None

    def test_select_with_composable(self):
        """Test select method with Composable parameter."""
        mock_connection = Mock(spec=HoloConnect)
        query_builder = QueryBuilder(mock_connection, "test_table")

        # Test with Composable
        composable_col = psql.SQL("COUNT(*)")
        result = query_builder.select(composable_col)

        assert result is query_builder
        assert len(query_builder._select_fields) == 1
        assert query_builder._select_fields[0][0] is composable_col
        assert query_builder._select_fields[0][1] is None
