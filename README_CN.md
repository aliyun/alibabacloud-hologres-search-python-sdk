# Holo Search SDK

**[English Version](README.md)**

一个用于Hologres数据检索操作的 Python SDK，支持向量检索和全文检索功能。

## ✨ 特性

- **🔍 向量检索**: 基于语义相似性的检索功能
- **📝 全文检索**: 传统的基于关键词的检索
- **💾 CRUD 操作**: 完整的数据增删改查功能（upsert, update, delete, truncate, overwrite）
- **🛡️ 类型安全**: 使用类型提示和数据验证
- **🧩 模块化设计**: 清晰的分层架构，便于扩展和维护

## 📦 安装

### 从 PyPI 安装

```bash
pip install holo-search-sdk
```

## 🚀 快速开始

### 基本使用

```python
import holo_search_sdk as holo

# 连接到数据库
client = holo.connect(
    host="your-host",
    port=80,
    database="your-database",
    access_key_id="your-access-key-id",
    access_key_secret="your-access-key-secret",
    schema="public"
)

# 建立连接
client.connect()

# 打开表
table = client.open_table("table_name")

# 插入数据
data = [
    [1, "Hello world", [0.1, 0.2, 0.3]],
    [2, "Python SDK", [0.4, 0.5, 0.6]],
    [3, "Vector search", [0.7, 0.8, 0.9]]
]
table.insert_multi(data, ["id", "content", "vector"])

# 设置向量索引
table.set_vector_index(
    column="vector",
    distance_method="Cosine",
    base_quantization_type="rabitq",
    max_degree=64,
    ef_construction=400
)

# 向量检索
query_vector = [0.1, 0.2, 0.3]
# 限制结果数量
results = table.search_vector(query_vector, "vector").limit(10).fetchall()
# 设置最小距离
results = table.search_vector(query_vector, "vector").min_distance(0.5).fetchall()

# 关闭连接
client.disconnect()
```

### 使用上下文管理器

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
    
    # 执行数据库操作
    table = client.open_table("table_name")
    results = table.search_vector([0.1, 0.2, 0.3], "vector_column").fetchall()
    
    # 连接会自动关闭
```

## 📚 详细文档

### 核心概念

#### 1. 客户端 (Client)

客户端是与数据库交互的主要接口：

```python
from holo_search_sdk import connect

# 创建客户端
client = connect(
    host="localhost",
    port=80,
    database="test_db",
    access_key_id="your_key",
    access_key_secret="your_secret"
)

# 建立连接
client.connect()

# 执行 SQL
result = client.execute("SELECT COUNT(*) FROM users", fetch_result=True)

# 表操作
table = client.open_table("table_name")
```

#### 2. 表操作 (Table Operations)

表是数据存储和搜索的基本单位：

```python
# 打开现有表
table = client.open_table("table_name")

# 检查表是否存在
exists = client.check_table_exist("table_name")

# 删除表
client.drop_table("table_name")
```

#### 3. 数据插入

支持单条和批量数据插入：

```python
# 插入单条记录
table.insert_one(
    [1, "标题", "内容", [0.1, 0.2, 0.3]],
    ["id", "title", "content", "vector"]
)

# 批量插入
data = [
    [1, "文档1", "内容1", [0.1, 0.2, 0.3]],
    [2, "文档2", "内容2", [0.4, 0.5, 0.6]],
    [3, "文档3", "内容3", [0.7, 0.8, 0.9]]
]
table.insert_multi(data, ["id", "title", "content", "vector"])
```

#### 4. CRUD 操作

支持完整的数据增删改查操作：

```python
# Upsert（插入或更新）
# 单条 upsert
table.upsert_one(
    index_column="id",
    values=[1, "更新的内容", [0.1, 0.2, 0.3]],
    column_names=["id", "content", "vector"],
    update=True  # 冲突时执行更新
)

