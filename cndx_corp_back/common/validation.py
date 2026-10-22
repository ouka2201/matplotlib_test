import re

from cndx_corp_back.entity.m_user_entity import MUser
from cndx_corp_back.utils.utils import get_message


def required_check(
    input: str | dict, item_name: str, err_list: list, dict_key=None, msg_id="REQUIRED"
):
    """
    必須チェックをする関数

    Args:
        input (str or dict): チェック対象かリクエストdict
        item_name (str): 項目名
        err_list (list): エラーメッセージを格納するリスト

    Returns:
        None: エラーメッセージがある場合はerr_listに追加される
    """
    if isinstance(input, dict):
        value = input.get(dict_key, None)
    else:
        value = input

    is_none = value is None
    is_empty = value == ""
    if is_none or is_empty:
        err_list.append(get_message(msg_id, item_name=item_name))
        return False
    return True


def length_check(
    value: str,
    item_name: str,
    err_list: list,
    min_length=None,
    max_length=None,
    msg_id=None,
):
    """
    文字列の長さをチェックする関数

    Args:
        value (any): チェック対象の値
        item_name (str): 項目名
        err_list (list): エラーメッセージを格納するリスト
        int_length (int): 整数部の最大長
        decimal_length (int): 小数部の最大長

    Returns:
        None: エラーメッセージがある場合はerr_listに追加される
    """
    check_ok = True
    if min_length is not None and len(str(value)) < min_length:
        if msg_id is None:
            if min_length == max_length:
                err_list.append(
                    get_message(
                        "EXACT_LENGTH_ERROR", item_name=item_name, length=min_length
                    )
                )
            else:
                err_list.append(
                    get_message("TOO_SHORT", item_name=item_name, min_length=min_length)
                )
        check_ok = False
    if max_length is not None and len(str(value)) > max_length:
        if msg_id is None:
            if min_length == max_length:
                err_list.append(
                    get_message(
                        "EXACT_LENGTH_ERROR", item_name=item_name, length=max_length
                    )
                )
            else:
                err_list.append(
                    get_message("TOO_LONG", item_name=item_name, max_length=max_length)
                )
        check_ok = False
    if msg_id is not None and not check_ok:
        err_list.append(get_message(msg_id, item_name=item_name))
    return check_ok


def decimal_digits_check(
    value: str,
    item_name: str,
    err_list: list,
    integer_digits=None,
    decimal_digits=None,
    msg_id=None,
):
    """
    数値の整数部と小数部の桁数をチェックする関数

    Args:
        value (any): チェック対象の値
        item_name (str): 項目名
        err_list (list): エラーメッセージを格納するリスト
        integer_digits (int): 整数部の最大桁数
        decimal_digits (int): 小数部の最大桁数（デフォルト値は0）
        msg_id (str, optional): エラーメッセージのID（オプション）

    Returns:
        bool: エラーメッセージがある場合はFalse、ない場合はTrue
    """
    # TODO この処理は、小数点がない場合と .1 のテストケース

    check_ok = True

    value = str(value)
    # 数値でない場合はエラー
    if re.search(r"^[0-9]*(\.[0-9]+)?$", value) is None:
        err_list.append(get_message("NOT_DECIMAL", item_name=item_name))
        return False

    # 小数点で分割
    parts = value.split(".")

    # 整数部の長さをチェック
    if integer_digits is not None and len(parts[0]) > integer_digits:
        if msg_id is None:
            err_list.append(
                get_message(
                    "INTEGER_PART_TOO_LONG",
                    item_name=item_name,
                    integer_digits=integer_digits,
                )
            )
        check_ok = False

    # 小数部の長さをチェック（小数点がない場合は小数部の長さを0とする）
    if decimal_digits is not None and len(parts) > 1 and len(parts[1]) > decimal_digits:
        if msg_id is None:
            err_list.append(
                get_message(
                    "DECIMAL_PART_TOO_LONG",
                    item_name=item_name,
                    decimal_digits=decimal_digits,
                )
            )
        check_ok = False
    if msg_id is not None and not check_ok:
        err_list.append(get_message(msg_id, item_name=item_name))
    return check_ok


