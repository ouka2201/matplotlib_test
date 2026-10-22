import traceback
from contextlib import contextmanager
from typing import Any, Generator

from sqlalchemy import Engine, inspect
from sqlalchemy.orm import scoped_session
from sqlalchemy.sql import text

from cndx_corp_back import db


def get_db_engine() -> Engine:
    """
    データベースエンジンを取得します。

    Returns:
        Engine: SQLAlchemyのデータベースエンジン
    """
    return db.engine


@contextmanager
def get_scoped_session(logger=None) -> Generator[scoped_session, None, None]:
    """
    データベースセッションのスコープを管理するコンテキストマネージャ。

    Args:
        logger (optional): ロガーインスタンス

    Yields:
        scoped_session: SQLAlchemyのセッション
    """
    try:
        session: scoped_session = db.session
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        if logger:
            # logger.error(f"データベース接続エラー：{e}", exc_info=True)
            logger.error(f"データベース接続エラー：{e}\n{traceback.format_exc()}")
        raise e
    finally:
        session.remove()


def build_sql(
    table: str,
    columns: list[str] = None,
    where: str | dict = None,
    order_by: str = None,
) -> str:
    """
    照会用のSQL文を組み立てます。

    廃置する予定。

    Args:
        table (str): テーブル名
        columns (list[str], optional): 取得するカラムのリスト
        where (str | dict, optional): WHERE句の条件
        order_by (str, optional): ORDER BY句の条件

    Returns:
        str: 組み立てられたSQL文
    """
    if columns:
        columns_str = ", ".join(columns)
    else:
        columns_str = "*"

    if isinstance(where, dict):
        where = build_where_state(**where)

    if where:
        where_clause = " WHERE " + where
    else:
        where_clause = ""

    if order_by:
        order_by_clause = " ORDER BY " + order_by
    else:
        order_by_clause = ""

    return f"SELECT {columns_str} FROM {table}{where_clause}{order_by_clause}"


def build_where_pairs(column: str, op_str: str, value: str) -> str:
    """
    WHERE句の条件ペアを組み立てます。

    Args:
        column (str): カラム名
        op_str (str): 演算子（例: '=', '>', '>=', '<'）
        value (str): 値

    Returns:
        str: 組み立てられた条件ペア
    """
    if isinstance(value, str):
        return f"{column} {op_str} '{value}'"
    else:
        return f"{column} {op_str} {value}"


def build_where_state(filters: list = None, op_str: str = None, **kwargs) -> str:
    """
    WHERE句の条件を組み立てます。

    Args:
        filters (list, optional): カラム、演算子、値のタプルのリスト
        op_str (str, optional): デフォルトの演算子
        **kwargs: カラムと値のペア

    Returns:
        str: 組み立てられたWHERE句
    """
    where_pairs = []
    if filters:
        for column, op, value in filters:
            where_pairs.append(build_where_pairs(column, op, value))
    else:
        op_dict = "=" if op_str is None else op_str
        for column, value in kwargs.items():
            where_pairs.append(build_where_pairs(column, op_dict, value))
    return " and ".join(where_pairs)


class DatabaseManager:
    def __init__(self, logger=None):
        self.logger = logger

    def get_engine(self) -> Engine:
        return get_db_engine()

    @contextmanager
    def begin(self):
        connection = self.get_engine().connect()
        transaction = connection.begin()
        try:
            yield connection
            transaction.commit()
        except Exception as e:
            transaction.rollback()
            if self.logger:
                # self.logger.error(f"トランザクションエラー：{e}", exc_info=True)
                self.logger.error(
                    f"トランザクションエラー：{e}\n{traceback.format_exc()}"
                )
            raise
        finally:
            connection.close()

    def get_scoped_session(self):
        return get_scoped_session(self.logger)


def build_select_clause(config: dict):
    columns = config.get("select", ["*"])
    return f"SELECT {', '.join(columns)}"


def build_from_clause(config: dict):
    return f"FROM {config['from']}"


def build_where_clause(config: dict[str, list[dict]], request: dict):
    """
    in の場合は必ず value の型を list にすること
    value が null の場合は 'null'
    """
    conditions = []
    for cond in config.get("where", []):

        field = cond["field"]
        op = cond["op"]

        val = request.get(field, None)
        if val is None:
            val = cond.get("value", None)
        if val is None:
            continue

        if op == "in":
            conditions.append(f"{field} IN ({', '.join(get_val(v) for v in val)})")
        elif op == "like":
            conditions.append(f"{field} LIKE '%{val}%'")
        else:
            conditions.append(f"{field} {op} {get_val(val)}")
    if conditions:
        return "WHERE " + " AND ".join(conditions)
    return ""


def get_val(input):
    """
    Convert a value to its SQL-safe string representation.
    Strings are escaped and wrapped in single quotes.
    Booleans become 1 or 0, None becomes NULL.
    """
    if input is None:
        return "NULL"
    if isinstance(input, str):
        return f"""'{input.replace("'", "''")}'"""
    return str(input)


def build_order_by_clause(config: dict):
    orders = config.get("order_by", [])
    if not orders:
        return ""
    order_exprs = [f"{o['field']} {o.get('direction', 'asc').upper()}" for o in orders]
    return f"ORDER BY {', '.join(order_exprs)}"


def build_limit_offset_clause(config: dict):
    pagination = config.get("pagination", {})
    clauses = []
    if "limit" in pagination:
        clauses.append(f"LIMIT {pagination['limit']}")
    if "offset" in pagination:
        clauses.append(f"OFFSET {pagination['offset']}")
    return " ".join(clauses)


def build_query(config: dict, request) -> str:
    return " ".join(
        filter(
            None,
            [
                build_select_clause(config),
                build_from_clause(config),
                build_where_clause(config, request),
                build_order_by_clause(config),
                build_limit_offset_clause(config),
            ],
        )
    )


def update_entity_fields(entity, update_data: dict):
    # エンティティからカラム名を取得
    model_columns = set(c.key for c in inspect(entity).mapper.column_attrs)

    # update_data に存在するカラムをすべて更新
    for key, value in update_data.items():
        if key in model_columns:
            setattr(entity, key, value)
