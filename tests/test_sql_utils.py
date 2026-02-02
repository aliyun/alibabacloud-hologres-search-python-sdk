"""
Tests for SQL utility functions in Holo Search SDK.

This module contains tests for SQL building helper functions.
"""

from collections import OrderedDict

import pytest

from holo_search_sdk.backend.utils.sql_utils import (
    build_analyzer_params_sql,
    build_text_search_sql,
    build_tokenize_sql,
)
from holo_search_sdk.exceptions import SqlError


class TestBuildAnalyzerParamsSql:
    """Test cases for build_analyzer_params_sql function."""

    def test_build_analyzer_params_with_tokenizer_only(self):
        """Test building analyzer params with only tokenizer."""
        result = build_analyzer_params_sql(tokenizer="jieba", tokenizer_params={})

        assert result is not None
        sql_str = result.as_string()
        assert '"type":jieba' in sql_str or '"type":"jieba"' in sql_str

    def test_build_analyzer_params_with_tokenizer_params(self):
        """Test building analyzer params with tokenizer parameters."""
        tokenizer_params = {"max_token_length": 100, "mode": "search"}

        result = build_analyzer_params_sql(
            tokenizer="ik", tokenizer_params=tokenizer_params
        )

        assert result is not None
        sql_str = result.as_string()
        assert '"tokenizer"' in sql_str
        assert "ik" in sql_str

    def test_build_analyzer_params_with_lowercase_filter(self):
        """Test building analyzer params with lowercase filter."""
        filter_params = OrderedDict([("lowercase", True)])

        result = build_analyzer_params_sql(
            tokenizer="standard", tokenizer_params={}, filter_params=filter_params
        )

        assert result is not None
        sql_str = result.as_string()
        assert '"filter"' in sql_str
        assert '"lowercase"' in sql_str

    def test_build_analyzer_params_with_stop_filter_list(self):
        """Test building analyzer params with stop filter as list."""
        filter_params = OrderedDict([("stop", ["the", "a", "an"])])

        result = build_analyzer_params_sql(
            tokenizer="standard", tokenizer_params={}, filter_params=filter_params
        )

        assert result is not None
        sql_str = result.as_string()
        assert '"filter"' in sql_str
        assert '"stop"' in sql_str
        assert "stop_words" in sql_str

    def test_build_analyzer_params_with_stop_filter_string(self):
        """Test building analyzer params with stop filter as string."""
        filter_params = OrderedDict([("stop", "english")])

        result = build_analyzer_params_sql(
            tokenizer="standard", tokenizer_params={}, filter_params=filter_params
        )

        assert result is not None
        sql_str = result.as_string()
        assert '"filter"' in sql_str
        assert "stop_words" in sql_str

    def test_build_analyzer_params_with_stemmer_filter(self):
        """Test building analyzer params with stemmer filter."""
        filter_params = OrderedDict([("stemmer", "english")])

        result = build_analyzer_params_sql(
            tokenizer="standard", tokenizer_params={}, filter_params=filter_params
        )

        assert result is not None
        sql_str = result.as_string()
        assert '"filter"' in sql_str
        assert '"stemmer"' in sql_str
        assert "language" in sql_str

    def test_build_analyzer_params_with_length_filter(self):
        """Test building analyzer params with length filter."""
        filter_params = OrderedDict([("length", 50)])

        result = build_analyzer_params_sql(
            tokenizer="standard", tokenizer_params={}, filter_params=filter_params
        )

        assert result is not None
        sql_str = result.as_string()
        assert '"filter"' in sql_str
        assert '"length"' in sql_str
        assert "max" in sql_str

    def test_build_analyzer_params_with_removepunct_filter_bool(self):
        """Test building analyzer params with removepunct filter as bool."""
        filter_params = OrderedDict([("removepunct", True)])

        result = build_analyzer_params_sql(
            tokenizer="standard", tokenizer_params={}, filter_params=filter_params
        )

        assert result is not None
        sql_str = result.as_string()
        assert '"filter"' in sql_str
        assert '"removepunct"' in sql_str

    def test_build_analyzer_params_with_removepunct_filter_string(self):
        """Test building analyzer params with removepunct filter as string."""
        filter_params = OrderedDict([("removepunct", "all")])

        result = build_analyzer_params_sql(
            tokenizer="standard", tokenizer_params={}, filter_params=filter_params
        )

        assert result is not None
        sql_str = result.as_string()
        assert '"filter"' in sql_str
        assert "removepunct" in sql_str
        assert "mode" in sql_str

    def test_build_analyzer_params_with_pinyin_filter(self):
        """Test building analyzer params with pinyin filter."""
        filter_params = OrderedDict(
            [("pinyin", {"keep_first_letter": True, "keep_full_pinyin": True})]
        )

        result = build_analyzer_params_sql(
            tokenizer="pinyin", tokenizer_params={}, filter_params=filter_params
        )

        assert result is not None
        sql_str = result.as_string()
        assert '"filter"' in sql_str
        assert '"pinyin"' in sql_str

    def test_build_analyzer_params_with_multiple_filters(self):
        """Test building analyzer params with multiple filters."""
        filter_params = OrderedDict(
            [("lowercase", True), ("stop", ["the", "a"]), ("stemmer", "english")]
        )

        result = build_analyzer_params_sql(
            tokenizer="standard", tokenizer_params={}, filter_params=filter_params
        )

        assert result is not None
        sql_str = result.as_string()
        assert '"filter"' in sql_str
        assert '"lowercase"' in sql_str
        assert "stop" in sql_str
        assert "stemmer" in sql_str

    def test_build_analyzer_params_none_tokenizer(self):
        """Test building analyzer params with None tokenizer."""
        result = build_analyzer_params_sql(tokenizer=None)

        assert result is None

    def test_build_analyzer_params_invalid_lowercase_type(self):
        """Test building analyzer params with invalid lowercase type."""
        filter_params = OrderedDict([("lowercase", "invalid")])

        with pytest.raises(SqlError) as exc_info:
            build_analyzer_params_sql(
                tokenizer="standard", tokenizer_params={}, filter_params=filter_params
            )

        assert "Invalid value type for filter parameter 'lowercase'" in str(
            exc_info.value
        )

    def test_build_analyzer_params_invalid_stop_type(self):
        """Test building analyzer params with invalid stop type."""
        filter_params = OrderedDict([("stop", 123)])

        with pytest.raises(SqlError) as exc_info:
            build_analyzer_params_sql(
                tokenizer="standard", tokenizer_params={}, filter_params=filter_params
            )

        assert "Invalid value type for filter parameter 'stop'" in str(exc_info.value)

    def test_build_analyzer_params_invalid_stemmer_type(self):
        """Test building analyzer params with invalid stemmer type."""
        filter_params = OrderedDict([("stemmer", 123)])

        with pytest.raises(SqlError) as exc_info:
            build_analyzer_params_sql(
                tokenizer="standard", tokenizer_params={}, filter_params=filter_params
            )

        assert "Invalid value type for filter parameter 'stemmer'" in str(
            exc_info.value
        )

    def test_build_analyzer_params_invalid_length_type(self):
        """Test building analyzer params with invalid length type."""
        filter_params = OrderedDict([("length", "invalid")])

        with pytest.raises(SqlError) as exc_info:
            build_analyzer_params_sql(
                tokenizer="standard", tokenizer_params={}, filter_params=filter_params
            )

        assert "Invalid value type for filter parameter 'length'" in str(exc_info.value)

    def test_build_analyzer_params_invalid_removepunct_type(self):
        """Test building analyzer params with invalid removepunct type."""
        filter_params = OrderedDict([("removepunct", 123)])

        with pytest.raises(SqlError) as exc_info:
            build_analyzer_params_sql(
                tokenizer="standard", tokenizer_params={}, filter_params=filter_params
            )

        assert "Invalid value type for filter parameter 'removepunct'" in str(
            exc_info.value
        )

    def test_build_analyzer_params_invalid_pinyin_type(self):
        """Test building analyzer params with invalid pinyin type."""
        filter_params = OrderedDict([("pinyin", "invalid")])

        with pytest.raises(SqlError) as exc_info:
            build_analyzer_params_sql(
                tokenizer="pinyin", tokenizer_params={}, filter_params=filter_params
            )

        assert "Invalid value type for filter parameter 'pinyin'" in str(exc_info.value)

    def test_build_analyzer_params_invalid_filter_key(self):
        """Test building analyzer params with invalid filter key."""
        filter_params = OrderedDict([("invalid_filter", True)])

        with pytest.raises(SqlError) as exc_info:
            build_analyzer_params_sql(
                tokenizer="standard", tokenizer_params={}, filter_params=filter_params
            )

        assert "Invalid filter parameter: invalid_filter" in str(exc_info.value)


