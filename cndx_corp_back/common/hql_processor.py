import traceback

import pandas as pd
from sqlalchemy import text

import cndx_corp_back.common.constants_colums as constants
import cndx_corp_back.common.log as log

# import middle.middle_download.errorMsgModule as errorMsgModule
# from pyhive.exc import DatabaseError
import cndx_corp_back.common.utils as utils

# log出力用インスタンス取得
logger = log.CorpLogger()

# ","
COMMA = constants.SpecialChars.COMMA.value
# "?"
hatena = constants.SpecialChars.HATENA.value
# ""
BLANK = constants.SpecialChars.BLANK.value

# json_config = utils.get_json_config()
# schema_middle = json_config["database_posgre"]["schema_middle"]
DOT = constants.SpecialChars.DOT.value


@log.log_writer(logger)
def insert_data(
    conn, insert_data_list, table_columns_list, partition_columns_dic, table_name
):
    """
    Args:
        conn: Hive接続用オブジェクト
        insert_data_list (list/DataFrame): データ。[('John', 30),('Alice', 25)]
        table_columns_list(list): 列名,data_listは"DataFrame" -> None 入力してください。
        partition_columns_dic (dict): 分区 ,分区なし None入力してください。
        table_name (str): テーブル名
    """
    logger.info(f"{table_name}テーブルのinsert用処理開始。")

    # DataFrame判定
    if isinstance(insert_data_list, pd.DataFrame):
        insert_datas_df = insert_data_list[list(table_columns_list)]
    else:
        # df型ではない場合、dfにする
        insert_datas_df = pd.DataFrame(insert_data_list, columns=table_columns_list)
    partition_ret = BLANK
    # 列名称編集
    # column_names = insert_datas_df.columns.tolist()
    # sql_column_names ='('+ ','.join([f"{col}" for col in column_names])+')'
    if partition_columns_dic is not None:
        # リスト内包表記を使って、key=value形式の文字列を生成
        partition_list = [
            f'{k}="{v}"'
            for k, v in zip(
                partition_columns_dic.keys(), partition_columns_dic.values()
            )
        ]
        # 文字列を連結して結果を得る
        partition_str = COMMA.join(partition_list)
        partition_ret = f" PARTITION ({partition_str})"

    # insert文を作成する
    # insert_hql = f"INSERT INTO TABLE {table_name} {partition_ret} VALUES "
    # TODO postgre TABLEなし
    insert_hql = f"INSERT INTO {table_name} {partition_ret} VALUES "

    # レコードデータ格納用配列
    recordList = []
    # 登録するデータのレコード数分をループする
    insert_datas_df.fillna(BLANK, inplace=True)
    # ''をNULLに変換
    insert_datas_df.replace(BLANK, "NULL", inplace=True)
    for index, (i, row) in enumerate(insert_datas_df.iterrows()):
        row_values = []
        # レコード毎のカラム数分をループする
        for column_value in row:
            if isinstance(column_value, (int, float)):
                row_values.append(str(column_value))
            # elif utils.is_empty(column_value):
            # elif pd.isnull(column_value) or (isinstance(column_value, str) and column_value == "") or column_value =="nan":
            #     #Excel空欄項目(nan)を処理するため
            #     row_values.append('NULL')
            elif column_value == "NULL":
                row_values.append(f"{column_value}")
            else:
                row_values.append(f"'{column_value}'")

        # カラム毎にカンマで分割する
        row_values_str = COMMA.join(row_values)

        if index != len(insert_datas_df) - 1:
            # レコード毎にカンマで分割する
            row_values_str = f"({row_values_str}),"
        else:
            row_values_str = f"({row_values_str})"

        # レコード文字列を配列に格納する
        recordList.append(row_values_str)

    insert_hql += BLANK.join(recordList)

    logger.debug(f"hql確認★: {insert_hql}")
    # insert用hqlを実行する
    conn.execute(text(insert_hql))
    # with conn.cursor() as cursor:
    #     cursor.execute(insert_hql)

    logger.info(f"{table_name}テーブルのinsert用処理完了。")


