import re

import numpy as np
import pandas as pd

from cndx_corp_back.common.db_base_handler import BaseRepository


def safe(val):
    return val or ""


def safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def convert_year_month(s: str) -> str:
    """_summary_

    Args:
        s (str): 年月をyyyyMMに変換

    Returns:
        str: yyyyMM
    """
    return re.sub(
        r"(\d{4})年(\d{1,2})月", lambda m: f"{m.group(1)}{int(m.group(2)):02}", s
    )


def df_to_repo(
    df: pd.DataFrame, repo: BaseRepository, column_map: dict[str, str] | None = None
):
    for row in df.to_dict(orient="records"):
        if column_map:
            row = {entity_key: row[df_key] for df_key, entity_key in column_map.items()}
        repo.insert(row)


def set_target_entity(target_entity, val_dict: dict):
    for key, value in val_dict.items():
        setattr(target_entity, key, value)


def split_code_name(value: str):
    code, name = value.split(":")
    return code, name


def normalize_blank(x):
    # None / NaN → None
    if x is None:
        return None
    if isinstance(x, float) and np.isnan(x):
        return None

    # 文字列の場合：空白系は None
    if isinstance(x, str):
        if x.strip() == "":
            return None
    return x


def nan_to_none(value):
    return None if pd.isna(value) else value


def is_numeric(x):
    try:
        float(x)
        return True
    except (ValueError, TypeError):
        return False
