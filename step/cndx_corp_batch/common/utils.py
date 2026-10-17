import getpass
import os
import sys
from datetime import datetime

from matplotlib.dates import relativedelta


def env_bool(
    key: str,
    default: bool = False,
    *,
    required: bool = False,
) -> bool:
    """
    環境変数を bool として取得する。

    True と判定する値:
        "1", "true", "t", "yes", "y", "on"

    False と判定する値:
        "0", "false", "f", "no", "n", "off"

    Args:
        key: 環境変数名
        default: 未設定時のデフォルト値
        required: True の場合、環境変数が未設定なら例外を送出する

    Raises:
        RuntimeError: required=True かつ未設定
        ValueError: bool として解釈できない値
    """
    raw = os.getenv(key)

    if raw is None:
        if required:
            raise RuntimeError(f"Environment variable '{key}' is required")
        return default

    value = raw.strip().lower()

    if value in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "f", "no", "n", "off"}:
        return False

    raise ValueError(f"Invalid boolean value for env '{key}': '{raw}'")


def get_target_period(start_month: str) -> str:
    """
    start_month: 'yyyyMM'
    return: 'yyyyMM-yyyyMM' (12ヶ月間)
    """
    start_date = datetime.strptime(start_month, "%Y%m")

    # 11ヶ月足す（開始月含めて12ヶ月にするため）
    end_date = start_date + relativedelta(months=11)

    return f"{start_date.strftime('%Y%m')}-{end_date.strftime('%Y%m')}"


def get_sysuser():
    """システムユーザ取得
    return:システムユーザー名
    """
    return getpass.getuser()


def cpu_workers():
    """現在のプロセスが利用できる論理CPU数を求める。

    Returns:
        int: CPU数。未取得なら1。WindowsはProcessPoolExecutorの上限61まで。
    """
    # Pythonのバージョンに応じて、利用できる論理CPU数を取得する。
    # コンテナー等で実際の上限と異なる場合は--workersで明示的に調整する。
    if hasattr(os, "process_cpu_count"):
        count = os.process_cpu_count() or 1
    elif hasattr(os, "sched_getaffinity"):
        count = len(os.sched_getaffinity(0)) or 1
    else:
        count = os.cpu_count() or 1
    return min(count, 61) if sys.platform == "win32" else count