@log.log_writer(logger)
def execute_insert(conn, insert_data_list, table_columns_list, table_name):
    """
    Args:
        conn: 接続用オブジェクト
        insert_data_list (list/DataFrame): データ。[('John', 30),('Alice', 25)]
        table_columns_list(list): 列名,data_listは"DataFrame" -> None 入力してください。
        table_name (str): 表。
    """
    logger.info(f"{table_name}テーブルのinsert用処理開始。")

    # DataFrame判定
    if isinstance(insert_data_list, pd.DataFrame):
        insert_datas_df = insert_data_list[list(table_columns_list)]
    else:
        # df型ではない場合、dfにする
        insert_datas_df = pd.DataFrame(insert_data_list, columns=table_columns_list)

    # 列名称編集
    column_names = insert_datas_df.columns.tolist()
    sql_column_names = "(" + ",".join([f"{col}" for col in column_names]) + ")"

    insert_hql = f"INSERT INTO {table_name} {sql_column_names} VALUES "

    # レコードデータ格納用配列
    recordList = []
    # 登録するデータのレコード数分をループする
    insert_datas_df.fillna(BLANK, inplace=True)
    # ''をNULLに変換
    insert_datas_df.replace(BLANK, "NULL", inplace=True)
    for index, (i, row) in enumerate(insert_datas_df.iterrows()):
        row_values = []
        # レコード毎のカラム数分をループする
        for column_value in row:
            if isinstance(column_value, (int, float)):
                row_values.append(str(column_value))
            elif column_value == "NULL":
                row_values.append(f"{column_value}")
            else:
                row_values.append(f"'{column_value}'")

        # カラム毎にカンマで分割する
        row_values_str = COMMA.join(row_values)

        if index != len(insert_datas_df) - 1:
            # レコード毎にカンマで分割する
            row_values_str = f"({row_values_str}),"
        else:
            row_values_str = f"({row_values_str})"

        # レコード文字列を配列に格納する
        recordList.append(row_values_str)

    insert_hql += BLANK.join(recordList)
    logger.debug(f"{table_name}に対するINSERTが実行されます。: {insert_hql}")

    # insert用hqlを実行する
    with conn.cursor() as cursor:
        cursor.execute(insert_hql)
        affected_rows = cursor.rowcount  # 挿入された行数を取得
        if affected_rows < 0:
            affected_rows = insert_datas_df.shape[0]
        # コミット
        conn.commit()

    logger.info(f"挿入された行数: {affected_rows}")  # 挿入された行数をログに記録

    logger.info(f"{table_name}テーブルのinsert用処理完了。")


@log.log_writer(logger)
def execute_delete(conn, table_name, where_clause=None):
    """
    Args:
        conn: 接続用オブジェクト
        table_name (str): 表。
        where_clause: 削除条件
    """
    logger.info(f"{table_name}テーブルのデータ削除処理開始。")
    try:
        delete_hql = f"DELETE FROM {table_name}"
        if where_clause:
            delete_hql += f" WHERE {where_clause}"

        logger.info(f"{table_name}に対するDELETEが実行されます。: {delete_hql}")

        # delete用hqlを実行する
        with conn.cursor() as cursor:
            cursor.execute(delete_hql)
            affected_rows = cursor.rowcount  # 削除された行数を取得
            conn.commit()

    except Exception as e:
        logger.error(f"DELETE処理でエラー発生: {str(e)}")
        conn.rollback()

    logger.info(f"{table_name}テーブルのデータ削除処理完了。")


@log.log_writer(logger)
def execute_update(conn, table_name, set_columns, where_conditions=None):
    """
    Hive用のUPDATE HQLを生成する
    :param table_name: 更新対象のテーブル名
    :param set_columns: SET句のカラムと値の辞書 例: {"column1": "value1", "column2": "value2"}
    :param where_conditions: WHERE句の条件の辞書（オプション） 例: {"column3": "value3", "column4": "value4"}
    :return: 生成された UPDATE 文
    """

    # SET 句の作成
    set_columns_dict = {
        k: v for d in set_columns for k, v in d.items()
    }  # リストを辞書に変換
    set_clause = ", ".join(
        [f"{col} = {format_sql_value(val)}" for col, val in set_columns_dict.items()]
    )

    where_clause = ""
    if where_conditions:
        conditions = []
        for col, val in where_conditions.items():
            if isinstance(val, list):  # 値がリストなら IN または IS NULL を作成
                null_check = " OR ".join(
                    [
                        (
                            f"{col} IS NULL"
                            if v is None
                            else f"{col} = {format_sql_value(v)}"
                        )
                        for v in val
                    ]
                )
                conditions.append(f"({null_check})")
            else:
                conditions.append(f"{col} = {format_sql_value(val)}")
        where_clause = " WHERE " + " AND ".join(conditions)

    # 最終的な UPDATE 文の作成
    update_hql = f"UPDATE {table_name} SET {set_clause}{where_clause};"

    logger.info(f"{table_name}に対する更新が実行されます。: {update_hql}")

    with conn.cursor() as cursor:
        cursor.execute(update_hql)
        affected_rows = cursor.rowcount  # 削除された行数を取得
        # コミット
        conn.commit()

    logger.info(f"更新された行数: {affected_rows}")  # 削除された行数をログに記録

    return update_hql


