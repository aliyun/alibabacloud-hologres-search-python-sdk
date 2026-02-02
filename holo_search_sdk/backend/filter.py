"""
Filter module for Holo Search SDK.

Provides filter expression classes for building complex query conditions.
"""

from collections import OrderedDict
from enum import Enum
from typing import Dict, List, Optional, Union

from psycopg import sql as psql
from typing_extensions import LiteralString

from ..exceptions import SqlError
from ..types import (
    PinyinFilterParamType,
    TextFilterType,
    TextSearchModeType,
    TextSearchOperatorType,
    TokenizerType,
)
from .utils.sql_utils import build_text_search_sql


class LogicalOperator(Enum):
    """Logical operators for query conditions."""

    AND = "AND"
    OR = "OR"


class FilterExpression:
    """Represents a filter expression that can contain logical operations."""

    def __init__(self, condition: Union[LiteralString, psql.Composable]):
        """Initialize with a single condition."""
        if isinstance(condition, psql.Composable):
            self.condition = condition
        elif condition:  # Only create SQL if condition is not empty
            self.condition = psql.SQL(condition)
        else:
            self.condition = None
        self.operator: Optional[LogicalOperator] = None
        self.left: Optional["FilterExpression"] = None
        self.right: Optional["FilterExpression"] = None
        self.is_negated: bool = False

    def __and__(self, other: "FilterExpression") -> "FilterExpression":
        """Combine with AND operator."""
        result = FilterExpression("")
        result.operator = LogicalOperator.AND
        result.left = self
        result.right = other
        result.condition = None
        return result

    def __or__(self, other: "FilterExpression") -> "FilterExpression":
        """Combine with OR operator."""
        result = FilterExpression("")
        result.operator = LogicalOperator.OR
        result.left = self
        result.right = other
        result.condition = None
        return result

    def __invert__(self) -> "FilterExpression":
        """Apply NOT operator."""
        result = FilterExpression("")
        result.condition = self.condition
        result.operator = self.operator
        result.left = self.left
        result.right = self.right
        result.is_negated = not self.is_negated
        return result

    def to_sql(self) -> psql.Composable:
        """Convert the expression to SQL."""
        if self.condition is not None:
            # Simple condition
            sql = self.condition
        elif (
            self.operator is not None
            and self.left is not None
            and self.right is not None
        ):
            # Complex expression with operator
            left_sql = self.left.to_sql()
            right_sql = self.right.to_sql()

            # Wrap in parentheses for proper precedence
            sql = psql.Composed(
                [
                    psql.SQL("("),
                    left_sql,
                    psql.SQL(" "),
                    psql.SQL(self.operator.value),
                    psql.SQL(" "),
                    right_sql,
                    psql.SQL(")"),
                ]
            )
        else:
            # Fallback for empty conditions
            sql = psql.SQL("1=1")

        if self.is_negated:
            sql = psql.Composed([psql.SQL("NOT ("), sql, psql.SQL(")")])

        return sql


# Convenient filter classes for creating filter expressions
class Filter(FilterExpression):
    """
    A convenient wrapper for FilterExpression that supports direct instantiation.
    Supports all logical operators (&, |, ~) for easy combination.

    Example:
        query.where(Filter("age > 18") & Filter("status = 'active'"))
        query.where(Filter("premium = true") | Filter("vip = true"))
        query.where(~Filter("deleted = true"))
    """

    def __new__(
        cls, condition: Union[LiteralString, psql.Composable]
    ) -> FilterExpression:
        """Create a new FilterExpression instance."""
        return FilterExpression(condition)


class AndFilter:
    """
    Creates an AND filter from multiple conditions.

    Example:
        query.where(AndFilter("age > 18", "status = 'active'"))
        query.where(AndFilter(Filter("category = 'books'"), Filter("price < 100")))
    """

    def __new__(
        cls, *conditions: Union[LiteralString, psql.Composable, FilterExpression]
    ) -> FilterExpression:
        """Create an AND FilterExpression from multiple conditions."""
        if not conditions:
            raise SqlError("At least one condition is required for AndFilter")

        result = (
            conditions[0]
            if isinstance(conditions[0], FilterExpression)
            else FilterExpression(conditions[0])
        )
        for condition in conditions[1:]:
            filter_expr = (
                condition
                if isinstance(condition, FilterExpression)
                else FilterExpression(condition)
            )
            result = result & filter_expr
        return result


class OrFilter:
    """
    Creates an OR filter from multiple conditions.

    Example:
        query.where(OrFilter("category = 'premium'", "vip = true"))
        query.where(OrFilter(Filter("discount > 0.5"), Filter("member = true")))
    """

    def __new__(
        cls, *conditions: Union[LiteralString, psql.Composable, FilterExpression]
    ) -> FilterExpression:
        """Create an OR FilterExpression from multiple conditions."""
        if not conditions:
            raise SqlError("At least one condition is required for OrFilter")

        result = (
            conditions[0]
            if isinstance(conditions[0], FilterExpression)
            else FilterExpression(conditions[0])
        )
        for condition in conditions[1:]:
            filter_expr = (
                condition
                if isinstance(condition, FilterExpression)
                else FilterExpression(condition)
            )
            result = result | filter_expr
        return result


class NotFilter:
    """
    Creates a NOT filter from a condition.

    Example:
        query.where(NotFilter("deleted = true"))
        query.where(NotFilter(Filter("banned = true")))
    """

    def __new__(
        cls, condition: Union[LiteralString, psql.Composable, FilterExpression]
    ) -> FilterExpression:
        """Create a NOT FilterExpression from a condition."""
        filter_expr = (
            condition
            if isinstance(condition, FilterExpression)
            else FilterExpression(condition)
        )
        return ~filter_expr


class TextSearchFilter:
    """
    Creates a text search filter.
    """

    def __new__(
        cls,
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
    ) -> FilterExpression:
        """
        Creates a text search filter.

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
        return FilterExpression(
            psql.SQL("{} > {}").format(text_search_clause, min_threshold)
        )
