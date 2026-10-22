from dataclasses import dataclass, fields
from typing import Any, Dict, Set, Type, TypeVar, get_args, get_origin

T = TypeVar("T")


def dict_to_dto(data_class: Type[T], data: Dict[str, Any]) -> T:
    """
    辞書を指定されたデータクラスのインスタンスに変換する関数

    Args:
        data_class (Type[T]): 変換先のデータクラス
        data (Dict[str, Any]): 変換元の辞書データ

    Returns:
        T: 指定されたデータクラスのインスタンス
    """
    kwargs = {}
    for field in fields(data_class):
        field_value = data.get(field.name)
        field_type = field.type

        # シンプル形式
        if isinstance(field.type, type) and issubclass(
            field.type, (int, str, float, bool)
        ):
            kwargs[field.name] = field_value
        # ネスト dataclass
        elif hasattr(field.type, "__dataclass_fields__"):
            kwargs[field.name] = dict_to_dto(field.type, field_value or {})
        # List 型の場合
        elif get_origin(field_type) is list:
            inner_type = get_args(field_type)[0]  # List の中身の型を取得
            if hasattr(inner_type, "__dataclass_fields__"):
                # List 中の要素を dataclass に変換
                kwargs[field.name] = [
                    dict_to_dto(inner_type, item) for item in (field_value or [])
                ]
            else:
                kwargs[field.name] = field_value  # dataclass 以外の List 元素直接入れる
        else:
            kwargs[field.name] = field_value  # 他の型直接入れる

    return data_class(**kwargs)


def include(data: Dict, allowed_keys: Set) -> Dict:
    """
    allowed_keys にある key だけが含まれる新しい dict を返す。
    """
    return {k: v for k, v in data.items() if k in allowed_keys}


def exclude(data: Dict, disallowed_keys: Set) -> Dict:
    """
    disallowed_keys にある key を除いた新しい dict を返す。
    """
    return {k: v for k, v in data.items() if k not in disallowed_keys}