def numeric_range_check(
    value: str,
    item_name: str,
    err_list: list,
    min_value=None,
    max_value=None,
    msg_id=None,
):
    """
    数値が指定された範囲内にあるかをチェックする関数

    Args:
        value (str): チェック対象の値
        item_name (str): 項目名
        err_list (list): エラーメッセージを格納するリスト
        min_value (float, optional): 最小値
        max_value (float, optional): 最大値
        msg_id (str, optional): エラーメッセージのID（オプション）

    Returns:
        None: エラーメッセージがある場合はerr_listに追加される
    """
    # 正常動作の桁数制限テスト

    check_ok = True
    try:
        num = float(value)
    except ValueError:
        return False

    if min_value is not None and value < min_value:
        if msg_id is None:
            err_list.append(
                get_message("TOO_SMALL", item_name=item_name, min_value=min_value)
            )
        check_ok = False
    if max_value is not None and value > max_value:
        if msg_id is None:
            err_list.append(
                get_message("TOO_LARGE", item_name=item_name, max_value=max_value)
            )
        check_ok = False
    if msg_id is not None and not check_ok:
        err_list.append(get_message(msg_id, item_name=item_name))
    return check_ok


def allowed_characters_check(
    value,
    item_name: str,
    err_list: list,
    allow_numeric=False,
    allow_lowercase=False,
    allow_uppercase=False,
    allow_kana=False,
    allow_space=False,
    allow_symbols=False,
    allow_newline=False,
    allow_fullwidth_numeric=False,
    allow_fullwidth_lowercase=False,
    allow_fullwidth_uppercase=False,
    allow_fullwidth_kana=False,
    allow_fullwidth_space=False,
    allow_fullwidth_symbols=False,
    allow_external_chars=False,
):
    """
    値が許可されない文字を含むかをチェックする関数

    Args:
        value (str): チェック対象の値
        item_name (str): 項目名
        err_list (list): エラーメッセージを格納するリスト
        allow_numeric (bool, optional): 半角数字を許可するか
        allow_lowercase (bool, optional): 半角小文字を許可するか
        allow_uppercase (bool, optional): 半角大文字を許可するか
        allow_kana (bool, optional): 半角仮名を許可するか
        allow_space (bool, optional): 半角スペースを許可するか
        allow_symbols (bool, optional): 半角記号を許可するか
        allow_newline (bool, optional): 改行コードを許可するか
        allow_fullwidth_numeric (bool, optional): 全角数字を許可するか
        allow_fullwidth_lowercase (bool, optional): 全角小文字を許可するか
        allow_fullwidth_uppercase (bool, optional): 全角大文字を許可するか
        allow_fullwidth_kana (bool, optional): 全角仮名を許可するか
        allow_fullwidth_space (bool, optional): 全角スペースを許可するか
        allow_fullwidth_symbols (bool, optional): 全角記号を許可するか
        allow_external_chars (bool, optional): 外部文字を許可するか

    Returns:
        None: エラーメッセージがある場合はerr_listに追加される
    """
    check_ok = True
    value = str(value)

    if not allow_numeric and re.search(r"[0-9]", value) is not None:
        err_list.append(get_message("NUMERIC_NOT_ALLOWED", item_name=item_name))
        check_ok = False
    if not allow_lowercase and re.search(r"[a-z]", value) is not None:
        err_list.append(get_message("LOWERCASE_NOT_ALLOWED", item_name=item_name))
        check_ok = False
    if not allow_uppercase and re.search(r"[A-Z]", value) is not None:
        err_list.append(get_message("UPPERCASE_NOT_ALLOWED", item_name=item_name))
        check_ok = False
    if not allow_kana and re.search(r"[ｦ-ﾟ]", value) is not None:
        err_list.append(get_message("KANA_NOT_ALLOWED", item_name=item_name))
        check_ok = False
    if not allow_space and re.search(r"[ ]", value) is not None:
        err_list.append(get_message("SPACE_NOT_ALLOWED", item_name=item_name))
        check_ok = False
    if not allow_symbols and re.search(r"[!-/:-@[-`{-~]", value) is not None:
        err_list.append(get_message("SYMBOL_NOT_ALLOWED", item_name=item_name))
        check_ok = False
    if not allow_newline and re.search(r"[\n\r]", value) is not None:
        err_list.append(get_message("NEWLINE_NOT_ALLOWED", item_name=item_name))
        check_ok = False
    if not allow_fullwidth_numeric and re.search(r"[０-９]", value) is not None:
        err_list.append(
            get_message("FULLWIDTH_NUMERIC_NOT_ALLOWED", item_name=item_name)
        )
        check_ok = False
    if not allow_fullwidth_lowercase and re.search(r"[ａ-ｚ]", value) is not None:
        err_list.append(
            get_message("FULLWIDTH_LOWERCASE_NOT_ALLOWED", item_name=item_name)
        )
        check_ok = False
    if not allow_fullwidth_uppercase and re.search(r"[Ａ-Ｚ]", value) is not None:
        err_list.append(
            get_message("FULLWIDTH_UPPERCASE_NOT_ALLOWED", item_name=item_name)
        )
        check_ok = False
    if (
        not allow_fullwidth_kana
        and re.search(r"[\u3040-\u309F\u30A0-\u30FF]", value) is not None
    ):
        err_list.append(get_message("FULLWIDTH_KANA_NOT_ALLOWED", item_name=item_name))
        check_ok = False
    if not allow_fullwidth_space and re.search(r"[　]", value) is not None:
        err_list.append(get_message("FULLWIDTH_SPACE_NOT_ALLOWED", item_name=item_name))
        check_ok = False
    if (
        not allow_fullwidth_symbols
        and re.search(r"[！-／：-＠［-｀｛-～]", value) is not None
    ):
        err_list.append(
            get_message("FULLWIDTH_SYMBOL_NOT_ALLOWED", item_name=item_name)
        )
        check_ok = False
    if not allow_external_chars and re.search(r"[\uE000-\uF8FF]", value) is not None:
        err_list.append(get_message("EXTERNAL_CHAR_NOT_ALLOWED", item_name=item_name))
        check_ok = False
    return check_ok


