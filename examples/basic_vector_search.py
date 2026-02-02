"""
Basic vector search example for Holo Search SDK.
"""

import holo_search_sdk as holo


def main():
    """Demonstrate basic SDK usage."""

    # Connect to Hologres
    client = holo.connect(
        host="localhost",
        port=80,
        database="holo_search_sdk",
        access_key_id="access_key_id",
        access_key_secret="access_key_secret",
    )

    # Create table
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS test_table (
            id BIGINT PRIMARY KEY,
            feature1 FLOAT4[] CHECK (array_ndims(feature1) = 1 AND array_length(feature1, 1) = 4),
            feature2 FLOAT4[], name TEXT
        );
    """
    _ = client.execute(create_table_sql, fetch_result=False)
    holo_table = client.open_table("test_table")
    print(f"Table '{holo_table.get_name()}' created successfully.")

    # Set vector index
    holo_table.set_vector_index(
        "feature1", "Cosine", base_quantization_type="sq8_uniform"
    )
    print("Vector index set successfully for column 'feature1'.")

    # insert data
    holo_table.insert_multi(
        [
            [1, [0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8], "Alice"],
            [2, [1.1, 1.2, 1.3, 1.4], [1.5, 1.6, 1.7, 1.8], "Bob"],
            [3, [2.1, 2.2, 2.3, 2.4], [2.5, 2.6, 2.7, 2.8], "Bob"],
        ]
    )
    print("Data inserted successfully.")

    # Get vector index info
    print(f"Vector index info: {holo_table.get_vector_index_info()}")

    # Search vector
    query_result1 = (
        holo_table.search_vector(
            [0.3, 0.4, 0.5, 0.6], "feature1", output_name="distance"
        )
        .min_distance(0.7)
        .fetchall()
    )
    print(f"Query result1: {query_result1}")
    query_result2 = (
        holo_table.search_vector(
            [0.3, 0.4, 0.5, 0.6], column="feature1", output_name="distance"
        )
        .select("id")
        .where("name = 'Bob'")
        .limit(1)
        .fetchone()
    )
    print(f"Query result2: {query_result2}")

    # get vector by key
    query_result3 = holo_table.get_by_key("id", 1).fetchone()
    print(f"Query result3: {query_result3}")
    query_result4 = holo_table.get_multi_by_keys("id", [1, 2]).fetchall()
    print(f"Query result4: {query_result4}")


if __name__ == "__main__":
    main()