# 批量 upsert
table.upsert_multi(
    index_column="id",
    values=[
        [1, "内容1", [0.1, 0.2, 0.3]],
        [2, "内容2", [0.4, 0.5, 0.6]]
    ],
    column_names=["id", "content", "vector"],
    update=True,
    update_columns=["content", "vector"]  # 指定更新的列
)

# Update（更新）
table.update(
    columns=["content", "updated_at"],
    values=["新内容", "2026-01-22"],
    condition="id = 1"
)

# 带表别名和 FROM 子句的更新
table.update(
    columns=["status"],
    values=["active"],
    table_alias="t1",
    from_table="other_table",
    from_alias="t2",
    condition="t1.id = t2.ref_id AND t2.flag = true"
)

# Delete（删除）
table.delete("id > 100")  # 删除满足条件的记录

# Truncate（清空）
table.truncate()  # 清空表中所有数据，保留表结构

# Overwrite（覆盖）
# 方式1：使用值覆盖
table.overwrite(
    values=[
        [1, "新数据1", [0.1, 0.2, 0.3]],
        [2, "新数据2", [0.4, 0.5, 0.6]]
    ]
)

# 方式2：使用查询结果覆盖
source_table = client.open_table("source_table")
table.overwrite(
    values_expression=source_table.select("*").where("active = true")
)

# Drop（删除表）
table.drop()  # 删除整个表
```

#### 5. 向量索引

为向量列创建高效的检索索引：

```python
# 设置单个向量索引
table.set_vector_index(
    column="vector",
    distance_method="Cosine",  # 可选: "Euclidean", "InnerProduct", "Cosine"
    base_quantization_type="rabitq",  # 可选: "sq8", "sq8_uniform", "fp16", "fp32", "rabitq"
    max_degree=64,
    ef_construction=400,
    use_reorder=True,
    precise_quantization_type="fp32",
    max_total_size_to_merge_mb=4096,  # 磁盘合并时数据的最大文件大小，单位MB
    build_thread_count=16  # 索引构建过程中使用的线程数
)

# 设置多个向量索引
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

# 删除所有向量索引
table.delete_vector_indexes()
```

#### 6. 向量检索

执行语义相似性检索：

```python
# 基本向量检索
query_vector = [0.1, 0.2, 0.3]
results = table.search_vector(
    vector=query_vector,
    column="vector",
    distance_method="Cosine"
).fetchall()

# 带输出别名的检索
results = table.search_vector(
    vector=query_vector,
    column="vector",
    output_name="similarity_score",
    distance_method="Cosine"
).fetchall()
```

#### 7. 数据查询

支持基于主键的精确查询：

```python
# 根据主键查询单条记录
result = table.get_by_key(
    key_column="id",
    key_value=1,
    return_columns=["id", "content", "vector"]  # 可选，不指定则返回所有列
).fetchone()

# 根据主键列表批量查询
results = table.get_multi_by_keys(
    key_column="id", 
    key_values=[1, 2, 3],
    return_columns=["id", "content"]  # 可选，不指定则返回所有列
).fetchall()
```

#### 8. 向量索引管理

查询和管理向量索引信息：

```python
# 获取向量索引信息
index_info = table.get_vector_index_info()
if index_info:
    print("当前向量索引配置:", index_info)
else:
    print("未找到向量索引配置")

# 索引信息示例返回格式
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

# 获取所有向量列的维度
all_dims = table.get_all_vector_column_dimensions()
print("所有向量列维度:", all_dims)
# 示例输出: {"feature1": [128], "feature2": [256]}

# 获取特定向量列的维度
feature_dim = table.get_vector_column_dimension("feature1")
print("feature1 维度:", feature_dim)
# 示例输出: [128]
```

#### 9. 全文检索索引

为文本列创建全文检索索引：

```python
# 创建全文索引
table.create_text_index(
    index_name="ft_idx_content",
    column="content",
    tokenizer="jieba"  # 可选: "jieba", "ik", "icu", "whitespace", "standard", "simple", "keyword", "ngram", "pinyin"
)