import re

# コンスタント定義：正規表現はコンパイルしても可
CHARACTER_RULES = [
    {
        "message_key": "NUMERIC_NOT_ALLOWED",
        "pattern": r"[0-9]",
        "option_key": "allow_numeric",
        "char_class": "0-9",
    },
    {
        "message_key": "LOWERCASE_NOT_ALLOWED",
        "pattern": r"[a-z]",
        "option_key": "allow_lowercase",
        "char_class": "a-z",
    },
    {
        "message_key": "UPPERCASE_NOT_ALLOWED",
        "pattern": r"[A-Z]",
        "option_key": "allow_uppercase",
        "char_class": "A-Z",
    },
    {
        "message_key": "KANA_NOT_ALLOWED",
        "pattern": r"[ｦ-ﾟ]",
        "option_key": "allow_kana",
        "char_class": "ｦ-ﾟ",
    },
    {
        "message_key": "SPACE_NOT_ALLOWED",
        "pattern": r"[ ]",
        "option_key": "allow_space",
        "char_class": " ",
    },
    {
        "message_key": "SYMBOL_NOT_ALLOWED",
        "pattern": r"[!-/:-@[-`{-~]",
        "option_key": "allow_symbols",
        "char_class": "!-/:-@\\[-`{-~",
    },
    {
        "message_key": "NEWLINE_NOT_ALLOWED",
        "pattern": r"[\n\r]",
        "option_key": "allow_newline",
        "char_class": r"\n\r",
    },
    {
        "message_key": "FULLWIDTH_NUMERIC_NOT_ALLOWED",
        "pattern": r"[０-９]",
        "option_key": "allow_fullwidth_numeric",
        "char_class": "０-９",
    },
    {
        "message_key": "FULLWIDTH_LOWERCASE_NOT_ALLOWED",
        "pattern": r"[ａ-ｚ]",
        "option_key": "allow_fullwidth_lowercase",
        "char_class": "ａ-ｚ",
    },
    {
        "message_key": "FULLWIDTH_UPPERCASE_NOT_ALLOWED",
        "pattern": r"[Ａ-Ｚ]",
        "option_key": "allow_fullwidth_uppercase",
        "char_class": "Ａ-Ｚ",
    },
    {
        "message_key": "FULLWIDTH_KANA_NOT_ALLOWED",
        "pattern": r"[\u3040-\u309F\u30A0-\u30FF]",
        "option_key": "allow_fullwidth_kana",
        "char_class": r"\u3040-\u309F\u30A0-\u30FF",
    },
    {
        "message_key": "FULLWIDTH_SPACE_NOT_ALLOWED",
        "pattern": r"[　]",
        "option_key": "allow_fullwidth_space",
        "char_class": "　",
    },
    {
        "message_key": "FULLWIDTH_SYMBOL_NOT_ALLOWED",
        "pattern": r"[！-／：-＠［-｀｛-～]",
        "option_key": "allow_fullwidth_symbols",
        "char_class": "！-／：-＠［-｀｛-～",
    },
    {
        "message_key": "EXTERNAL_CHAR_NOT_ALLOWED",
        "pattern": r"[\uE000-\uF8FF]",
        "option_key": "allow_external_chars",
        "char_class": r"\uE000-\uF8FF",
    },
]


