"""
Tests for filter module in Holo Search SDK.

This module contains tests for filter expression classes.
"""

from collections import OrderedDict

import pytest
from psycopg import sql as psql

from holo_search_sdk.backend.filter import (
    AndFilter,
    Filter,
    FilterExpression,
    LogicalOperator,
    NotFilter,
    OrFilter,
    TextSearchFilter,
)
from holo_search_sdk.exceptions import SqlError


class TestFilterExpression:
    """Test cases for the FilterExpression class."""

    def test_filter_expression_initialization_with_string(self):
        """Test FilterExpression initialization with string condition."""
        condition = "age > 18"
        filter_expr = FilterExpression(condition)

        assert filter_expr.condition is not None
        assert filter_expr.operator is None
        assert filter_expr.left is None
        assert filter_expr.right is None
        assert filter_expr.is_negated is False

    def test_filter_expression_initialization_with_composable(self):
        """Test FilterExpression initialization with Composable condition."""
        condition = psql.SQL("status = 'active'")
        filter_expr = FilterExpression(condition)

        assert filter_expr.condition is not None
        assert filter_expr.operator is None

    def test_filter_expression_initialization_with_empty_string(self):
        """Test FilterExpression initialization with empty string."""
        filter_expr = FilterExpression("")

        assert filter_expr.condition is None

    def test_filter_expression_and_operator(self):
        """Test FilterExpression AND operator."""
        filter1 = FilterExpression("age > 18")
        filter2 = FilterExpression("status = 'active'")

        result = filter1 & filter2

        assert result.operator == LogicalOperator.AND
        assert result.left is filter1
        assert result.right is filter2
        assert result.condition is None

    def test_filter_expression_or_operator(self):
        """Test FilterExpression OR operator."""
        filter1 = FilterExpression("premium = true")
        filter2 = FilterExpression("vip = true")

        result = filter1 | filter2

        assert result.operator == LogicalOperator.OR
        assert result.left is filter1
        assert result.right is filter2
        assert result.condition is None

    def test_filter_expression_not_operator(self):
        """Test FilterExpression NOT operator."""
        filter_expr = FilterExpression("deleted = true")

        result = ~filter_expr

        assert result.is_negated is True
        assert result.condition is not None

    def test_filter_expression_double_negation(self):
        """Test FilterExpression double negation."""
        filter_expr = FilterExpression("active = true")

        result = ~~filter_expr

        assert result.is_negated is False

    def test_filter_expression_to_sql_simple(self):
        """Test converting simple FilterExpression to SQL."""
        filter_expr = FilterExpression("age > 18")

        sql = filter_expr.to_sql()

        assert sql is not None
        sql_str = sql.as_string()
        assert "age > 18" in sql_str

    def test_filter_expression_to_sql_and(self):
        """Test converting AND FilterExpression to SQL."""
        filter1 = FilterExpression("age > 18")
        filter2 = FilterExpression("status = 'active'")
        combined = filter1 & filter2

        sql = combined.to_sql()

        assert sql is not None
        sql_str = sql.as_string()
        assert "AND" in sql_str
        assert "(" in sql_str
        assert ")" in sql_str

    def test_filter_expression_to_sql_or(self):
        """Test converting OR FilterExpression to SQL."""
        filter1 = FilterExpression("premium = true")
        filter2 = FilterExpression("vip = true")
        combined = filter1 | filter2

        sql = combined.to_sql()

        assert sql is not None
        sql_str = sql.as_string()
        assert "OR" in sql_str

    def test_filter_expression_to_sql_not(self):
        """Test converting NOT FilterExpression to SQL."""
        filter_expr = FilterExpression("deleted = true")
        negated = ~filter_expr

        sql = negated.to_sql()

        assert sql is not None
        sql_str = sql.as_string()
        assert "NOT" in sql_str

    def test_filter_expression_to_sql_complex(self):
        """Test converting complex FilterExpression to SQL."""
        filter1 = FilterExpression("age > 18")
        filter2 = FilterExpression("status = 'active'")
        filter3 = FilterExpression("premium = true")

        combined = (filter1 & filter2) | filter3

        sql = combined.to_sql()

        assert sql is not None
        sql_str = sql.as_string()
        assert "AND" in sql_str
        assert "OR" in sql_str

    def test_filter_expression_to_sql_empty_condition(self):
        """Test converting empty FilterExpression to SQL."""
        filter_expr = FilterExpression("")

        sql = filter_expr.to_sql()

        assert sql is not None
        sql_str = sql.as_string()
        assert "1=1" in sql_str


