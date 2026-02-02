"""
Tests for type definitions in Holo Search SDK.

This module contains tests for data types and type validation.
"""

import pytest

from holo_search_sdk.types import (
    BaseQuantizationType,
    ConnectionConfig,
    DistanceType,
    PreciseIOType,
    PreciseQuantizationType,
    VectorSearchFunction,
)


class TestConnectionConfig:
    """Test cases for ConnectionConfig dataclass."""

    def test_connection_config_creation(self):
        """Test creating a ConnectionConfig instance."""
        config = ConnectionConfig(
            host="localhost",
            port=80,
            database="test_db",
            access_key_id="test_key_id",
            access_key_secret="test_key_secret",
            schema="public",
        )

        assert config.host == "localhost"
        assert config.port == 80
        assert config.database == "test_db"
        assert config.access_key_id == "test_key_id"
        assert config.access_key_secret == "test_key_secret"
        assert config.schema == "public"

    def test_connection_config_default_schema(self):
        """Test ConnectionConfig with default schema."""
        config = ConnectionConfig(
            host="localhost",
            port=80,
            database="test_db",
            access_key_id="test_key_id",
            access_key_secret="test_key_secret",
        )

        assert config.schema == "public"

    def test_connection_config_custom_schema(self):
        """Test ConnectionConfig with custom schema."""
        config = ConnectionConfig(
            host="localhost",
            port=80,
            database="test_db",
            access_key_id="test_key_id",
            access_key_secret="test_key_secret",
            schema="custom_schema",
        )

        assert config.schema == "custom_schema"

    def test_connection_config_equality(self):
        """Test ConnectionConfig equality comparison."""
        config1 = ConnectionConfig(
            host="localhost",
            port=80,
            database="test_db",
            access_key_id="test_key_id",
            access_key_secret="test_key_secret",
            schema="public",
        )

        config2 = ConnectionConfig(
            host="localhost",
            port=80,
            database="test_db",
            access_key_id="test_key_id",
            access_key_secret="test_key_secret",
            schema="public",
        )

        config3 = ConnectionConfig(
            host="different_host",
            port=80,
            database="test_db",
            access_key_id="test_key_id",
            access_key_secret="test_key_secret",
            schema="public",
        )

        assert config1 == config2
        assert config1 != config3

    def test_connection_config_repr(self):
        """Test ConnectionConfig string representation."""
        config = ConnectionConfig(
            host="localhost",
            port=80,
            database="test_db",
            access_key_id="test_key_id",
            access_key_secret="test_key_secret",
            schema="public",
        )

        repr_str = repr(config)
        assert "ConnectionConfig" in repr_str
        assert "localhost" in repr_str
        assert "80" in repr_str
        assert "test_db" in repr_str


class TestTypeAliases:
    """Test cases for type aliases."""

    def test_distance_type_values(self):
        """Test DistanceType literal values."""
        valid_distances = ["Euclidean", "InnerProduct", "Cosine"]

        # Test that all expected values are valid
        for distance in valid_distances:
            # This would fail at type checking if the literal doesn't match
            distance_var: DistanceType = distance  # type: ignore
            assert distance_var in valid_distances

    def test_base_quantization_type_values(self):
        """Test BaseQuantizationType literal values."""
        valid_quantizations = ["sq8", "sq8_uniform", "fp16", "fp32", "rabitq"]

        for quantization in valid_quantizations:
            quantization_var: BaseQuantizationType = quantization  # type: ignore
            assert quantization_var in valid_quantizations

    def test_precise_quantization_type_values(self):
        """Test PreciseQuantizationType literal values."""
        valid_precise_quantizations = ["sq8", "sq8_uniform", "fp16", "fp32"]

        for quantization in valid_precise_quantizations:
            quantization_var: PreciseQuantizationType = quantization  # type: ignore
            assert quantization_var in valid_precise_quantizations

    def test_precise_io_type_values(self):
        """Test PreciseIOType literal values."""
        valid_io_types = ["block_memory_io", "reader_io"]

        for io_type in valid_io_types:
            io_type_var: PreciseIOType = io_type  # type: ignore
            assert io_type_var in valid_io_types


class TestVectorSearchFunction:
    """Test cases for VectorSearchFunction mapping."""

    def test_vector_search_function_mapping(self):
        """Test VectorSearchFunction contains correct mappings."""
        expected_mappings = {
            "Euclidean": "approx_euclidean_distance",
            "InnerProduct": "approx_inner_product_distance",
            "Cosine": "approx_cosine_distance",
        }

        assert VectorSearchFunction == expected_mappings

    def test_vector_search_function_keys(self):
        """Test VectorSearchFunction has all expected keys."""
        expected_keys = {"Euclidean", "InnerProduct", "Cosine"}
        actual_keys = set(VectorSearchFunction.keys())

        assert actual_keys == expected_keys

    def test_vector_search_function_values(self):
        """Test VectorSearchFunction has all expected values."""
        expected_values = {
            "approx_euclidean_distance",
            "approx_inner_product_distance",
            "approx_cosine_distance",
        }
        actual_values = set(VectorSearchFunction.values())

        assert actual_values == expected_values

    def test_vector_search_function_access(self):
        """Test accessing VectorSearchFunction values."""
        assert VectorSearchFunction["Euclidean"] == "approx_euclidean_distance"
        assert VectorSearchFunction["InnerProduct"] == "approx_inner_product_distance"
        assert VectorSearchFunction["Cosine"] == "approx_cosine_distance"

    def test_vector_search_function_key_error(self):
        """Test VectorSearchFunction raises KeyError for invalid keys."""
        with pytest.raises(KeyError):
            _ = VectorSearchFunction["InvalidDistance"]


class TestTypeIntegration:
    """Integration tests for types working together."""

    def test_connection_config_with_all_types(self):
        """Test ConnectionConfig works with various data types."""
        config = ConnectionConfig(
            host="test.example.com",
            port=5432,
            database="production_db",
            access_key_id="AKIA1234567890",
            access_key_secret="secret123456789",
            schema="analytics",
        )

        # Test that all fields are properly set and accessible
        assert isinstance(config.host, str)
        assert isinstance(config.port, int)
        assert isinstance(config.database, str)
        assert isinstance(config.access_key_id, str)
        assert isinstance(config.access_key_secret, str)
        assert isinstance(config.schema, str)

        # Test specific values
        assert config.host == "test.example.com"
        assert config.port == 5432
        assert config.database == "production_db"
        assert config.access_key_id == "AKIA1234567890"
        assert config.access_key_secret == "secret123456789"
        assert config.schema == "analytics"

    def test_distance_type_with_vector_search_function(self):
        """Test DistanceType compatibility with VectorSearchFunction."""
        for distance_type in VectorSearchFunction.keys():
            # Verify each key in VectorSearchFunction is a valid DistanceType
            distance_var: DistanceType = distance_type  # type: ignore
            function_name = VectorSearchFunction[distance_var]
            assert isinstance(function_name, str)
            assert function_name.startswith("approx_")
            assert function_name.endswith("_distance")
