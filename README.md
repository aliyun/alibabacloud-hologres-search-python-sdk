# Holo Search SDK

**[中文文档](README_CN.md)**

A Python SDK for Hologres data retrieval operations, supporting vector search and full-text indexing.

## ✨ Attributes

- **🔍 Vector search**: Retrieval feature based on semantic similarity
- **📝 Full-text index**: Traditional keyword-based retrieval
- **💾 CRUD operations**: Full create, read, update, delete capabilities (upsert, update, delete, truncate, overwrite)
- **🛡️ Type safety**: Uses type hints and Data Validation
- **🧩 Modular design**: Clear layered architecture for easy extension and maintenance

## 📦 Install

### Install from PyPI

```bash
pip install holo-search-sdk
```

## 🚀 Get started

### Basic usage

```python
import holo_search_sdk as holo

# Connect to database
client = holo.connect(
    host="your-host",
    port=80,
    database="your-database",
    access_key_id="your-access-key-id",
    access_key_secret="your-access-key-secret",
    schema="public"
)

# Establish connection
client.connect()

# Open table
columns = {
    "id": ("INTEGER", "PRIMARY KEY"),
    "content": "TEXT",
    "vector": "FLOAT4[]"
}
table = client.open_table("table_name")

# Insert data
data = [
    [1, "Hello world", [0.1, 0.2, 0.3]],
    [2, "Python SDK", [0.4, 0.5, 0.6]],
    [3, "Vector search", [0.7, 0.8, 0.9]]
]
table.insert_multi(data, ["id", "content", "vector"])

# Set vector index
table.set_vector_index(
    column="vector",
    distance_method="Cosine",
    base_quantization_type="rabitq",
    max_degree=64,
    ef_construction=400
)

# Vector search
query_vector = [0.1, 0.2, 0.3]
# Limit results
results = table.search_vector(query_vector, "vector").limit(10).fetchall()
# Set minimum distance
results = table.search_vector(query_vector, "vector").min_distance(0.5).fetchall()

# Close connection
client.disconnect()
```

### Use context manager

```python
import holo_search_sdk as holo

with holo.connect(
    host="your-host",
    port=80,
    database="your-database",
    access_key_id="your-access-key-id",
    access_key_secret="your-access-key-secret"
) as client:
    client.connect()
    
# Execute database operations
    table = client.open_table("table_name")
    results = table.search_vector([0.1, 0.2, 0.3], "vector_column").fetchall()
    
# Connection will close automatically
```

## 📚 Detailed document

### Core concepts

#### 1. Client

The client is the primary API for interacting with the database:

```python
from holo_search_sdk import connect

# Create client
client = connect(
    host="localhost",
    port=80,
    database="test_db",
    access_key_id="your_key",
    access_key_secret="your_secret"
)

# Establish connection
client.connect()

# Execute SQL
result = client.execute("SELECT COUNT(*) FROM users", fetch_result=True)

# Table operations
table = client.open_table("table_name")
```

#### 2. Table Operations

Table is the basic unit of data storage and search:

```python
# Open existing table
table = client.open_table("table_name")

# Check if table exists
exists = client.check_table_exist("table_name")

# Delete
client.drop_table("table_name")
```

#### 3. Data insert

Supports single and batch data inserts:

```python
# Insert single record
table.insert_one(
[1, "title", "Content", [0.1, 0.2, 0.3]],
    ["id", "title", "content", "vector"]
)

# Bulk insert
data = [
[1, "document1", "Content1", [0.1, 0.2, 0.3]],
[2, "document2", "Content2", [0.4, 0.5, 0.6]],
[3, "document3", "Content3", [0.7, 0.8, 0.9]]
]
table.insert_multi(data, ["id", "title", "content", "vector"])
```

#### 4. CRUD operations

Supports full create, read, update, and delete operations:

```python
# Upsert (insert or update)
# Single upsert
table.upsert_one(
    index_column="id",
    values=[1, "updated content", [0.1, 0.2, 0.3]],
    column_names=["id", "content", "vector"],
    update=True  # Perform update on conflict
)

# Batch upsert
table.upsert_multi(
    index_column="id",
    values=[
        [1, "content1", [0.1, 0.2, 0.3]],
        [2, "content2", [0.4, 0.5, 0.6]]
    ],
    column_names=["id", "content", "vector"],
    update=True,
    update_columns=["content", "vector"]  # Columns to update on conflict
)

# Update
table.update(
    columns=["content", "updated_at"],
    values=["new content", "2026-01-22"],
    condition="id = 1"
)

# Update with table alias and FROM clause
table.update(
    columns=["status"],
    values=["active"],
    table_alias="t1",
    from_table="other_table",
    from_alias="t2",
    condition="t1.id = t2.ref_id AND t2.flag = true"
)

# Delete
table.delete("id > 100")  # Delete records matching the condition

# Truncate
table.truncate()  # Remove all data from the table while keeping the schema

# Overwrite - using values
table.overwrite(
    values=[
        [1, "new data1", [0.1, 0.2, 0.3]],
        [2, "new data2", [0.4, 0.5, 0.6]]
    ]
)

# Overwrite - using query results
source_table = client.open_table("source_table")
table.overwrite(
    values_expression=source_table.select("*").where("active = true")
)

# Drop table
table.drop()
```

#### 5. Vector index

Create efficient retrieval indexes for vector columns:

```python
# Set single vector index
table.set_vector_index(
    column="vector",
distance_method="Cosine",  # Optional: "Euclidean", "InnerProduct", "Cosine"
base_quantization_type="rabitq",  # Optional: "sq8", "sq8_uniform", "fp16", "fp32", "rabitq"
    max_degree=64,
    ef_construction=400,
    use_reorder=True,
    precise_quantization_type="fp32",
max_total_size_to_merge_mb=4096,  # Maximum File Size of Data when merging on disk, in MB
build_thread_count=16  # Number of threads used during index Build procedure
)

# Set multiple vector indexes
table.set_vector_indexes({
    "content_vector": {
        "distance_method": "Cosine",
        "base_quantization_type": "rabitq",
        "max_degree": 64,
        "ef_construction": 400,
        "use_reorder": True,
        "precise_quantization_type": "fp32",
        "max_total_size_to_merge_mb": 4096,
        "build_thread_count": 16
    },
    "title_vector": {
        "distance_method": "Euclidean",
        "base_quantization_type": "rabitq",
        "max_degree": 32,
        "ef_construction": 200,
        "use_reorder": True,
        "precise_quantization_type": "fp32",
        "max_total_size_to_merge_mb": 4096,
        "build_thread_count": 16
    }
})

# Delete all vector indexes
table.delete_vector_indexes()
```

#### 6. Vector search

Execute semantic similarity retrieval:

```python
# Basic vector search
query_vector = [0.1, 0.2, 0.3]
results = table.search_vector(
    vector=query_vector,
    column="vector",
    distance_method="Cosine"
).fetchall()

# Retrieval with outputs alias
results = table.search_vector(
    vector=query_vector,
    column="vector",
    output_name="similarity_score",
    distance_method="Cosine"
).fetchall()
```

#### 7. Data query

Supports primary key-based term query:

```python
# Query single record by primary key
result = table.get_by_key(
    key_column="id",
    key_value=1,
return_columns=["id", "content", "vector"]  # Optional. If not specified, returns all columns
).fetchone()

# Batch query by primary key list
results = table.get_multi_by_keys(
    key_column="id", 
    key_values=[1, 2, 3],
return_columns=["id", "content"]  # Optional. If not specified, returns all columns
).fetchall()
```

#### 8. Vector index management

Query and manage vector index information:

```python
# Retrieve vector index information
index_info = table.get_vector_index_info()
if index_info:
print("Current vector index configuration:", index_info)
else:
print("Vector index configuration not found")

# Index information sample return format
# {
#     "vector_column": {
#         "algorithm": "HGraph",
#         "distance_method": "Cosine",
#         "builder_params": {
#             "max_degree": 64,
#             "ef_construction": 400,
#             "base_quantization_type": "rabitq",
#             "use_reorder": true,
#             "precise_quantization_type": "fp32",
#             "precise_io_type": "block_memory_io",
#             "max_total_size_to_merge_mb": 4096,
#             "build_thread_count": 16
#         }
#     }
# }

# Get all vector column dimensions
all_dims = table.get_all_vector_column_dimensions()
print("All vector column dimensions:", all_dims)
# Sample output: {"feature1": [128], "feature2": [256]}

# Get specific vector column dimension
feature_dim = table.get_vector_column_dimension("feature1")
print("feature1 dimension:", feature_dim)
# Sample output: [128]
```

#### 9. Full-text index

Create a full-text index for text columns:

