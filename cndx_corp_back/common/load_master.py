import datetime

import pandas as pd
from flask import current_app
from sqlalchemy import Engine

from cndx_corp_back.common.database_manager import build_sql, build_where_state
from cndx_corp_back.constant.constants import MST_LIST, MstTable

# マスタデータを格納
mst_data: dict = {}


def load_mst_data(engine: Engine, logger=None) -> None:
    """マスタデータ読込"""

    global mst_data
    # if env == None:
    #     env = "development"  # デフォルト環境
    today = datetime.date.today().strftime("%Y%m%d")

    with engine.begin() as conn:
        for tbl, clm in MST_LIST.items():
            where = ""
            # if "DB_COMMON.ACTIVITY_MINOR_CATEGORY_MST" != tbl:
            #     where = f"start_date <= '{today}' AND ( end_date >= '{today}' OR end_date IS NULL ) "  # AND delete_flg IS NOT TRUE"

            if tbl in ("DB_CORP.M_USER"):
                if where:
                    where += " AND"
                where += " delete_flg IS NOT TRUE"

            sql = build_sql(table=tbl, columns=clm, where=where)

            # 有効なデータを抽出
            res_df = pd.read_sql(sql, conn)
            if res_df.empty:

                if logger:
                    logger.error(
                        f"テーブル {tbl} からマスタデータを1件も取得できませんでした。"
                    )
                raise Exception(
                    f"テーブル {tbl} からマスタデータを1件も取得できませんでした。"
                )

            mst_data[tbl.split(".")[1]] = res_df.to_dict(orient="records")

    if logger:
        logger.info("マスタデータの読込が完了しました。")


def get_mst_data(table: MstTable | str, column: str = None, **kwargs):
    """
    マスタデータ取得

    Args:
        table (MstTable): 取得するデータ所在のテーブル名かそれを表す Enum 項目
        column (str): 目標カラム名。None の場合は dict で全カラムを返す
        kwargs: クエリ条件

    Returns:
        Result: Any | dict | None:
        目標カラムの value or dict 型で一件目のレコード
        カラム存在しない又は絞った結果がない場合は None
    """
    tbl_nm = table if isinstance(table, str) else table.value
    records = mst_data[tbl_nm].query(build_where_state(op_str="==", **kwargs))
    if records.empty:
        return None
    if column is None:
        return records.iloc[0].to_dict()
    else:
        return records[column].values[0]