def allowed_characters_check(value, item_name: str, err_list: list, **options) -> bool:
    check_ok = True
    value = str(value)

    for rule in CHARACTER_RULES:
        if not options.get(rule["option_key"], False) and re.search(
            rule["pattern"], value
        ):
            err_list.append(get_message(rule["message_key"], item_name=item_name))
            check_ok = False

    return check_ok


def check_only_allowed_characters(
    value: str, item_name: str, err_list: list, **options
) -> bool:
    allowed_char_classes = []

    for rule in CHARACTER_RULES:
        if options.get(rule["option_key"], False):
            allowed_char_classes.append(rule["char_class"])

    if not allowed_char_classes:
        err_list.append(f"{item_name} に許可されている文字種がありません")
        return False

    allowed_pattern = f"^[{''.join(allowed_char_classes)}]*$"
    if not re.fullmatch(allowed_pattern, value):
        err_list.append(get_message("ONLY_ALLOWED_CHARACTERS", item_name=item_name))
        return False

    return True


def integer_format_check(value: str, item_name: str, err_list: list):
    """
    整数の形式かをチェックする関数

    Args:
        value (str): チェック対象の値
        item_name (str): 項目名
        err_list (list): エラーメッセージを格納するリスト

    Returns:
        None: エラーメッセージがある場合はerr_listに追加される
    """
    value = str(value)
    if re.search(r"^[0-9]*$", value) is None:  # TODO isnumeric() に変更
        err_list.append(get_message("NOT_NUMERIC", item_name=item_name))
        return False
    return True


def newline_check(value: str, item_name: str, err_list: list):
    """
    改行コードを含むかをチェックする関数

    Args:
        value (str): チェック対象の値
        item_name (str): 項目名
        err_list (list): エラーメッセージを格納するリスト

    Returns:
        None: エラーメッセージがある場合はerr_listに追加される
    """
    value = str(value)
    if re.search(r"[\n\r]", value) is not None:
        err_list.append(get_message("NEWLINE_NOT_ALLOWED", item_name=item_name))
        return False
    return True


def is_chara_code_ok(value: str):
    """
    外字判定
    Args:
        value (str): チェック対象の値

    Returns:
        true: ok
        false: 'shift-jis', 'cp932', 'utf-8'以外の外字
    """
    JP_ENCODE = "shift-jis", "cp932", "utf-8"
    for char in JP_ENCODE:
        try:
            r = value.encode(char).hex
        except UnicodeDecodeError:
            return False
    return True


def get_message_list(e: Exception) -> list:
    """
    PydanticのValidationErrorからエラーメッセージを抽出する関数
    """
    error_messages = []
    for error in e.errors():
        # エラーメッセージを取り出す
        loc_str = ""
        for loc in error["loc"]:
            if isinstance(loc, int):
                loc_str += f"[{loc}]"
            else:
                if loc_str and not loc_str.endswith("]"):
                    loc_str += "."
                loc_str += str(loc)
        error_messages.append(f"{loc_str}: {error['msg']}")
    return error_messages