def format_sql_value(value):
    """
    SQL に適した形式に値を変換する
    """
    if value is None:
        return "NULL"
    elif isinstance(value, bool):  # Boolean は `TRUE` / `FALSE` に変換
        return "TRUE" if value else "FALSE"
    elif isinstance(value, (int, float)):  # 数値型はそのまま
        return str(value)
    else:  # 文字列はクォートする
        return f"'{value}'"


def generate_insert_overwrite_query(
    table_name, column_list, update_all_columns=True, logical_delete=True
):
    """
    外部フラグを使って、全カラム更新と論理削除を制御する INSERT OVERWRITE クエリを生成

    Args:
        table_name (str): 対象テーブル名
        column_list (list): カラム名リスト
        update_all_columns (bool): 全カラム更新を行うか（デフォルト: True）
        logical_delete (bool): 論理削除を行うか（デフォルト: True）

    Returns:
        str: 生成された SQL クエリ
    """

    # カラムごとの処理
    sql_column_expressions = []
    for col in column_list:
        if col == "DELETE_FLG":
            if logical_delete:
                # DELETE_FLG を論理削除のルールで更新
                sql_column_expressions.append(
                    "CASE WHEN delete_flg = FALSE OR delete_flg IS NULL THEN TRUE ELSE delete_flg END AS delete_flg"
                )
            else:
                # DELETE_FLG の更新を行わない
                sql_column_expressions.append("DELETE_FLG")
        else:
            if update_all_columns:
                # 通常カラムをすべて更新
                sql_column_expressions.append(col)
            else:
                # カラムを更新しない場合は、元の値をそのまま保持
                sql_column_expressions.append(f"{col}")

    sql_columns = ", ".join(sql_column_expressions)

    insert_overwrite_query = f"""
        INSERT OVERWRITE TABLE {table_name}
        SELECT {sql_columns}
        FROM {table_name}
    """
    return insert_overwrite_query


@log.log_writer(logger)
def execute_hive_update(
    conn, table_name, column_list, update_all_columns=True, logical_delete=True
):
    """
    Args:
        conn: 接続用オブジェクト
        table_name (str): 表。
        where_clause: 削除条件
    """
    logger.info(f"{table_name}テーブルのデータ削除処理開始。")
    try:
        # 列名称編集
        # sql_column_names = ', '.join([f"{col}" for col in column_list if col != "DELETE_FLG"])
        # insert_overwrite_query = f"""
        #     INSERT OVERWRITE TABLE {table_name}
        #     SELECT {sql_column_names},
        #         CASE
        #             WHEN delete_flg = FALSE OR delete_flg IS NULL THEN TRUE
        #             ELSE delete_flg
        #         END AS delete_flg
        #     FROM {table_name}
        # """
        insert_overwrite_query = generate_insert_overwrite_query(
            table_name, column_list, update_all_columns, logical_delete
        )

        logger.info(
            f"Hiveの{table_name}に対する更新が実行されます。: {insert_overwrite_query}"
        )
        # delete用hqlを実行する
        with conn.cursor() as cursor:
            cursor.execute(insert_overwrite_query)
            conn.commit()

        logger.info(f"論理削除成功しました。")  # 削除された行数をログに記録

    except Exception as e:
        logger.error(f"DELETE処理でエラー発生: {str(e)}")

    logger.info(f"{table_name}テーブルのデータ更新処理完了。")


def load_csv_to_mst(conn, csv_file_path, table_name):
    """
    csvデータをmasterにロードする

    param:
        conn, csv_file_path, table_name
    """
    hql = f"LOAD DATA INPATH '{csv_file_path}' INTO TABLE {table_name}"
    logger.info(hql)
    try:
        with conn.cursor() as cursor:
            cursor.execute(hql)
            print(f"Data loaded successfully from {csv_file_path} into {table_name}")
    except Exception as e:
        print(f"Failed to load data from {csv_file_path} into {table_name}")
        print(f"Error: {e}")
        raise e


