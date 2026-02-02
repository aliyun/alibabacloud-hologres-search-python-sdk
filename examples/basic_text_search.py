"""
Basic text search example for Holo Search SDK.
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
        CREATE TABLE IF NOT EXISTS wiki_articles (id int primary key, content text);
    """
    _ = client.execute(create_table_sql, fetch_result=False)
    wiki_table = client.open_table("wiki_articles")
    print(f"Table '{wiki_table.get_name()}' created successfully.")

    # Set vector index
    wiki_table.create_text_index(
        index_name="ft_idx_1", column="content", tokenizer="jieba"
    )
    print("Vector index set successfully for column 'content'.")

    # insert data
    wiki_table.insert_multi(
        [
            [1, "长江是中国第一大河，世界第三长河，全长约6,300公里。"],
            [2, "Li was born in 1962 in Wendeng County, Shandong."],
            [3, "He graduated from the department of physics at Shandong University."],
            [4, "春节，即农历新年，是中国最重要的传统节日。"],
            [
                5,
                "春节通常在公历1月下旬至2月中旬之间。春节期间的主要习俗包括贴春联、放鞭炮、吃年夜饭、拜年等。",
            ],
            [6, "2006年，春节被国务院批准为第一批国家级非物质文化遗产。"],
            [7, "Shandong has dozens of universities."],
            [8, "ShanDa is a famous university of Shandong."],
            [9, ""],
            [10, None],
            [
                11,
                '211.11.9.0 - - [1998-06-21T15:00:01-05:00] "GET /english/index.html HTTP/1.0" 304 0',
            ],
        ]
    )
    print("Data inserted successfully.")

    res = wiki_table.select("*").limit(1).fetchone()
    print(f"Data fetched successfully: {res}")

    # Vacuum
    wiki_table.vacuum()
    print("Vacuum completed.")

    # Search text
    query_result = wiki_table.search_text(
        column="content", expression="长江", return_all_columns=True
    ).fetchall()
    print(f"Query result1: {query_result}")
    query_result = wiki_table.search_text(
        column="content", expression="春节1962", return_all_columns=True
    ).fetchall()
    print(f"Query result2: {query_result}")

    # Get index properties
    index_properties = wiki_table.get_index_properties()
    print(f"Index properties: {index_properties}")

    # Effect of different search modes
    # (K1) 关键词检索（默认operator=OR），包含'shandong'或'university'的文档均能匹配
    query_result = wiki_table.search_text(
        column="content", expression="shandong university", return_all_columns=True
    ).fetchall()
    print(f"Query result(K1): {query_result}")
    # (K2) 关键词检索（operator=AND），必须同时包含'machine'和'learning'才能匹配
    query_result = wiki_table.search_text(
        column="content",
        expression="shandong university",
        return_all_columns=True,
        operator="AND",
    ).fetchall()
    print(f"Query result(K2): {query_result}")

    # (P1) 短语检索（默认slop = 0），即必须 shandong 后紧接 university 后才匹配
    query_result = wiki_table.search_text(
        column="content",
        expression="shandong university",
        return_all_columns=True,
        mode="phrase",
    ).fetchall()
    print(f"Query result(P1): {query_result}")
    # (P2) 短语检索指定slop = 14，即 shandong 与 university 之间的距离不超过14个字符，那么可以匹配“Shandong has dozens of universities.”
    query_result = wiki_table.search_text(
        column="content",
        expression="shandong university",
        return_all_columns=True,
        mode="phrase",
        slop="14",
    ).fetchall()
    print(f"Query result(P2): {query_result}")
    # (P3) 短语检索支持检索不保序的短语，但slop计算方式不一样，要比保序的slop要大。因此'university of Shandong'也能匹配以下查询，但slop=22时不会匹配到
    query_result = wiki_table.search_text(
        column="content",
        expression="shandong university",
        return_all_columns=True,
        mode="phrase",
        slop="23",
    ).fetchall()
    print(f"Query result(P3): {query_result}")
    # (P4) standard分词索引下的表现。（ALTER INDEX ft_idx_1 SET (tokenizer = 'standard');）对于standard分词来说，slop则是以tokens为计算单位。只要中间间隔0个tokens，不管有多少空格，都算作短语匹配。
    wiki_table.set_text_index(index_name="ft_idx_1", tokenizer="standard").vacuum()
    query_result = wiki_table.search_text(
        column="content",
        expression="shandong university",
        return_all_columns=True,
        mode="phrase",
    ).fetchall()
    print(f"Query result(P4): {query_result}")
    # (P5) 标点将被忽略。（IK分词器为例）即使文本中，长河和全长之间是逗号，而查询串是句号。
    wiki_table.set_text_index(index_name="ft_idx_1", tokenizer="ik").vacuum()
    query_result = wiki_table.search_text(
        column="content",
        expression="长河。全长",
        return_all_columns=True,
        mode="phrase",
    ).fetchall()
    print(f"Query result(P5): {query_result}")

    # (N1) 自然语言查询：关键词检索，与(K1)等价
    wiki_table.set_text_index(index_name="ft_idx_1", tokenizer="jieba").vacuum()
    query_result = wiki_table.search_text(
        column="content",
        expression="shandong university",
        return_all_columns=True,
        mode="natural_language",
    ).fetchall()
    print(f"Query result(N1): {query_result}")
    # (N2) 自然语言查询：关键词检索，必须(同时包含'shandong'和'university')或者包含'文化'才匹配。AND运算符优先级大于OR。
    query_result = wiki_table.search_text(
        column="content",
        expression="(shandong AND university) OR 文化",
        return_all_columns=True,
        mode="natural_language",
    ).fetchall()
    print(f"Query result(N2_1): {query_result}")
    # 等价于
    query_result = wiki_table.search_text(
        column="content",
        expression="shandong AND university OR 文化",
        return_all_columns=True,
        mode="natural_language",
    ).fetchall()
    print(f"Query result(N2_2): {query_result}")
    # 等价于
    query_result = wiki_table.search_text(
        column="content",
        expression="(+shandong +university) 文化",
        return_all_columns=True,
        mode="natural_language",
    ).fetchall()
    print(f"Query result(N2_3): {query_result}")
    # (N3) 自然语言查询：关键词检索，必须包含'shandong'，必须不包含'university'，可以包含'文化'。在这个查询中'文化'关键词前没有+, -符号，不会影响哪些行会匹配上，但会影响匹配分数，带有'文化'的匹配分数更高。
    query_result = wiki_table.search_text(
        column="content",
        expression="+shandong -university 文化",
        return_all_columns=True,
        mode="natural_language",
    ).fetchall()
    print(f"Query result(N3_1): {query_result}")
    # 必须包含'shandong'，必须不包含'physics'，可以包含'famous'。包含famous的相关性分数更高。
    query_result = (
        wiki_table.search_text(
            column="content",
            expression="+shandong -physics famous",
            return_score=True,
            return_score_name="score",
            mode="natural_language",
        )
        .select(["id", "content"])
        .order_by("score", "desc")
        .fetchall()
    )
    print(f"Query result(N3_2): {query_result}")
    # (N4) 自然语言查询：短语检索，与(P1)等价，短语需用双引号""包裹，如果中间有"，则需使用\转义。
    query_result = wiki_table.search_text(
        column="content",
        expression='"shandong university"',
        return_all_columns=True,
        mode="natural_language",
    ).fetchall()
    print(f"Query result(N4): {query_result}")
    # (N5) 自然语言查询：短语检索，与(P2)等价，支持以~语法设置slop
    query_result = wiki_table.search_text(
        column="content",
        expression='"shandong university"~23',
        return_all_columns=True,
        mode="natural_language",
    ).fetchall()
    print(f"Query result(N5): {query_result}")
    # (N6) 自然语言查询：匹配所有文档
    query_result = wiki_table.search_text(
        column="content",
        expression="*",
        return_all_columns=True,
        mode="natural_language",
    ).fetchall()
    print(f"Query result(N6): {query_result}")
    # (T1) 术语检索：没有精确包含'shandong university'词的，大小写也不对
    query_result = wiki_table.search_text(
        column="content",
        expression="shandong university",
        return_all_columns=True,
        mode="term",
    ).fetchall()
    print(f"Query result(T1): {query_result}")
    # (T2) 术语检索：分词后，有'春节'这个精确的术语
    query_result = wiki_table.search_text(
        column="content",
        expression="春节",
        return_all_columns=True,
        mode="term",
    ).fetchall()
    print(f"Query result(T2): {query_result}")
    # (T3) 术语检索：词语都被拆分，查此术语查不到
    query_result = wiki_table.search_text(
        column="content",
        expression="春节，即农历新年，是中国最重要的传统节日。",
        return_all_columns=True,
        mode="term",
    ).fetchall()
    print(f"Query result(T3): {query_result}")
    # keyword分词
    wiki_table.set_text_index(index_name="ft_idx_1", tokenizer="keyword").vacuum()
    # (T4) 术语检索：查不到'春节'这个精确术语，因为索引不分词
    query_result = wiki_table.search_text(
        column="content",
        expression="春节",
        return_all_columns=True,
        mode="term",
    ).fetchall()
    print(f"Query result(T4): {query_result}")
    # (T5) 术语检索：精确匹配
    query_result = wiki_table.search_text(
        column="content",
        expression="春节，即农历新年，是中国最重要的传统节日。",
        return_all_columns=True,
        mode="term",
    ).fetchall()
    print(f"Query result(T5): {query_result}")
    # 恢复分词器
    wiki_table.set_text_index(index_name="ft_idx_1", tokenizer="jieba").vacuum()

    # Different query structures
    # 与pk联合查询
    query_result = (
        wiki_table.search_text(
            column="content", expression="shandong university", return_all_columns=True
        )
        .and_where("id = 3")
        .fetchall()
    )
    print(f"Query result(DQ1): {query_result}")
    query_result = (
        wiki_table.search_text(
            column="content", expression="shandong university", return_all_columns=True
        )
        .or_where("id < 2")
        .fetchall()
    )
    print(f"Query result(DQ2): {query_result}")
    # 查出分数并取TOP几个
    query_result = (
        wiki_table.select(["id", "content"])
        .select_text_search(
            column="content",
            expression="shandong university",
            output_name="score",
        )
        .select_tokenize(column="content", tokenizer="jieba")
        .order_by("score", "desc")
        .limit(3)
        .fetchall()
    )
    print(f"Query result(DQ3): {query_result}")
    # 同时在output和where中
    query_result = (
        wiki_table.select(["id", "content"])
        .select_text_search(
            column="content",
            expression="shandong university",
            output_name="score",
        )
        .select_tokenize(column="content", tokenizer="jieba")
        .where_text_search(
            column="content", expression="shandong university", min_threshold=0
        )
        .order_by("score", "desc")
    ).fetchall()
    print(f"Query result(DQ4): {query_result}")
    # 来源表，用于JOIN
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS article_source (id int primary key, source text);
    """
    _ = client.execute(create_table_sql, fetch_result=False)
    source_table = client.open_table("article_source")
    source_table.insert_multi(
        [
            [1, "baike"],
            [2, "wiki"],
            [3, "wiki"],
            [4, "baike"],
            [5, "baike"],
            [6, "baike"],
            [7, "wiki"],
            [8, "paper"],
            [9, "http_log"],
            [10, "http_log"],
            [11, "http_log"],
        ]
    )
    # 检索wiki来源中，和'shandong university'最相关的文档
    query_sql = (
        wiki_table.set_table_alias("a")
        .select(["a.id", "source", "content"])
        .select_text_search(
            column="content",
            expression="shandong university",
            output_name="score",
        )
        .select_tokenize(column="a.content", tokenizer="jieba")
        .join(source_table, "a.id = b.id", table_alias="b")
        .where_text_search(
            column="a.content", expression="shandong university", min_threshold=0
        )
        .where("b.source = 'wiki'")
        .order_by("score", "desc")
    )
    query_result = query_sql.fetchall()
    print(f"Query result(DQ5): {query_result}")
    query_result = query_sql.explain()
    print(f"Explain result(DQ5): {query_result}")

    # ALTER INDEX
    wiki_table.set_text_index(index_name="ft_idx_1", tokenizer="ik")
    index_properties = wiki_table.get_index_properties()
    print(f"Index properties: {index_properties}")
    # ik分词可以分出一、大、一大
    query_sql = wiki_table.search_text(
        column="content", expression="一大", return_all_columns=True
    )
    query_result = query_sql.fetchall()
    print(f"Query result(DQ6): {query_result}")
    client.set_guc_off("hg_experimental_enable_result_cache")
    query_result = query_sql.explain_analyze()
    print(f"Explain analyze result(DQ6): {query_result}")

    # Tokenize
    # 使用默认jieba分词器，默认为search模式，会多分词型提高检索效果
    query_result = wiki_table.show_tokenize_effect(
        text="他来到北京清华大学", tokenizer="jieba"
    )
    print(f"Query result(TK1): {query_result}")
    # 使用自定义的exact模式的jieba分词器，不会多分出词型
    query_result = wiki_table.show_tokenize_effect(
        text="他来到北京清华大学", tokenizer="jieba", tokenizer_params={"mode": "exact"}
    )
    print(f"Query result(TK2): {query_result}")
    # 分词器对比
    query_result = (
        client.build_query()
        .select_tokenize(
            text="他来到北京清华大学", tokenizer="jieba", output_name="jieba"
        )
        .select_tokenize(
            text="他来到北京清华大学", tokenizer="keyword", output_name="keyword"
        )
        .select_tokenize(
            text="他来到北京清华大学", tokenizer="whitespace", output_name="whitespace"
        )
        .select_tokenize(
            text="他来到北京清华大学", tokenizer="simple", output_name="simple"
        )
        .select_tokenize(
            text="他来到北京清华大学", tokenizer="standard", output_name="standard"
        )
        .select_tokenize(text="他来到北京清华大学", tokenizer="icu", output_name="icu")
        .fetchall()
    )
    print(f"Query result(TK3): {query_result}")
    # 对http_logs的分词效果对比
    query_result = (
        client.build_query()
        .select_tokenize(
            text='211.11.9.0 - - [1998-06-21T15:00:01-05:00] "GET /english/index.html HTTP/1.0" 304 0',
            tokenizer="jieba",
            output_name="jieba",
        )
        .select_tokenize(
            text='211.11.9.0 - - [1998-06-21T15:00:01-05:00] "GET /english/index.html HTTP/1.0" 304 0',
            tokenizer="keyword",
            output_name="keyword",
        )
        .select_tokenize(
            text='211.11.9.0 - - [1998-06-21T15:00:01-05:00] "GET /english/index.html HTTP/1.0" 304 0',
            tokenizer="whitespace",
            output_name="whitespace",
        )
        .select_tokenize(
            text='211.11.9.0 - - [1998-06-21T15:00:01-05:00] "GET /english/index.html HTTP/1.0" 304 0',
            tokenizer="simple",
            output_name="simple",
        )
        .select_tokenize(
            text='211.11.9.0 - - [1998-06-21T15:00:01-05:00] "GET /english/index.html HTTP/1.0" 304 0',
            tokenizer="standard",
            output_name="standard",
        )
        .select_tokenize(
            text='211.11.9.0 - - [1998-06-21T15:00:01-05:00] "GET /english/index.html HTTP/1.0" 304 0',
            tokenizer="icu",
            output_name="icu",
        )
        .fetchall()
    )
    print(f"Query result(TK4): {query_result}")
    # 分词器对比
    query_result = (
        wiki_table.select(["id", "content"])
        .select_tokenize(column="content", tokenizer="jieba", output_name="jieba")
        .select_tokenize(column="content", tokenizer="keyword", output_name="keyword")
        .select_tokenize(
            column="content", tokenizer="whitespace", output_name="whitespace"
        )
        .select_tokenize(column="content", tokenizer="simple", output_name="simple")
        .select_tokenize(column="content", tokenizer="standard", output_name="standard")
        .select_tokenize(column="content", tokenizer="icu", output_name="icu")
        .fetchall()
    )
    print(f"Query result(TK5): {query_result}")


if __name__ == "__main__":
    main()