class TestFilter:
    """Test cases for the Filter class."""

    def test_filter_creation(self):
        """Test Filter creation."""
        filter_obj = Filter("age > 18")

        assert isinstance(filter_obj, FilterExpression)
        assert filter_obj.condition is not None

    def test_filter_with_and_operator(self):
        """Test Filter with AND operator."""
        filter1 = Filter("age > 18")
        filter2 = Filter("status = 'active'")

        result = filter1 & filter2

        assert result.operator == LogicalOperator.AND

    def test_filter_with_or_operator(self):
        """Test Filter with OR operator."""
        filter1 = Filter("premium = true")
        filter2 = Filter("vip = true")

        result = filter1 | filter2

        assert result.operator == LogicalOperator.OR

    def test_filter_with_not_operator(self):
        """Test Filter with NOT operator."""
        filter_obj = Filter("deleted = true")

        result = ~filter_obj

        assert result.is_negated is True


class TestAndFilter:
    """Test cases for the AndFilter class."""

    def test_and_filter_with_two_conditions(self):
        """Test AndFilter with two conditions."""
        result = AndFilter("age > 18", "status = 'active'")

        assert isinstance(result, FilterExpression)
        assert result.operator == LogicalOperator.AND

    def test_and_filter_with_three_conditions(self):
        """Test AndFilter with three conditions."""
        result = AndFilter("age > 18", "status = 'active'", "premium = true")

        assert isinstance(result, FilterExpression)
        sql = result.to_sql()
        sql_str = sql.as_string()
        assert "AND" in sql_str

    def test_and_filter_with_filter_expressions(self):
        """Test AndFilter with FilterExpression objects."""
        filter1 = Filter("age > 18")
        filter2 = Filter("status = 'active'")

        result = AndFilter(filter1, filter2)

        assert isinstance(result, FilterExpression)
        assert result.operator == LogicalOperator.AND

    def test_and_filter_with_mixed_types(self):
        """Test AndFilter with mixed string and FilterExpression."""
        filter1 = Filter("age > 18")

        result = AndFilter(filter1, "status = 'active'")

        assert isinstance(result, FilterExpression)
        assert result.operator == LogicalOperator.AND

    def test_and_filter_no_conditions(self):
        """Test AndFilter with no conditions raises error."""
        with pytest.raises(SqlError) as exc_info:
            AndFilter()

        assert "At least one condition is required for AndFilter" in str(exc_info.value)


class TestOrFilter:
    """Test cases for the OrFilter class."""

    def test_or_filter_with_two_conditions(self):
        """Test OrFilter with two conditions."""
        result = OrFilter("premium = true", "vip = true")

        assert isinstance(result, FilterExpression)
        assert result.operator == LogicalOperator.OR

    def test_or_filter_with_three_conditions(self):
        """Test OrFilter with three conditions."""
        result = OrFilter("premium = true", "vip = true", "admin = true")

        assert isinstance(result, FilterExpression)
        sql = result.to_sql()
        sql_str = sql.as_string()
        assert "OR" in sql_str

    def test_or_filter_with_filter_expressions(self):
        """Test OrFilter with FilterExpression objects."""
        filter1 = Filter("premium = true")
        filter2 = Filter("vip = true")

        result = OrFilter(filter1, filter2)

        assert isinstance(result, FilterExpression)
        assert result.operator == LogicalOperator.OR

    def test_or_filter_with_mixed_types(self):
        """Test OrFilter with mixed string and FilterExpression."""
        filter1 = Filter("premium = true")

        result = OrFilter(filter1, "vip = true")

        assert isinstance(result, FilterExpression)
        assert result.operator == LogicalOperator.OR

    def test_or_filter_no_conditions(self):
        """Test OrFilter with no conditions raises error."""
        with pytest.raises(SqlError) as exc_info:
            OrFilter()

        assert "At least one condition is required for OrFilter" in str(exc_info.value)


class TestNotFilter:
    """Test cases for the NotFilter class."""

    def test_not_filter_with_string(self):
        """Test NotFilter with string condition."""
        result = NotFilter("deleted = true")

        assert isinstance(result, FilterExpression)
        assert result.is_negated is True

    def test_not_filter_with_filter_expression(self):
        """Test NotFilter with FilterExpression."""
        filter_obj = Filter("banned = true")

        result = NotFilter(filter_obj)

        assert isinstance(result, FilterExpression)
        assert result.is_negated is True

    def test_not_filter_to_sql(self):
        """Test NotFilter SQL generation."""
        result = NotFilter("active = false")

        sql = result.to_sql()
        sql_str = sql.as_string()

        assert "NOT" in sql_str