# 设置全文索引（修改现有索引的分词器）
table.set_text_index(
    index_name="ft_idx_content",
    tokenizer="ik"
)

# 删除全文索引
table.drop_text_index(index_name="ft_idx_content")
```

#### 10. 全文检索

执行全文检索查询：

```python
# 基本全文检索
results = table.search_text(
    column="content",
    expression="机器学习",
    return_all_columns=True
).fetchall()

# 带分数返回的全文检索
results = table.search_text(
    column="content",
    expression="深度学习",
    return_score=True,
    return_score_name="relevance_score"
).select(["id", "title", "content"]).fetchall()

# 使用不同的检索模式
# 关键词模式（默认）
results = table.search_text(
    column="content",
    expression="python programming",
    mode="match",
    operator="AND"  # 要求同时包含所有关键词
).fetchall()

# 短语模式
results = table.search_text(
    column="content",
    expression="machine learning",
    mode="phrase"  # 精确短语匹配
).fetchall()

# 自然语言模式
results = table.search_text(
    column="content",
    expression="+python -java",  # 必须包含python，不能包含java
    mode="natural_language"
).fetchall()

# 术语检索
results = table.search_text(
    column="content",
    expression="python",
    mode="term" # 对expression不做分词或其他处理，直接去索引中精确匹配
).fetchall()
```

#### 11. 高级查询构建

使用查询构建器进行复杂查询：

```python
# 组合全文检索和过滤条件
results = (
    table.search_text(
        column="content",
        expression="人工智能",
        return_score=True,
        return_score_name="score"
    )
    .where("publish_date > '2023-01-01'")
    .order_by("score", "desc")
    .limit(10)
    .fetchall()
)

# 使用过滤器表达式
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

# 使用或过滤器表达式
results = (
    table.select(["id", "title", "content"])
    .where(
        Filter("category = 'technology'") | Filter("views > 1000")
    )
    .order_by("views", "desc")
    .fetchall()
)

# 使用分词功能
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

#### 12. 表连接查询

支持多表连接查询：

```python
# 内连接
table1 = client.open_table("articles", table_alias="a")
table2 = client.open_table("authors", table_alias="b")

results = (
    table1.select(["a.id", "a.title", "b.name"])
    .inner_join(table2, "a.author_id = b.id")
    .where("a.publish_date > '2023-01-01'")
    .fetchall()
)

# 左连接
results = (
    table1.select(["a.id", "a.title", "b.name"])
    .left_join(table2, "a.author_id = b.id")
    .fetchall()
)
```

### 配置选项

#### 连接配置

```python
from holo_search_sdk.types import ConnectionConfig

config = ConnectionConfig(
    host="your-host.com",
    port=80,
    database="production_db",
    access_key_id="user...",
    access_key_secret="secret...",
    schema="analytics"  # 默认为 "public"
)
```

#### 向量索引配置

- **distance_method**: 距离计算方法
  - `"Euclidean"`: 欧几里得距离
  - `"InnerProduct"`: 内积距离
  - `"Cosine"`: 余弦距离

- **base_quantization_type**: 基础量化类型
  - `"sq8"`, `"sq8_uniform"`, `"fp16"`, `"fp32"`, `"rabitq"`
- **max_degree**: 图构建过程中每个顶点尝试连接的最近邻数量 (默认: 64)
- **ef_construction**: 图构建过程中的检索深度控制 (默认: 400)
- **use_reorder**: 是否使用 HGraph 高精度索引 (默认: False)
- **precise_quantization_type**: 精确量化类型 (默认: "fp32")
- **precise_io_type**: 精确 IO 类型 (默认: "block_memory_io")
- **max_total_size_to_merge_mb**: 磁盘合并时数据的最大文件大小，单位MB (默认: 4096)
- **build_thread_count**: 索引构建过程中使用的线程数 (默认: 16)

#### 全文检索配置