```python
# Create a full-text index
table.create_text_index(
    index_name="ft_idx_content",
    column="content",
tokenizer="jieba"  # Optional: "jieba", "ik", "icu", "whitespace", "standard", "simple", "keyword", "ngram", "pinyin"
)

# Set full-text index (modify the tokenizer of an existing index)
table.set_text_index(
    index_name="ft_idx_content",
    tokenizer="ik"
)

# Delete a full-text index
table.drop_text_index(index_name="ft_idx_content")
```

#### 10. Full-text retrieval

Execute a full-text retrieval query:

```python
# Basic full-text retrieval
results = table.search_text(
    column="content",
    expression="machine learning",
    return_all_columns=True
).fetchall()

# Full-text retrieval with scores returned
results = table.search_text(
    column="content",
    expression="deep learning",
    return_score=True,
    return_score_name="relevance_score"
).select(["id", "title", "content"]).fetchall()

# Use different retrieval patterns
# Keyword pattern (default)
results = table.search_text(
    column="content",
    expression="python programming",
    mode="match",
operator="AND"  # Require containing all keywords
).fetchall()

# Phrase pattern
results = table.search_text(
    column="content",
    expression="machine learning",
mode="phrase"  # Exact phrase match
).fetchall()

# Natural language pattern
results = table.search_text(
    column="content",
expression="+python -java",  # Must contain python, cannot contain java
    mode="natural_language"
).fetchall()

# Term retrieval
results = table.search_text(
    column="content",
    expression="python",
mode="term" # Do not perform tokenization or other processing on the expression. Directly perform an exact match in the index
).fetchall()
```

#### 11. Advanced query build

Use the query builder to perform complex queries:

```python
# Combine full-text search and filter conditions
results = (
    table.search_text(
        column="content",
        expression="artificial intelligence",
        return_score=True,
        return_score_name="score"
    )
    .where("publish_date > '2023-01-01'")
    .order_by("score", "desc")
    .limit(10)
    .fetchall()
)

# Use filter expressions
from holo_search_sdk import Filter, AndFilter, OrFilter, NotFilter

results = (
    table.select(["id", "title", "content"])
    .where(
        AndFilter(
            Filter("category = 'technology'"),
            Filter("views > 1000")
        )
    )
    .order_by("views", "desc")
    .fetchall()
)

# Use OR filter expressions
results = (
    table.select(["id", "title", "content"])
    .where(
        Filter("category = 'technology'") | Filter("views > 1000")
    )
    .order_by("views", "desc")
    .fetchall()
)

# Use the tokenization feature
results = (
    table.select(["id", "content"])
    .select_tokenize(
        column="content",
        tokenizer="jieba",
        output_name="tokens"
    )
    .limit(5)
    .fetchall()
)
```

#### 12. Table join query

Support multi-table join queries:

```python
# Inner join
table1 = client.open_table("articles", table_alias="a")
table2 = client.open_table("authors", table_alias="b")

results = (
    table1.select(["a.id", "a.title", "b.name"])
    .inner_join(table2, "a.author_id = b.id")
    .where("a.publish_date > '2023-01-01'")
    .fetchall()
)

# Left join
results = (
    table1.select(["a.id", "a.title", "b.name"])
    .left_join(table2, "a.author_id = b.id")
    .fetchall()
)
```

### Configuration options

#### Connection configuration

```python
from holo_search_sdk.types import ConnectionConfig

config = ConnectionConfig(
    host="your-host.com",
    port=80,
    database="production_db",
    access_key_id="user...",
    access_key_secret="secret...",
schema="analytics"  # The default is "public"
)
```

#### Vector index configuration

- **distance_method**: Distance computation method
- `"Euclidean"`: Euclidean distance
- `"InnerProduct"`: Inner product distance
- `"Cosine"`: Cosine distance

- **base_quantization_type**: Base quantization type
  - `"sq8"`, `"sq8_uniform"`, `"fp16"`, `"fp32"`, `"rabitq"`
- **max_degree**: The quantity of nearest neighbors that each vertex attempts to connect to during the graph build procedure (default: 64)
- **ef_construction**: Retrieval depth control during the graph build procedure (default: 400)
- **use_reorder**: Specifies whether to use the HGraph high-precision index (default: False)
- **precise_quantization_type**: Precise quantization type (default: "fp32")
- **precise_io_type**: Precise IO type (default: "block_memory_io")
- **max_total_size_to_merge_mb**: The maximum file size of data during disk merge, in MB (default: 4096)
- **build_thread_count**: The number of threads used during the index build procedure (default: 16)

