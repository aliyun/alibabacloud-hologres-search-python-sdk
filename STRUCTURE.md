# Holo Search SDK - 目录结构说明

本项目是一个用于数据库检索的Python SDK，支持向量检索、全文检索和混合检索功能。

## 项目结构

```
holo-search-sdk/
├── README.md                          # 项目说明文档
├── pyproject.toml                     # 项目配置和依赖管理
├── Makefile                           # 构建和开发工具命令
├── .gitignore                         # Git忽略文件配置
├── STRUCTURE.md                       # 目录结构说明（本文件）
├── LICENSE.txt                        # 项目许可证文件
│
├── holo_search_sdk/                   # 主要SDK代码包
│   ├── __init__.py                    # 包初始化，导出主要API
│   ├── client.py                      # 客户端类，管理数据库连接
│   ├── types.py                       # 类型定义（ConnectionConfig等）
│   ├── exceptions.py                  # 自定义异常类
│   │
│   └── backend/                       # 数据库后端实现
│       ├── __init__.py                # 后端模块导出
│       ├── database.py                # HoloDB 数据库连接管理
│       ├── table.py                   # HoloTable 表操作实现
│       ├── connection.py              # HoloConnect 底层连接实现
│       ├── query.py                   # QueryBuilder 查询构建器
│       ├── filter.py                  # 过滤器表达式类
│       │
│       └── utils/                     # 工具函数模块
│           ├── __init__.py            # 工具模块导出
│           └── sql_utils.py           # SQL构建工具函数
│
├── tests/                             # 测试代码
│   ├── __init__.py                    # 测试包初始化
│   ├── conftest.py                    # pytest配置和fixtures
│   ├── test_client.py                 # 客户端测试
│   ├── test_types.py                  # 类型定义测试
│   ├── test_exceptions.py             # 异常类测试
│   ├── test_backend.py                # 后端模块测试
│   └── test_query.py                  # 查询构建器测试
│
└── examples/                          # 使用示例
    ├── basic_vector_search.py         # 向量检索示例
    ├── basic_text_search.py           # 全文检索示例
    └── basic_crud_usage.py            # CRUD 操作示例
```

## 核心组件说明

### 1. 客户端层 (Client)
- **client.py**: 主要的客户端接口，负责连接管理和表操作
- 支持连接池管理和上下文管理器
- 提供统一的数据库连接抽象
- 支持表的创建、打开、删除等操作

**主要功能：**
```python
# 连接管理
client = holo.connect(host, port, database, access_key_id, access_key_secret)
client.connect()
client.disconnect()

# 表操作
table = client.open_table("documents")
client.drop_table("documents")
exists = client.check_table_exist("documents")

# 数据操作
client.insert_one("documents", {"id": "1", "content": "Hello world", "vector": [0.1, 0.2, 0.3]})
client.insert_multi("documents", [
    {"id": "2", "content": "Hello Python", "vector": [0.4, 0.5, 0.6]},
    {"id": "3", "content": "Hello World", "vector": [0.7, 0.8, 0.9]}
])

# CRUD 操作
table = client.open_table("documents")
table.upsert_one("id", [1, "Updated content", [0.1, 0.2, 0.3]], update=True)  # 插入或更新
table.update(["content"], ["New content"], condition="id = 1")  # 更新
table.delete("id > 100")  # 删除
table.truncate()  # 清空
table.overwrite(values=[[1, "New", [0.1, 0.2, 0.3]]])  # 覆盖全表

# 向量索引管理
client.set_vector_index("documents", "vector", "Euclidean")
client.set_vector_indexes("documents", {
    "vector": {"distance_method": "Cosine"},
    "text": {"distance_method": "InnerProduct"}
})
client.delete_vector_indexes("documents")
```

### 2. 后端层 (Backend)

#### 2.1 数据库管理 (database.py)
- **HoloDB**: 数据库连接和管理类
- 负责建立和维护数据库连接
- 提供 SQL 执行接口
- 管理表的生命周期

**核心方法：**
```python
# 连接管理
db.connect()
db.disconnect()
db.execute(sql, fetch_result=False)

# 表管理
db.open_table(table_name)
db.drop_table(table_name)
db.check_table_exist(table_name)
```

#### 2.2 表操作 (table.py)
- **HoloTable**: 表操作的核心实现
- 支持数据插入、向量检索和全文检索
- 管理向量索引配置
- 提供查询构建接口
- 支持基于主键的精确查询

