from collections.abc import Iterable, Mapping
from copy import deepcopy
from datetime import datetime
from pandas._libs.tslibs.nattype import NaTType

def format_datetimes(data, fmt="%Y-%m-%d %H:%M:%S", in_place=True, nest=True):
    """
    ネストされたコレクション（dict, list）の datetime オブジェクトを再帰的にフォーマットする。

    :param data: 処理対象のコレクション（dict, list, tuple, set）
    :param fmt: 変換後の日時フォーマット（デフォルト "%Y-%m-%d %H:%M:%S"）
    :param in_place: 元のデータを直接変更するか（デフォルト True）。
        ただし、タプルやセットなど変更不可の型の場合は必ず新しいオブジェクトを返す。
    :param nest: ネストされたデータを再帰的に処理するか（デフォルト True）。
        ただし、タプルやセットでは無視される。
    :return: 新しいコレクションを返す。
    """

    if isinstance(data, Mapping):  # 辞書を処理
        if not in_place:
            data = deepcopy(data)
        for key, value in data.items():
            if isinstance(value, NaTType):
                data[key] = None
            elif isinstance(value, datetime):
                data[key] = value.strftime(fmt)
            elif (
                nest
                and isinstance(value, (Mapping, Iterable))
                and not isinstance(value, str)
            ):
                data[key] = format_datetimes(value, fmt, True, nest)
    elif isinstance(data, list):  # リストを処理
        if not in_place:
            data = deepcopy(data)
        for i in range(len(data)):
            if isinstance(data[i], datetime):
                data[i] = data[i].strftime(fmt)
            elif (
                nest
                and isinstance(data[i], (Mapping, Iterable))
                and not isinstance(data[i], str)
            ):
                data[i] = format_datetimes(data[i], fmt, True, nest)
    elif isinstance(data, tuple):  # タプルを処理（新しいタプルを返す）
        return tuple(
            value.strftime(fmt) if isinstance(value, datetime) else value
            for value in data
        )
    elif isinstance(data, set):  # セットを処理（新しいセットを返す）
        return {
            value.strftime(fmt) if isinstance(value, datetime) else value
            for value in data
        }

    return data
