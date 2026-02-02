"""
Type definitions for Holo Search SDK.

Defines common data types and structures used throughout the SDK.
"""

from dataclasses import dataclass
from typing import Dict, Literal

from typing_extensions import LiteralString


@dataclass
class ConnectionConfig:
    """Configuration for database connections."""

    host: str
    port: int
    database: str
    access_key_id: str
    access_key_secret: str
    schema: str = "public"
    autocommit: bool = False


# Type aliases used for Vector Search
DistanceType = Literal["Euclidean", "InnerProduct", "Cosine"]
BaseQuantizationType = Literal["sq8", "sq8_uniform", "fp16", "fp32", "rabitq"]
PreciseQuantizationType = Literal["sq8", "sq8_uniform", "fp16", "fp32"]
PreciseIOType = Literal["block_memory_io", "reader_io"]


# Functions for Vector Search
VectorSearchFunction: Dict[DistanceType, LiteralString] = {
    "Euclidean": "approx_euclidean_distance",
    "InnerProduct": "approx_inner_product_distance",
    "Cosine": "approx_cosine_distance",
}


# Type aliases used for Text Search
TokenizerType = Literal[
    "jieba",
    "ik",
    "icu",
    "whitespace",
    "standard",
    "keyword",
    "simple",
    "ngram",
    "pinyin",
]
TextFilterType = Literal[
    "lowercase", "stop", "stemmer", "length", "removepunct", "pinyin"
]
TextSearchModeType = Literal["match", "phrase", "natural_language", "term"]
TextSearchOperatorType = Literal["AND", "OR"]
PinyinFilterParamType = Literal[
    "keep_first_letter",
    "keep_separate_first_letter",
    "keep_full_pinyin",
    "keep_joined_full_pinyin",
    "keep_none_chinese",
    "keep_none_chinese_together",
    "none_chinese_pinyin_tokenize",
    "keep_original",
    "limit_first_letter_length",
    "lowercase",
    "trim_whitespace",
    "keep_none_chinese_in_first_letter",
    "keep_none_chinese_in_joined_full_pinyin",
    "remove_duplicated_term",
    "ignore_pinyin_offset",
    "fixed_pinyin_offset",
    "keep_separate_chinese",
]