**核心方法：**
```python
# 数据插入操作
table.insert_one(values, column_names)
table.insert_multi(values, column_names)
table.upsert_one(index_column, values, column_names, update, ...)  # 插入或更新（ON CONFLICT）
table.upsert_multi(index_column, values, column_names, update, ...)  # 批量插入或更新
table.overwrite(values=..., values_expression=...)  # 覆盖表中所有数据

# 数据更新操作
table.update(columns, values, condition, ...)  # 更新指定条件的记录

# 数据删除操作
table.delete(condition)  # 删除满足条件的记录
table.truncate()  # 清空表中所有数据（保留表结构）
table.drop()  # 删除表

# 向量索引管理
table.set_vector_index(column, distance_method, ...)
table.set_vector_indexes(column_configs)
table.delete_vector_indexes()
table.get_vector_index_info()  # 获取当前向量索引配置信息

# 向量检索
table.search_vector(vector, column, output_name, distance_method)

# 数据查询
table.get_by_key(key_column, key_value, return_columns)        # 根据主键查询单条记录
table.get_multi_by_keys(key_column, key_values, return_columns) # 根据主键列表批量查询
```

#### 2.3 连接层 (connection.py)
- **HoloConnect**: 底层数据库连接实现
- 封装 psycopg 连接
- 提供 SQL 执行和结果获取

#### 2.4 查询构建 (query.py)
- **QueryBuilder**: 查询构建器
- 支持链式调用
- 提供灵活的查询接口
- 支持距离过滤功能
- 支持全文检索和分词
- 支持表连接查询

**核心方法：**
```python
# 基本查询构建
query_builder.select(["id", "name"]).where("status = 'active'").limit(10)

# 距离过滤
query_builder.min_distance(0.5)  # 设置最小距离阈值
query_builder.max_distance(0.8)  # 设置最大距离阈值

# 全文检索
query_builder.select_text_search(column="content", expression="关键词", output_name="score")
query_builder.where_text_search(column="content", expression="关键词", min_threshold=0.5)

# 分词
query_builder.select_tokenize(column="content", tokenizer="jieba", output_name="tokens")

# 表连接
query_builder.inner_join(table2, "table1.id = table2.foreign_id")
query_builder.left_join(table2, "table1.id = table2.foreign_id")
```

#### 2.5 过滤器表达式 (filter.py)
- **FilterExpression**: 过滤器表达式基类
- **Filter**: 基础过滤器
- **AndFilter**: AND 逻辑过滤器
- **OrFilter**: OR 逻辑过滤器
- **NotFilter**: NOT 逻辑过滤器
- **TextSearchFilter**: 全文检索过滤器
- 支持逻辑运算符重载（&, |, ~）

**核心功能：**
```python
# 使用逻辑运算符
filter1 = Filter("age > 18")
filter2 = Filter("status = 'active'")
combined = filter1 & filter2  # AND
combined = filter1 | filter2  # OR
negated = ~filter1  # NOT

# 使用便捷类
AndFilter("age > 18", "status = 'active'")
OrFilter("premium = true", "vip = true")
NotFilter("deleted = true")

# 全文检索过滤器
TextSearchFilter(
    column="content",
    expression="关键词",
    min_threshold=0.5,
    tokenizer="jieba"
)
```

#### 2.6 SQL 工具函数 (utils/sql_utils.py)
- **build_text_search_sql**: 构建全文检索 SQL
- **build_tokenize_sql**: 构建分词 SQL
- **build_analyzer_params_sql**: 构建分析器参数 SQL
- 提供统一的 SQL 构建接口
- 处理复杂的参数组合

**核心功能：**
```python
# 构建全文检索 SQL
build_text_search_sql(
    column="content",
    expression="检索词",
    mode="match",
    operator="AND",
    tokenizer="jieba",
    filter_params={"lowercase": True, "stop": ["的", "了"]}
)

# 构建分词 SQL
build_tokenize_sql(
    column="content",
    tokenizer="jieba",
    tokenizer_params={"mode": "search", "hmm": True},
    filter_params={"removepunct": True, "lowercase": True, "stop": ["_english_"], "stemmer": "english"}
)
```

### 3. 类型系统 (Types)

#### 3.1 核心类型 (types.py)
- **ConnectionConfig**: 连接配置数据类
- **DistanceType**: 距离计算方法类型
- **BaseQuantizationType**: 基础量化类型
- **PreciseQuantizationType**: 精确量化类型
- **PreciseIOType**: 精确IO类型
- **VectorSearchFunction**: 向量检索函数映射
- **TokenizerType**: 分词器类型
- **TextFilterType**: 分词过滤器类型
- **TextSearchModeType**: 全文检索模式类型
- **TextSearchOperatorType**: 全文检索操作符类型

**类型定义：**
```python
@dataclass
class ConnectionConfig:
    host: str
    port: int
    database: str
    access_key_id: str
    access_key_secret: str
    schema: str = "public"
    autocommit: bool = False

# 向量检索类型别名
DistanceType = Literal["Euclidean", "InnerProduct", "Cosine"]
BaseQuantizationType = Literal["sq8", "sq8_uniform", "fp16", "fp32", "rabitq"]

# 全文检索类型别名
TokenizerType = Literal["jieba", "ik", "icu", "whitespace", "standard", "keyword", "simple", "ngram", "pinyin"]
TextFilterType = Literal["lowercase", "stop", "stemmer", "length", "removepunct", "pinyin"]
TextSearchModeType = Literal["match", "phrase", "natural_language", "term"]
TextSearchOperatorType = Literal["AND", "OR"]
```

