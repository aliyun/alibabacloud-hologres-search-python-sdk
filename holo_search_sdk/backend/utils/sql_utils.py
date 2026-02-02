"""
SQL utility functions for Holo Search SDK.

Contains helper functions for building SQL queries.
"""

from collections import OrderedDict
from typing import Dict, List, Optional, Union

from psycopg import sql as psql
from typing_extensions import LiteralString

from ...exceptions import SqlError
from ...types import (
    PinyinFilterParamType,
    TextFilterType,
    TextSearchModeType,
    TextSearchOperatorType,
    TokenizerType,
)


def build_analyzer_params_sql(
    tokenizer: Optional[TokenizerType] = None,
    tokenizer_params: Optional[Dict[str, Union[str, int, bool]]] = None,
    filter_params: Optional[
        "OrderedDict[TextFilterType, Union[str, int, bool, List[str], Dict[PinyinFilterParamType, Union[int, bool]]]]"
    ] = None,
) -> Optional[psql.Composable]:
    if tokenizer is None or (tokenizer_params is None and filter_params is None):
        return None
    # Build tokenizer parameters
    tokenizer_params_sql: list[psql.Composable] = [
        psql.SQL('"type":{}').format(psql.Identifier(tokenizer))
    ]
    if tokenizer_params:
        for key, value in tokenizer_params.items():
            if isinstance(value, str):
                tokenizer_params_sql.append(
                    psql.SQL("{}: {}").format(
                        psql.Identifier(key), psql.Identifier(value)
                    )
                )
            else:
                tokenizer_params_sql.append(
                    psql.SQL("{}: {}").format(psql.Identifier(key), value)
                )
    analyzer_params = psql.SQL('"tokenizer": {{{}}}').format(
        psql.SQL(", ").join(tokenizer_params_sql)
    )

    # Build filter parameters
    if filter_params:
        filter_params_sql: list[psql.Composable] = []
        for key, value in filter_params.items():
            if key == "lowercase":
                if isinstance(value, bool):
                    if value:
                        filter_params_sql.append(psql.SQL('"lowercase"'))
                else:
                    raise SqlError(
                        "Invalid value type for filter parameter 'lowercase'"
                    )
            elif key == "stop":
                if isinstance(value, list):
                    filter_params_sql.append(
                        psql.SQL('{{"type": "stop", "stop_words":[{}]}}').format(
                            psql.SQL(", ").join(map(psql.Identifier, value))
                        )
                    )
                elif isinstance(value, str):
                    filter_params_sql.append(
                        psql.SQL('{{"type": "stop", "stop_words":[{}]}}').format(
                            psql.Identifier(value)
                        )
                    )
                else:
                    raise SqlError("Invalid value type for filter parameter 'stop'")
            elif key == "stemmer":
                if isinstance(value, str):
                    filter_params_sql.append(
                        psql.SQL('{{"type": "stemmer", "language":{}}}').format(
                            psql.Identifier(value)
                        )
                    )
                else:
                    raise SqlError("Invalid value type for filter parameter 'stemmer'")
            elif key == "length":
                if isinstance(value, int):
                    filter_params_sql.append(
                        psql.SQL('{{"type": "length", "max":{}}}').format(
                            psql.Literal(value)
                        )
                    )
                else:
                    raise SqlError("Invalid value type for filter parameter 'length'")
            elif key == "removepunct":
                if isinstance(value, bool):
                    if value:
                        filter_params_sql.append(psql.SQL('"removepunct"'))
                elif isinstance(value, str):
                    filter_params_sql.append(
                        psql.SQL('{{"type": "removepunct", "mode":{}}}').format(
                            psql.Identifier(value)
                        )
                    )
                else:
                    raise SqlError(
                        "Invalid value type for filter parameter 'removepunct'"
                    )
            elif key == "pinyin":
                if isinstance(value, dict):
                    pinyin_params_sql: list[psql.Composable] = []
                    for k, v in value.items():
                        pinyin_params_sql.append(
                            psql.SQL("{}: {}").format(psql.Identifier(k), v)
                        )
                    filter_params_sql.append(
                        psql.SQL('{{"type": "pinyin", {}}}').format(
                            psql.SQL(", ").join(pinyin_params_sql)
                        )
                    )
                else:
                    raise SqlError("Invalid value type for filter parameter 'pinyin'")
            else:
                raise SqlError(f"Invalid filter parameter: {key}")

        if len(filter_params_sql) > 0:
            analyzer_params += psql.SQL(', "filter": [{}]').format(
                psql.SQL(", ").join(filter_params_sql)
            )
    return psql.SQL("'{{{}}}'").format(analyzer_params)


def build_tokenize_sql(
    column: Optional[LiteralString] = None,
    text: Optional[str] = None,
    tokenizer: Optional[TokenizerType] = None,
    tokenizer_params: Optional[Dict[str, Union[str, int, bool]]] = None,
    filter_params: Optional[
        "OrderedDict[TextFilterType, Union[str, int, bool, List[str], Dict[PinyinFilterParamType, Union[int, bool]]]]"
    ] = None,
) -> psql.Composable:
    if column is None and text is None:
        raise SqlError("Either column or text must be specified.")
    if column is not None and text is not None:
        raise SqlError("Only one of column or text can be specified.")
    analyzer_params = build_analyzer_params_sql(
        tokenizer,
        tokenizer_params,
        filter_params,
    )
    if column:
        search_data = psql.SQL(column)
    else:
        search_data = psql.Literal(text)
    if analyzer_params:
        return psql.SQL("TOKENIZE({}, {}, {})").format(
            search_data,
            psql.Literal(tokenizer),
            analyzer_params,
        )
    else:
        return psql.SQL("TOKENIZE({}, {})").format(
            search_data,
            psql.Literal(tokenizer),
        )


def build_text_search_sql(
    column: LiteralString,
    expression: str,
    mode: Optional[TextSearchModeType] = None,
    operator: Optional[TextSearchOperatorType] = None,
    tokenizer: Optional[TokenizerType] = None,
    tokenizer_params: Optional[Dict[str, Union[str, int, bool]]] = None,
    filter_params: Optional[
        "OrderedDict[TextFilterType, Union[str, int, bool, List[str], Dict[PinyinFilterParamType, Union[int, bool]]]]"
    ] = None,
    **kwargs,
) -> psql.Composable:
    analyzer_params = build_analyzer_params_sql(
        tokenizer,
        tokenizer_params,
        filter_params,
    )
    search_sqls: list[psql.Composable] = [
        psql.SQL(column),
        psql.Literal(expression),
    ]
    if mode:
        search_sqls.append(psql.SQL("mode => {}").format(psql.Literal(mode)))
    if operator:
        search_sqls.append(psql.SQL("operator => {}").format(psql.Literal(operator)))
    if tokenizer:
        search_sqls.append(psql.SQL("tokenizer => {}").format(psql.Literal(tokenizer)))
    if analyzer_params:
        search_sqls.append(psql.SQL("analyzer_params => {}").format(analyzer_params))
    options = ""
    for key, value in kwargs.items():
        if value:
            options += f"{key}={value};"
    if len(options) > 0:
        search_sqls.append(psql.SQL("options => {}").format(psql.Literal(options)))
    return psql.SQL("TEXT_SEARCH({})").format(psql.SQL(", ").join(search_sqls))