- **tokenizer**: 分词器类型
- **mode**: 全文检索模式
  - `match`:关键词匹配，默认
  - `phrase`:短语检索
  - `natural_language`:自然语言检索
  - `term`:术语检索
- **operator**: 关键词检索操作符 (仅适用于match模式, 默认: "OR")
- *分词过滤器**:
  - `lowercase`: 将token中的大写字母转为小写
  - `stop`: 移除停用词token
  - `stemmer`: 根据对应语言的语法规则将token转化为其对应的词干
  - `length`: 移除超过指定长度的token
  - `removepunct`: 移除只包含标点符号字符的token。
  - `pinyin`: 拼音Token Filter

## 🔧 API 参考

### 主要类

- **`Client`**: 数据库客户端，管理连接和表操作
- **`HoloTable`**: 表操作接口，支持数据插入、向量检索和全文检索
- **`QueryBuilder`**: 查询构建器，支持链式调用构建复杂查询
- **`ConnectionConfig`**: 连接配置数据类

### 过滤器类

- **`Filter`**: 基础过滤器表达式
- **`AndFilter`**: AND 逻辑过滤器
- **`OrFilter`**: OR 逻辑过滤器
- **`NotFilter`**: NOT 逻辑过滤器
- **`TextSearchFilter`**: 全文检索过滤器

### 主要函数

**连接和表管理：**
- **`connect()`**: 创建数据库客户端连接
- **`open_table()`**: 打开现有表
- **`check_table_exist()`**: 检查表是否存在
- **`drop_table()`**: 删除表

**数据操作：**
- **`insert_one()`**: 插入单条记录
- **`insert_multi()`**: 批量插入记录
- **`upsert_one()`**: 插入或更新单条记录（ON CONFLICT）
- **`upsert_multi()`**: 批量插入或更新记录
- **`update()`**: 更新指定条件的记录
- **`delete()`**: 删除满足条件的记录
- **`truncate()`**: 清空表中所有数据
- **`overwrite()`**: 覆盖表中所有数据
- **`drop()`**: 删除表
- **`get_by_key()`**: 根据主键查询单条记录
- **`get_multi_by_keys()`**: 根据主键列表批量查询

**向量检索：**
- **`set_vector_index()`**: 设置单个向量索引
- **`set_vector_indexes()`**: 设置多个向量索引
- **`delete_vector_indexes()`**: 删除所有向量索引
- **`get_vector_index_info()`**: 获取向量索引信息
- **`get_all_vector_column_dimensions()`**: 获取所有向量列及其维度
- **`get_vector_column_dimension()`**: 获取特定向量列的维度
- **`search_vector()`**: 执行向量检索

**全文检索：**
- **`create_text_index()`**: 创建全文索引
- **`set_text_index()`**: 修改全文索引
- **`drop_text_index()`**: 删除全文索引
- **`get_index_properties()`**: 获取索引属性
- **`search_text()`**: 执行全文检索

**查询构建：**
- **`select()`**: 选择返回的列
- **`where()`**: 添加过滤条件
- **`and_where()`**: 添加 AND 过滤条件
- **`or_where()`**: 添加 OR 过滤条件
- **`order_by()`**: 排序
- **`group_by()`**: 分组
- **`limit()`**: 限制结果数量
- **`offset()`**: 跳过指定数量的结果
- **`join()`**: 表连接
- **`inner_join()`**: 内连接
- **`left_join()`**: 左连接
- **`right_join()`**: 右连接
- **`select_tokenize()`**: 显示分词效果
- **`select_text_search()`**: 在 SELECT 中进行全文检索
- **`where_text_search()`**: 在 WHERE 中进行全文检索过滤

### 异常类

- **`HoloSearchError`**: 基础异常类
- **`ConnectionError`**: 连接相关错误
- **`QueryError`**: 查询执行错误
- **`SqlError`**: SQL 生成错误
- **`TableError`**: 表操作错误

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

**Holo Search SDK** - 让Hologres向量和全文检索变得简单高效 🚀