@log.log_writer(logger)
def select_data(conn, condition_list, select_columns, table_name):
    """
    Args:
        condition_list (dict): condition_list = [
            ['条件1', '值1', '方法1'],
            ['条件2', '值2', '方法2'],
        ]
        ['条件2', '值2-1', '值2-2' ,'值2-3' ,'方法2'], ->column1 IN (1, 2, 3)
        select_columns (list): 表示列 ['name', 'age', 'city'] , NULL = *
        table_name (str): 表
        file_name (str): ファイル
    Returns:
        list: 結果
    """
    try:
        # 検索用HQL条件文格納する用配列
        where_conditions = []
        if condition_list is None:
            condition_list = []
        # 検索条件数分を繰り返して条件文を作成する
        for condition_item in condition_list:
            # 検索条件列
            condition_column = condition_item[0]
            # 検索条件値
            condition_value = condition_item[1]
            # 操作子
            condition_operator = condition_item[2]
            if isinstance(condition_value, (int, float)):
                condition_value = str(condition_value)
            elif condition_value is None:
                condition_value = "NULL"
            elif isinstance(condition_value, list):
                # INやNOTINを対応するため
                condition_value = f"({COMMA.join([hatena]*len(condition_value))})"
            else:
                condition_value = f"'{condition_value}'"

            where_conditions.append(
                f"{condition_column} {condition_operator} {condition_value}"
            )

        # AND文を追加する
        where_clause = " AND ".join(where_conditions) if where_conditions else ""

        # 検索対象列
        if isinstance(select_columns, tuple):
            select_columns = list(select_columns)
        select_columns_str = COMMA.join(select_columns) if select_columns else "*"

        # 検索用HQL文
        select_query = f"SELECT {select_columns_str} FROM {table_name}"
        if where_clause:
            select_query += f" WHERE {where_clause}"

        # 検索用hqlを実行する
        result_df = None
        logger.debug(f"検索時HQL★{select_query}")
        with conn.cursor() as cursor:
            cursor.execute(select_query)
            result_list = cursor.fetchall()
            # 結果をDataFrameに変換
            columns = [
                column[0].split(".")[-1].upper() for column in cursor.description
            ]
            result_df = pd.DataFrame(result_list, columns=columns)

        return result_df

    except Exception as e:
        msg = f"{table_name}の検索時エラー"
        traceback.format_stack()
        raise e


@log.log_writer(logger)
def get_master_data(conn, condition_list, select_columns, table_name):
    """
    マスタデータを取得する
    params
        conn: 接続用シングルトン
        table_name: 対象マスタテーブル名
        condition_list: # 検索条件格納用リスト、ph1にては一旦条件なし
        select_columns: 検索対象列
    """
    result_df = None
    try:
        result_df = select_data(conn, condition_list, select_columns, table_name)
    except Exception as e:
        msg = f"{table_name}マスタのデータ取得時エラーが発生しました。"
        logger.error(f"{msg}:{e.args[0]}")
        traceback.format_exc()
    return result_df


