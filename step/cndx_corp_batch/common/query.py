from pathlib import Path

QUERY_PATH = Path(__file__).parent.parent / "query"


def load_sql_file(file_name: str):
    """SQLファイルを読み込む。

    Args:
        file_name (str): ファイル名

    Returns:
        str: SQL
    """
    sql_file_path = QUERY_PATH / file_name
    with open(sql_file_path, "r", encoding="utf-8") as f:
        sql_query = f.read()
    return sql_query
