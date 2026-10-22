import datetime
import os
from enum import Enum

from cndx_corp_back.common.log import CorpLogger, log_writer
from cndx_corp_back.constant import constants as Constants
from cndx_corp_back.constant.messages import MESSAGES

# import pytz


logger = CorpLogger()


def set_log_level(run_mode):
    """
    AirflowのVariableから実行モードに応じてログレベルを設定する。
    - 開発環境、ステージング環境ではDEBUGレベル
    - 本番環境ではINFOレベル

    パラメータ:
        run_mode (str): 実行モード

    戻り値:
        なし
    """
    if run_mode == Constants.RunMode.DEV.value:
        os.environ["LOG_LEVEL"] = "DEBUG"
    elif run_mode == Constants.RunMode.STG.value:
        os.environ["LOG_LEVEL"] = "DEBUG"
    elif run_mode == Constants.RunMode.PROD.value:
        os.environ["LOG_LEVEL"] = "INFO"


@log_writer(logger)
def get_current_date():
    """
    現在の日付を"YYYY-MM-DD"形式の文字列で取得する。

    パラメータ:
        なし

    戻り値:
        str: 現在の日付を表す文字列。
    """
    return datetime.datetime.now().strftime("%Y-%m-%d")


# @log_writer(logger)
def get_current_timestamp():
    """
    現在のタイムスタンプを"YYYY-MM-DD HH:MM:SS"形式の文字列で取得する。

    パラメータ:
        なし

    戻り値:
        str: 現在のタイムスタンプを表す文字列。
    """
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# @log_writer(logger)
# def get_current_tokyo_timestamp():
#     """
#     タイムゾーンが東京現在のタイムスタンプを"yyyyMMddHMS"形式の文字列で取得する。

#     パラメータ:
#         なし

#     戻り値:
#         str: 東京現在のタイムスタンプを表す文字列。
#     """
#     # タイムゾーンが取得する
#     timezone = pytz.timezone("Asia/Tokyo")
#     # UTC時間が東京時間を変換する
#     local_time = datetime.datetime.now().replace(tzinfo=pytz.utc).astimezone(timezone)
#     return local_time.strftime("%Y%m%d%H%M%S")


def get_message(message_id, **kwargs):
    """
    メッセージIDに対応するメッセージを取得する。

    パラメータ:
        message_id (str): メッセージID
        keyword args: 埋め字
    戻り値:
        str: メッセージ
    """

    res = MESSAGES.get(message_id)
    if res is None:
        return None

    return res.format(**kwargs)


def get_query(query_base: Enum, **kwargs):

    return query_base.value.format(**kwargs)