### 4. 异常处理 (Exceptions)

#### 4.1 异常层次结构 (exceptions.py)
```
HoloSearchError (基础异常)
├── ConnectionError (连接错误)
├── QueryError (查询错误)
├── SqlError (SQL错误)
└── TableError (表操作错误)
```

**异常特性：**
- 统一的错误代码系统
- 详细的错误信息和上下文
- 支持错误链和异常传播
- 类型安全的异常处理

### 5. 测试系统 (Tests)

#### 5.1 测试结构
- **conftest.py**: pytest 配置和通用 fixtures
- **test_client.py**: 客户端功能测试
- **test_types.py**: 类型定义和验证测试
- **test_exceptions.py**: 异常处理测试
- **test_backend.py**: 后端模块测试

#### 5.2 测试覆盖
- **单元测试**: 每个模块的独立功能测试
- **集成测试**: 模块间交互测试
- **Mock测试**: 使用 Mock 对象隔离外部依赖
- **异常测试**: 错误情况和边界条件测试

#### 5.3 测试工具和配置
```python
# pytest 配置
pytest.ini_options = {
    "testpaths": ["tests"],
    "python_files": ["test_*.py"],
    "addopts": "-v --cov=holo_search_sdk --cov-report=term-missing",
    "asyncio_mode": "auto"
}

# 主要 fixtures
- sample_connection_config: 测试连接配置
- mock_holo_db: 模拟数据库对象
- mock_holo_table: 模拟表对象
- client_with_mock_backend: 带模拟后端的客户端
- sample_table_columns: 示例表结构
- sample_vector_data: 示例向量数据
```

## 设计特点

### 1. 模块化设计
- **清晰的分层架构**: 客户端 → 后端 → 连接层
- **职责分离**: 每个模块有明确的职责边界
- **可扩展性**: 易于添加新的后端实现
- **可测试性**: 模块间松耦合，便于单元测试

### 2. 类型安全
- **静态类型检查**: 使用 mypy 进行类型验证
- **运行时验证**: 使用 dataclass 进行数据验证
- **类型提示**: 完整的类型注解覆盖
- **类型别名**: 清晰的类型定义和约束

### 3. 错误处理
- **分层异常**: 不同层次的专门异常类型
- **错误上下文**: 详细的错误信息和调试信息
- **异常链**: 保留原始异常信息
- **错误代码**: 统一的错误分类系统

### 4. 向量检索优化
- **多种距离算法**: 支持欧几里得、内积、余弦距离
- **索引配置**: 灵活的向量索引参数配置
- **量化支持**: 多种量化类型优化存储和性能
- **高精度索引**: HGraph 高精度索引支持

### 5. 全文检索功能
- **多种分词器**: 支持 jieba、ik、icu、whitespace、standard 等分词器
- **检索模式**: 关键词检索、短语检索、自然语言检索、术语检索
- **分词过滤器**: 支持小写转换、停用词过滤、词干提取、长度过滤、标点移除、拼音分词
- **灵活配置**: 可自定义分词参数和过滤器顺序
- **分词展示**: 支持查看全文的分词效果

### 6. 过滤器表达式系统
- **逻辑运算**: 支持 AND、OR、NOT 逻辑运算
- **运算符重载**: 使用 &、|、~ 进行直观的逻辑组合
- **类型安全**: 完整的类型提示和验证
- **SQL 生成**: 自动生成优化的 SQL 查询

### 7. 查询构建器增强
- **表连接**: 支持 INNER、LEFT、RIGHT、FULL、CROSS JOIN
- **全文检索集成**: 在 SELECT 和 WHERE 中使用全文检索
- **分词集成**: 在查询中展示分词效果
- **复杂查询**: 支持分组、排序、限制、偏移等操作

### 8. 开发体验
- **链式API**: 直观的方法链调用
- **上下文管理**: 自动资源管理
- **详细文档**: 完整的代码文档和使用示例
- **开发工具**: 完整的开发工具链支持

## 使用模式

### 1. 基本使用模式
```python
# 1. 建立连接
client = holo.connect(host, port, database, key_id, key_secret)
client.connect()

# 2. 打开表
table = client.open_table("docs")

# 3. 插入数据
table.insert_multi(data, column_names)

# 4. 设置索引
table.set_vector_index("vector", "Cosine")

# 5. 执行检索
results = table.search_vector(query_vector, "vector").fetchall()

# 6. 关闭连接
client.disconnect()
```

### 2. 上下文管理器模式
```python
with holo.connect(...) as client:
    client.connect()
    table = client.open_table("docs")
    results = table.search_vector(query_vector, "vector").fetchall()
    # 自动关闭连接
```

### 3. 批量操作模式
```python
# 批量数据插入
table.insert_multi(large_dataset, column_names)

# 批量索引设置
table.set_vector_indexes({
    "content_vector": {"distance_method": "Cosine"},
    "title_vector": {"distance_method": "Euclidean"}
})
```