import pandas as pd
from flask import current_app
from sqlalchemy import Engine
from tableauhyperapi import (
    Connection,
    CreateMode,
    HyperProcess,
    Inserter,
    SqlType,
    TableDefinition,
    TableName,
    Telemetry,
)

from cndx_corp_back.common.database_manager import build_sql, build_where_state


class HyperManager:

    # TODO 毎回hyperを生成するのを省くように、テンプレート化

    # TODO インスタント化する際にパラメータからもらって初期化
    # 定数 DB関連情報
    # 定数 Datasource名

    def __init__(self):
        # データベーススキーマとテーブル名
        self.schema = "db_corp"

    def get_query(self, schema=None, table=None, **kwargs):
        """クエリ用 SQL を取得"""
        if schema is None:
            schema = self.schema
        if table is None:
            table = self.table_name

        return build_sql(f"{schema}.{table}", where=build_where_state(**kwargs))

    def map_pandas_dtype_to_hyper_type(self, dtype):
        """Pandas から Hyper へ 型のマッピング"""
        if pd.api.types.is_integer_dtype(dtype):
            return SqlType.big_int()
        elif pd.api.types.is_float_dtype(dtype):
            return SqlType.double()
        elif pd.api.types.is_string_dtype(dtype):
            return SqlType.text()
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            return SqlType.timestamp()
        elif pd.api.types.is_bool_dtype(dtype):
            return SqlType.bool()
        else:
            raise ValueError(f"Unsupported data type: {dtype}")

    def fetch_table_data(self, query, engine: Engine) -> pd.DataFrame:
        """Pandas 経由でテーブルからデータを取得"""

        with engine.connect() as conn:

            df = pd.read_sql(query, conn)

        return df

    def fetch_table_def(self, dataframe: pd.DataFrame, table_name) -> TableDefinition:
        """DataFrame からテーブル構造を取得"""

        return TableDefinition(
            table_name=TableName(table_name),
            columns=[
                TableDefinition.Column(
                    col,
                    self.map_pandas_dtype_to_hyper_type(dataframe[col].dtype),
                )
                for col in dataframe.columns
            ],
        )

    def create_hyper_file(
        self,
        dataframe: pd.DataFrame,
        table_def: TableDefinition,
        hyper_file_loc,
        schema="Extract",
        method=1,
    ):
        """DataFrame to Hyper"""

        if method == 1:
            try:
                with HyperProcess(
                    telemetry=Telemetry.SEND_USAGE_DATA_TO_TABLEAU
                ) as hyper:
                    with Connection(
                        endpoint=hyper.endpoint,
                        database=hyper_file_loc,
                        create_mode=CreateMode.CREATE_AND_REPLACE,
                    ) as connection:
                        connection.catalog.create_schema(schema)

                        connection.catalog.create_table(table_def)

                        if not dataframe.empty:
                            with Inserter(connection, table_def) as inserter:
                                inserter.add_rows(
                                    dataframe.itertuples(index=False, name=None)
                                )
                                inserter.execute()
            except Exception as e:
                current_app.logger.error(f"Hyper file creation failed: {str(e)}")
                raise e
        else:
            # pantab を使用して Hyper ファイルを作成 TODO: pantab の使用を検討
            from pantab import frame_to_hyper

            dataframe = dataframe.fillna("")
            frame_to_hyper(dataframe, hyper_file_loc, table=table_def.table_name)

        return hyper_file_loc
