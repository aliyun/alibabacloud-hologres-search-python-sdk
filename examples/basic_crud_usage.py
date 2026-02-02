"""
Basic CRUD (Create, Read, Update, Delete) example for Holo Search SDK.
"""

import holo_search_sdk as holo


def main():
    """Demonstrate basic CRUD operations."""

    # 1. Connect to Hologres
    # Note: Replace with your actual connection details
    client = holo.connect(
        host="localhost",
        port=80,
        database="holo_search_sdk",
        access_key_id="access_key_id",
        access_key_secret="access_key_secret",
    )

    # 2. Setup: Create a table for demonstration
    table_name = "crud_example_table"
    # Use execute to run standard DDL
    create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INT PRIMARY KEY,
            name TEXT,
            age INT,
            city TEXT
        );
    """
    client.execute(create_table_sql, fetch_result=False)

    # Open the table for SDK operations
    table = client.open_table(table_name)
    print(f"Table '{table_name}' is ready.")

    # 3. Create (Insert)
    # Insert a single record
    table.insert_one([1, "Alice", 25, "New York"])

    # Insert multiple records
    table.insert_multi(
        [
            [2, "Bob", 30, "San Francisco"],
            [3, "Charlie", 22, "Los Angeles"],
            [4, "David", 35, "Chicago"],
        ]
    )
    print("Data inserted successfully.")

    # 4. Read (Query)
    # Read one record by primary key
    alice = table.get_by_key("id", 1).fetchone()
    print(f"Read by key (id=1): {alice}")

    # Read multiple records by keys
    others = table.get_multi_by_keys("id", [2, 3]).fetchall()
    print(f"Read by multiple keys (id in [2, 3]): {others}")

    # General query with filters, ordering, and limit
    results = (
        table.select(["name", "age"])
        .where("age > 25")
        .order_by("age", "asc")
        .limit(10)
        .fetchall()
    )
    print(f"Read with select and where (age > 25): {results}")

    # 5. Update
    # Update specific columns based on a condition
    table.update(columns=["age", "city"], values=[26, "Boston"], condition="id = 1")
    updated_alice = table.get_by_key("id", 1).fetchone()
    print(f"After update (id=1): {updated_alice}")

    # Upsert (Insert or Update on conflict)
    # If id=4 exists, update its name and age, otherwise insert.
    table.upsert_one(
        index_column="id",
        values=[4, "Dave", 36, "Chicago"],
        column_names=["id", "name", "age", "city"],
        update=True,
    )
    upserted_david = table.get_by_key("id", 4).fetchone()
    print(f"After upsert (id=4): {upserted_david}")

    # 6. Delete
    # Delete a record based on a condition
    table.delete("id = 3")

    # Verify deletion by counting records
    remaining_count = table.select("count(*)").fetchone()[0]
    print(f"After delete (id=3), remaining records: {remaining_count}")

    # 7. Truncate
    # Truncate removes all rows from the table but keeps the table structure
    table.truncate()
    count_after_truncate = table.select("count(*)").fetchone()[0]
    print(f"After truncate, record count: {count_after_truncate}")

    # Re-insert some data for overwrite demonstration
    table.insert_multi(
        [
            [1, "Alice", 26, "Boston"],
            [4, "Dave", 36, "Chicago"],
            [5, "Emma", 24, "Houston"],
        ]
    )
    print(
        f"Re-inserted data for overwrite demo. Current records: {table.select('*').fetchall()}"
    )

    # 8. Overwrite
    # Overwrite replaces all data in the table with new data
    # Method 1: Overwrite with values
    table.overwrite(
        values=[
            [10, "Eve", 28, "Seattle"],
            [11, "Frank", 32, "Portland"],
            [12, "Grace", 27, "Austin"],
        ]
    )
    count_after_overwrite = table.select("count(*)").fetchone()[0]
    print(f"After overwrite with values, record count: {count_after_overwrite}")

    # Verify overwrite content
    all_records = table.select("*").fetchall()
    print(f"Records after overwrite: {all_records}")

    # Method 2: Overwrite with query result from another table
    # Create a temporary source table
    source_table_name = "crud_source_table"
    create_source_sql = f"""
        CREATE TABLE IF NOT EXISTS {source_table_name} (
            id INT PRIMARY KEY,
            name TEXT,
            age INT,
            city TEXT
        );
    """
    client.execute(create_source_sql, fetch_result=False)
    source_table = client.open_table(source_table_name)

    # Insert data into source table
    source_table.insert_multi([[20, "Henry", 40, "Denver"], [21, "Iris", 29, "Miami"]])

    # Overwrite target table with data from source table
    table.overwrite(values_expression=source_table.select("*"))
    count_after_query_overwrite = table.select("count(*)").fetchone()[0]
    print(f"After overwrite with query, record count: {count_after_query_overwrite}")

    # Verify overwrite with query result
    final_records = table.select("*").fetchall()
    print(f"Final records after query overwrite: {final_records}")

    # 9. Cleanup: Drop the tables
    source_table.drop()
    print(f"Table '{source_table_name}' dropped.")

    table.drop()
    print(f"Table '{table_name}' dropped.")


if __name__ == "__main__":
    main()