class TestTextSearchFilter:
    """Test cases for the TextSearchFilter class."""

    def test_text_search_filter_basic(self):
        """Test basic TextSearchFilter creation."""
        result = TextSearchFilter(
            column="content", expression="search term", min_threshold=0.5
        )

        assert isinstance(result, FilterExpression)
        sql = result.to_sql()
        sql_str = sql.as_string()
        assert "TEXT_SEARCH" in sql_str
        assert ">" in sql_str

    def test_text_search_filter_with_mode(self):
        """Test TextSearchFilter with mode."""
        result = TextSearchFilter(
            column="content", expression="search term", min_threshold=0.5, mode="phrase"
        )

        assert isinstance(result, FilterExpression)
        sql = result.to_sql()
        assert sql is not None

    def test_text_search_filter_with_operator(self):
        """Test TextSearchFilter with operator."""
        result = TextSearchFilter(
            column="content",
            expression="search term",
            min_threshold=0.5,
            operator="and",
        )

        assert isinstance(result, FilterExpression)
        sql = result.to_sql()
        assert sql is not None

    def test_text_search_filter_with_tokenizer(self):
        """Test TextSearchFilter with tokenizer."""
        result = TextSearchFilter(
            column="content",
            expression="search term",
            min_threshold=0.5,
            tokenizer="jieba",
        )

        assert isinstance(result, FilterExpression)
        sql = result.to_sql()
        assert sql is not None

    def test_text_search_filter_with_tokenizer_params(self):
        """Test TextSearchFilter with tokenizer parameters."""
        tokenizer_params = {"max_token_length": 100}

        result = TextSearchFilter(
            column="content",
            expression="search term",
            min_threshold=0.5,
            tokenizer="ik",
            tokenizer_params=tokenizer_params,
        )

        assert isinstance(result, FilterExpression)
        sql = result.to_sql()
        assert sql is not None

    def test_text_search_filter_with_filter_params(self):
        """Test TextSearchFilter with filter parameters."""
        filter_params = OrderedDict([("lowercase", True)])

        result = TextSearchFilter(
            column="content",
            expression="search term",
            min_threshold=0.5,
            tokenizer="standard",
            filter_params=filter_params,
        )

        assert isinstance(result, FilterExpression)
        sql = result.to_sql()
        assert sql is not None

    def test_text_search_filter_comprehensive(self):
        """Test TextSearchFilter with all parameters."""
        filter_params = OrderedDict([("lowercase", True), ("stop", ["the", "a"])])

        result = TextSearchFilter(
            column="content",
            expression="search term",
            min_threshold=0.7,
            mode="natural_language",
            operator="OR",
            tokenizer="jieba",
            tokenizer_params={"mode": "search"},
            filter_params=filter_params,
            slop=2,
        )

        assert isinstance(result, FilterExpression)
        sql = result.to_sql()
        sql_str = sql.as_string()
        assert "TEXT_SEARCH" in sql_str
        assert ">" in sql_str


class TestFilterIntegration:
    """Integration tests for filter combinations."""

    def test_complex_filter_combination(self):
        """Test complex filter combination."""
        age_filter = Filter("age > 18")
        status_filter = Filter("status = 'active'")
        premium_filter = Filter("premium = true")

        # (age > 18 AND status = 'active') OR premium = true
        combined = (age_filter & status_filter) | premium_filter

        sql = combined.to_sql()
        sql_str = sql.as_string()

        assert "AND" in sql_str
        assert "OR" in sql_str
        assert "(" in sql_str

    def test_and_filter_with_not(self):
        """Test AndFilter combined with NOT."""
        filter1 = Filter("age > 18")
        filter2 = NotFilter("deleted = true")

        result = filter1 & filter2

        sql = result.to_sql()
        sql_str = sql.as_string()

        assert "AND" in sql_str
        assert "NOT" in sql_str

    def test_or_filter_with_and_filter(self):
        """Test OrFilter combined with AndFilter."""
        and_result = AndFilter("age > 18", "status = 'active'")
        or_condition = Filter("admin = true")

        combined = and_result | or_condition

        sql = combined.to_sql()
        sql_str = sql.as_string()

        assert "AND" in sql_str
        assert "OR" in sql_str

    def test_nested_logical_operations(self):
        """Test deeply nested logical operations."""
        f1 = Filter("a = 1")
        f2 = Filter("b = 2")
        f3 = Filter("c = 3")
        f4 = Filter("d = 4")

        # ((a = 1 AND b = 2) OR c = 3) AND d = 4
        combined = ((f1 & f2) | f3) & f4

        sql = combined.to_sql()
        sql_str = sql.as_string()

        assert "AND" in sql_str
        assert "OR" in sql_str
        # Multiple levels of parentheses
        assert sql_str.count("(") >= 3

    def test_filter_with_text_search(self):
        """Test combining regular filter with text search filter."""
        text_filter = TextSearchFilter(
            column="content", expression="search", min_threshold=0.5
        )
        status_filter = Filter("status = 'published'")

        combined = text_filter & status_filter

        sql = combined.to_sql()
        sql_str = sql.as_string()

        assert "TEXT_SEARCH" in sql_str
        assert "AND" in sql_str
        assert "status" in sql_str