#### Full-text search configuration

- **tokenizer**: Tokenizer type
- **mode**: Full-text search mode
- `match`: Keyword match. Default.
- `phrase`: Phrase search
- `natural_language`: Natural language search
- `term`: Term search
- **operator**: Keyword search operator (Applicable only to match mode. Default: "OR")
- **Token filter**:
- `lowercase`: Converts uppercase letters in tokens to lowercase.
- `stop`: Removes stop word tokens.
- `stemmer`: Converts tokens to their corresponding stems based on the syntax rules of the corresponding language.
- `length`: Removes tokens that exceed the specified length.
- `removepunct`: Removes tokens that contain only punctuation characters.
- `pinyin`: Pinyin token filter

## 🔧 API Reference

### Main classes

- **`Client`**: Database client. It manages connections and table operations.
- **`HoloTable`**: Table operation API. It supports data insertion, vector search, and full-text search.
- **`QueryBuilder`**: Query builder. It supports chain invocation to build complex queries.
- **`ConnectionConfig`**: Connection configuration data class.

### Filter classes

- **`Filter`**: Basic filter expression.
- **`AndFilter`**: AND logic filter.
- **`OrFilter`**: OR logic filter.
- **`NotFilter`**: NOT logic filter.
- **`TextSearchFilter`**: Full-text search filter.

### Main functions

**Connection and Table Management:**
- **`connect()`**: Creates a database client connection.
- **`open_table()`**: Opens an existing table.
- **`check_table_exist()`**: Checks whether a table exists.
- **`drop_table()`**: Deletes a table.

**Data operation:**
- **`insert_one()`**: Inserts a single record.
- **`insert_multi()`**: Bulk inserts records.
- **`upsert_one()`**: Inserts or updates a single record (ON CONFLICT).
- **`upsert_multi()`**: Bulk inserts or updates records.
- **`update()`**: Updates records that match the given condition.
- **`delete()`**: Deletes records that match the given condition.
- **`truncate()`**: Removes all data from the table.
- **`overwrite()`**: Overwrites all data in the table.
- **`drop()`**: Drops the table.
- **`get_by_key()`**: Queries a single record based on the primary key.
- **`get_multi_by_keys()`**: Batch queries based on a primary key list.

**Vector search:**
- **`set_vector_index()`**: Sets a single vector index.
- **`set_vector_indexes()`**: Sets multiple vector indexes.
- **`delete_vector_indexes()`**: Deletes all vector indexes.
- **`get_vector_index_info()`**: Retrieves vector index information.
- **`get_all_vector_column_dimensions()`**: Retrieves all vector columns and their dimensions.
- **`get_vector_column_dimension()`**: Retrieves the dimension of a specific vector column.
- **`search_vector()`**: Executes vector search.

**Full-text search:**
- **`create_text_index()`**: Creates a full-text index.
- **`set_text_index()`**: Modifies a full-text index.
- **`drop_text_index()`**: Deletes a full-text index.
- **`get_index_properties()`**: Retrieves index properties.
- **`search_text()`**: Executes full-text search.

**Query building:**
- **`select()`**: Selects the columns to return
- **`where()`**: Adds filter conditions
- **`and_where()`**: Adds AND filter conditions
- **`or_where()`**: Adds OR filter conditions
- **`order_by()`**: Sorts the results
- **`group_by()`**: Groups the results
- **`limit()`**: Limits the quantity of results
- **`offset()`**: Skips the specified quantity of results
- **`join()`**: Table join
- **`inner_join()`**: Inner join
- **`left_join()`**: Left join
- **`right_join()`**: Right join
- **`select_tokenize()`**: Displays tokenization effects
- **`select_text_search()`**: Performs full-text search in SELECT
- **`where_text_search()`**: Performs full-text search filtering in WHERE

### Exception classes

- **`HoloSearchError`**: Base exception class
- **`ConnectionError`**: Connection-related errors
- **`QueryError`**: Query execution errors
- **`SqlError`**: SQL generation errors
- **`TableError`**: Table operation errors

## 📄 License

This project uses the MIT License - View the [LICENSE](LICENSE) file for details.

---

**Holo Search SDK** - Makes Hologres vector and full-text retrieval simple and efficient 🚀