class TestBuildTokenizeSql:
    """Test cases for build_tokenize_sql function."""

    def test_build_tokenize_sql_with_column(self):
        """Test building tokenize SQL with column."""
        result = build_tokenize_sql(column="content", tokenizer="jieba")

        assert result is not None
        sql_str = result.as_string()
        assert "TOKENIZE" in sql_str
        assert "content" in sql_str
        assert "jieba" in sql_str

    def test_build_tokenize_sql_with_text(self):
        """Test building tokenize SQL with text."""
        result = build_tokenize_sql(text="Hello world", tokenizer="standard")

        assert result is not None
        sql_str = result.as_string()
        assert "TOKENIZE" in sql_str
        assert "Hello world" in sql_str
        assert "standard" in sql_str

    def test_build_tokenize_sql_with_tokenizer_params(self):
        """Test building tokenize SQL with tokenizer parameters."""
        tokenizer_params = {"max_token_length": 100}

        result = build_tokenize_sql(
            column="content", tokenizer="ik", tokenizer_params=tokenizer_params
        )

        assert result is not None
        sql_str = result.as_string()
        assert "TOKENIZE" in sql_str

    def test_build_tokenize_sql_with_filter_params(self):
        """Test building tokenize SQL with filter parameters."""
        filter_params = OrderedDict([("lowercase", True)])

        result = build_tokenize_sql(
            column="content", tokenizer="standard", filter_params=filter_params
        )

        assert result is not None
        sql_str = result.as_string()
        assert "TOKENIZE" in sql_str

    def test_build_tokenize_sql_no_column_or_text(self):
        """Test building tokenize SQL without column or text raises error."""
        with pytest.raises(SqlError) as exc_info:
            build_tokenize_sql(tokenizer="jieba")

        assert "Either column or text must be specified" in str(exc_info.value)

    def test_build_tokenize_sql_both_column_and_text(self):
        """Test building tokenize SQL with both column and text raises error."""
        with pytest.raises(SqlError) as exc_info:
            build_tokenize_sql(column="content", text="Hello", tokenizer="jieba")

        assert "Only one of column or text can be specified" in str(exc_info.value)