@log.log_writer(logger)
def getSystemDate(conn):
    """DWH環境のシステム日時を取得する"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT current_timestamp")
            return cursor.fetchone()[0]
    except Exception as e:
        msg = "システム日時取得時エラー発生しました。"
        logger.error(f"{msg}:{e.args[0]}")
        traceback.format_exc()
    finally:
        pass


@log.log_writer(logger)
def generate_id(conn, condition_list, select_columns, table_name):
    """
    採番処理
    params:
        conn: hive接続用オブジェクト
        condition_list: 検索用リスト
        select_columns: 検索対象カラム
        table_name: テーブル名
    """
    # 対象列値 + 001 (エリアマスタの場合、法人番号 + 001)
    numbering_id = condition_list[0][1]
    # 検索対象列
    if isinstance(select_columns, tuple):
        select_columns = list(select_columns)
    # 既存データあるかどうかを検索する
    result_list = select_data(conn, condition_list, select_columns, table_name)
    if result_list is None or len(result_list) <= 0:
        numbering_id = get_new_id(result_list)
    return numbering_id


def get_new_id(result_list):
    """自動採番"""
    # ID列の値を抽出してリストに保存
    # id_column_values = [row[0] for row in result_list]
    # ID列の最大値を取得
    # max_id = max(id_column_values)
    numbering_id = None
    # Noneを持つ行を削除
    result_list = result_list.dropna(subset=["BUILDING_ID"])
    max_id = result_list["BUILDING_ID"].max()
    # with conn.cursor() as cursor:
    #     select_hql = f"select max({select_column}) from {table_name}"
    #     cursor.execute(select_hql)
    # 最大値取得
    # max_id = cursor.fetchone()[0]
    if max_id is not None:
        # マスタテーブルにデータが存在する場合は、最後のIDに1を加えて新しいIDを生成する
        # 採番箇所をスライス
        pk_str = max_id[0:-3]
        number_str = max_id[-3:]
        max_id_numbering = str(int(number_str) + 1).zfill(len(number_str))
        # テーブルが存在しない場合はIDを001から採番する
        numbering_id = pk_str + max_id_numbering
    return numbering_id


# def get_new_id(result_list):
#     '''自動採番'''
#     #ID列の値を抽出してリストに保存
#     # id_column_values = [row[0] for row in result_list]
#     # ID列の最大値を取得
#     # max_id = max(id_column_values)
#     numbering_id = None
#     # Noneを持つ行を削除
#     result_list = result_list.dropna(subset=['BUILDING_ID'])
#     max_id = result_list["BUILDING_ID"].max()
#     # with conn.cursor() as cursor:
#     #     select_hql = f"select max({select_column}) from {table_name}"
#     #     cursor.execute(select_hql)
#         # 最大値取得
#         # max_id = cursor.fetchone()[0]
#     if max_id is not None:
#         # マスタテーブルにデータが存在する場合は、最後のIDに1を加えて新しいIDを生成する
#         # 採番箇所をスライス
#         pk_str = max_id[0:-3]
#         number_str = max_id[-3:]
#         max_id_numbering = str(int(number_str) + 1).zfill(len(number_str))
#         # テーブルが存在しない場合はIDを001から採番する
#         numbering_id = pk_str + max_id_numbering
#     return numbering_id


def get_new_id(max_id):
    """自動採番"""
    numbering_id = None
    # 採番箇所をスライス
    pk_str = max_id[0:-3]
    number_str = max_id[-3:]
    max_id_numbering = str(int(number_str) + 1).zfill(len(number_str))
    # テーブルが存在しない場合はIDを001から採番する
    numbering_id = pk_str + max_id_numbering

    return numbering_id


# def get_file_status(conn, input_file_name):
#     '''
#     ファイル処理ステータス取得
#     params:
#         conn   Hive接続し
#         input_file_name ファイル名
#     return:
#         file_status  ファイル処理ステータス
#     '''
#     # ファイル処理ステータステーブル追加対応
#     file_status = False
#     try:
#         condition_list = [["FILE_NAME", input_file_name, constants.HqlConditonOperators.EQUAL.value]]
#         select_columns = ["STATUS"]
#         status_table_name = "DB" + DOT + constants.BusinessTable.FPSTBL.value
#         result_list = select_data(conn, condition_list, select_columns, status_table_name)

#         # ファイルステータスがエラーか処理済の場合、カレントファイルの処理をスキップする
#         if result_list is not None and len(result_list) > 0: file_status = True # 処理不要
#     except Exception as e:
#         logger.error(f"{input_file_name}ファイルの{status_table_name}のファイルステータス取得処理が失敗しました。")
#         raise e

#     return file_status

# def insert_file_status_info(conn, file_name):
#     '''
#     企業カルテ用生データと集計データ
#     params:
#         conn
#         corporate_df   処理対象シート情報格納DataFrame
#         building_df カラム情報
#         energy_df
#         file_name
#     return:
#         energy_dic  エネルギー情報辞書
#     '''
#     try:
#         # 処理済みファイルをprocessed_filesへ移動する
#         insert_file_status_data =[(file_name, None, None,
#                                    constants.FileProcessStatus.COMPELETED.value, f"{utils.get_current_timestamp()}",f"{utils.get_sysuser()}")]
#         # ファイル処理状況テーブルデータ登録
#         insert_data(conn, insert_file_status_data, constants.FPSTBL_COLUMNS, None,
#                     schema_middle + DOT + constants.BusinessTable.FPSTBL.value, file_name)
#     except Exception as e:
#         logger.error(f"データ登録が失敗しました。{e.__traceback__}")
#         raise e

# def get_building_id(conn, sheet_df, corporate_df, area_id):
# def get_building_id(conn, building_name, corporate_number, bank_cd, area_id):
#     '''
#     エリアマスタから既存エリアの存在チェックと採番処理
#     既に既存データ存在していたら、そのまま利用、存在していない場合、採番処理実行
#     params:
#         data_list   登録データリスト
#         column_list カラム情報
#     return:
#         new_area_id  採番エリアID
#     '''
#     try:
#         condition_list = [["BANK_CODE", bank_cd, constants.HqlConditonOperators.EQUAL.value],
#                             ["CORPORATE_NUMBER", corporate_number, constants.HqlConditonOperators.EQUAL.value],
#                             ["AREA_ID", area_id, constants.HqlConditonOperators.EQUAL.value]]
#                             # ["BUILDING_NAME", building_name, constants.HqlConditonOperators.EQUAL.value]]
#         select_columns = ["BUILDING_ID", "BUILDING_NAME"]
#         inputinfo_table_name = schema_middle + DOT + constants.BusinessTable.ABITBL.value
#         result_list = select_data(conn, condition_list, select_columns, inputinfo_table_name)

#         building_id = None
#         if result_list is not None and len(result_list) > 0:
#             # 対象法人既に登録ありの場合、事業所名でチェックする
#             for index, item in result_list.iterrows():
#                 if item["BUILDING_NAME"] == building_name:
#                     building_id = item["BUILDING_ID"]
#                     break

#             if building_id is None:
#                 building_id = get_new_id(result_list)
#         else:
#             # 自動採番処理
#             building_id = area_id + constants.NumberingStartValue.THREE_NUMBER.value
#         return building_id
#     except Exception as e:
#         logger.error(traceback.format_exc())
#         raise e

# def get_area_id(conn, corporate_number):
#     '''
#     エリアマスタから既存エリアの存在チェックと採番処理
#     既に既存データ存在していたら、そのまま利用、存在していない場合、採番処理実行
#     params:
#         data_list   登録データリスト
#         column_list カラム情報
#     return:
#         new_area_id  採番エリアID
#     '''
#     try:
#         condition_list = [["CORPORATE_NUMBER", corporate_number, constants.HqlConditonOperators.EQUAL.value]]
#         select_columns = ["AREA_ID"]
#         inputinfo_table_name = schema_middle + DOT + constants.MasterTable.AIMST.value
#         result_list = select_data(conn, condition_list, select_columns, inputinfo_table_name)

#         area_id = None
#         if result_list is not None and len(result_list) > 0:
#             # 対象法人既に登録ありの場合、事業所名でチェックする
#             for index, item in result_list.iterrows():
#                 area_id = item["AREA_ID"]
#         else:
#             # 自動採番処理
#             area_id = corporate_number + constants.NumberingStartValue.THREE_NUMBER.value
#         return area_id
#     except Exception as e:
#         logger.error(traceback.format_exc())
#         raise e

'''
PH1では一旦利用不要のためコメントアウトしています。
def delete_data(conn, data_list, partition_columns_dic, table_name, file_name):
    """
    （注意！）
    Args:
        data_list (dict): データ{'a':'b','c':'d'}
        partition_columns_dic (dict): 区分
        table_name (str): 表
        file_name (str): ファイル
    """
    try:
        cursor = conn.cursor()
        
        # 条件
        conditions = [f"{column} = '{value}'" for column, value in data_list.items()] if data_list else []
        
        # 分区条件
        partition_conditions = [f"{column} = '{value}'" for column, value in partition_columns_dic.items()] if partition_columns_dic else []
        
        # 削除判定
        where_conditions = conditions + partition_conditions
        where_clause = " AND ".join(where_conditions) if where_conditions else ""
        
        # 削除
        delete_query = f"DELETE FROM {table_name}"
        if where_clause:
            delete_query += f" WHERE {where_clause}"
            
        # 実行
        cursor.execute(delete_query)
        conn.commit()

        #log
        loggerModule.MyAppLog.info(f"{delete_query}実行成功")  
    
    except DatabaseError as e:
        error_message = traceback.format_exc()
        error_line = str(e.__traceback__.tb_lineno) 
        error_str = f"{file_name} : DatabaseError occurred at line {error_line}: {error_message}"
        errorMsgModule.ErrorHandler.handle_error("ValueError", error_str)      
                           
    except Exception as e:
        error_type = type(e).__name__
        error_message = traceback.format_exc()  
        error_line = str(e.__traceback__.tb_lineno) 
        error_str = f"{file_name} :{error_type} Error occurred at line {error_line}: {error_message}"
        errorMsgModule.ErrorHandler.handle_error("ValueError", error_str)
'''
'''
PH1では一旦利用不要のためコメントアウトしています。
def delete_Row(conn, data_list, partition_columns_dic, table_name, file_name):
    """
    Args:
        data_list (dict): データ{'a':'b','c':'d'}
        partition_columns_dic (dict): 区分
        table_name (str): 表
        file_name (str): ファイル 
    """
    try:
        cursor = conn.cursor()
        
        # 条件
        conditions = [f"{condition_column} = '{condition_value}'" for condition_column, condition_value in data_list.items()]if data_list else []

        # 分区判定
        partition_conditions = [f"{partition_column} = '{partition_value}'" for partition_column, partition_value in partition_columns_dic.items()]if partition_columns_dic else []
            
        #　条件構築
        where_conditions = conditions + partition_conditions + ["delete = '0'"]
        where_clause = " AND ".join(where_conditions)
            
        # delete更新
        delete_update_query = f"UPDATE {table_name} SET delete = '1' WHERE {where_clause}"
        
        # 実行
        cursor.execute(delete_update_query)
        conn.commit()
        
        #追加log
        loggerModule.MyAppLog.info(f"{delete_update_query}実行成功")  
    
    except DatabaseError as e:
        error_message = traceback.format_exc()
        error_line = str(e.__traceback__.tb_lineno) 
        error_str = f"{file_name} : DatabaseError occurred at line {error_line}: {error_message}"
        errorMsgModule.ErrorHandler.handle_error("ValueError", error_str)            
                     
    except Exception as e:
        error_type = type(e).__name__
        error_message = traceback.format_exc()  
        error_line = str(e.__traceback__.tb_lineno) 
        error_str = f"{file_name} :{error_type} Error occurred at line {error_line}: {error_message}"
        errorMsgModule.ErrorHandler.handle_error("ValueError", error_str)
'''
'''
PH1では一旦利用不要のためコメントアウトしています。
def update_data(conn, data_list, update_data, partition_columns_dic, table_name, file_name):
    """
    Args:
        data_list (dict): データ{'a':'b','c':'d'}
        update_data(dict) :列{'a':'b','c':'d'}
        partition_columns_dic (dict): 区分 
        table_name (str): 表
        file_name (str): ファイル       
    Returns:
        bool: 更新操作是否成功。
    """
    try:
        cursor = conn.cursor()
        
        # 更新内容
        update_clause = ", ".join([f"{column} = '{value}'" for column, value in update_data.items()])
        
        # 条件
        conditions = [f"{column} = '{value}'" for column, value in data_list.items()] if data_list else []
        
        # 分区条件
        partition_conditions = [f"{column} = '{value}'" for column, value in partition_columns_dic.items()] if partition_columns_dic else []
        
        # 条件構築
        where_conditions = conditions + partition_conditions
        where_clause = " AND ".join(where_conditions) if where_conditions else ""
        
        # update構築
        update_query = f"UPDATE {table_name} SET {update_clause}"
        if where_clause:
            update_query += f" WHERE {where_clause}"
        
        # 実行
        cursor.execute(update_query)
        conn.commit()
        
        # log記録
        loggerModule.MyAppLog.info(f"{update_query}実行成功")  
        
    except DatabaseError as e:
        error_message = traceback.format_exc()
        error_line = str(e.__traceback__.tb_lineno) 
        error_str = f"{file_name} : DatabaseError occurred at line {error_line}: {error_message}"
        errorMsgModule.ErrorHandler.handle_error("ValueError", error_str)
        
    except Exception as e:
        error_type = type(e).__name__
        error_message = traceback.format_exc()  
        error_line = str(e.__traceback__.tb_lineno) 
        error_str = f"{file_name} :{error_type} Error occurred at line {error_line}: {error_message}"
        errorMsgModule.ErrorHandler.handle_error("ValueError", error_str)
'''