class TestBuildTextSearchSql:
    """Test cases for build_text_search_sql function."""

    def test_build_text_search_sql_basic(self):
        """Test building basic text search SQL."""
        result = build_text_search_sql(column="content", expression="search term")

        assert result is not None
        sql_str = result.as_string()
        assert "TEXT_SEARCH" in sql_str
        assert "content" in sql_str
        assert "search term" in sql_str

    def test_build_text_search_sql_with_mode(self):
        """Test building text search SQL with mode."""
        result = build_text_search_sql(
            column="content", expression="search term", mode="phrase"
        )

        assert result is not None
        sql_str = result.as_string()
        assert "TEXT_SEARCH" in sql_str
        assert "mode" in sql_str
        assert "phrase" in sql_str

    def test_build_text_search_sql_with_operator(self):
        """Test building text search SQL with operator."""
        result = build_text_search_sql(
            column="content", expression="search term", operator="AND"
        )

        assert result is not None
        sql_str = result.as_string()
        assert "TEXT_SEARCH" in sql_str
        assert "operator" in sql_str
        assert "AND" in sql_str

    def test_build_text_search_sql_with_tokenizer(self):
        """Test building text search SQL with tokenizer."""
        result = build_text_search_sql(
            column="content", expression="search term", tokenizer="jieba"
        )

        assert result is not None
        sql_str = result.as_string()
        assert "TEXT_SEARCH" in sql_str
        assert "tokenizer" in sql_str
        assert "jieba" in sql_str

    def test_build_text_search_sql_with_tokenizer_params(self):
        """Test building text search SQL with tokenizer parameters."""
        tokenizer_params = {"max_token_length": 100}

        result = build_text_search_sql(
            column="content",
            expression="search term",
            tokenizer="ik",
            tokenizer_params=tokenizer_params,
        )

        assert result is not None
        sql_str = result.as_string()
        assert "TEXT_SEARCH" in sql_str

    def test_build_text_search_sql_with_filter_params(self):
        """Test building text search SQL with filter parameters."""
        filter_params = OrderedDict([("lowercase", True)])

        result = build_text_search_sql(
            column="content",
            expression="search term",
            tokenizer="standard",
            tokenizer_params={},
            filter_params=filter_params,
        )

        assert result is not None
        sql_str = result.as_string()
        assert "TEXT_SEARCH" in sql_str
        assert "analyzer_params" in sql_str

    def test_build_text_search_sql_with_options(self):
        """Test building text search SQL with additional options."""
        result = build_text_search_sql(
            column="content", expression="search term", slop=2, boost=1.5
        )

        assert result is not None
        sql_str = result.as_string()
        assert "TEXT_SEARCH" in sql_str
        assert "options" in sql_str

    def test_build_text_search_sql_comprehensive(self):
        """Test building text search SQL with all parameters."""
        filter_params = OrderedDict([("lowercase", True), ("stop", ["the", "a"])])

        result = build_text_search_sql(
            column="content",
            expression="search term",
            mode="natural_language",
            operator="OR",
            tokenizer="jieba",
            tokenizer_params={"mode": "search"},
            filter_params=filter_params,
            slop=2,
        )

        assert result is not None
        sql_str = result.as_string()
        assert "TEXT_SEARCH" in sql_str
        assert "mode" in sql_str
        assert "operator" in sql_str
        assert "tokenizer" in sql_str
