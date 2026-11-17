"""バッチ設計書_定期削除の物理削除処理。"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import os
from pathlib import Path

from sqlalchemy import text

from cndx_corp_batch.common.db import get_session
from cndx_corp_batch.jobs.base import BaseJob


PAGE_SIZE = 1000
DELETE_SIZE = 10000


def months_before(value: datetime, months: int) -> datetime:
    """指定した月数だけ日時を戻す。

    戻した先に同じ日がない場合は、PostgreSQLの月減算と同じく月末を使う。

    Args:
        value: 基準となる日時。
        months: 戻す月数。

    Returns:
        月数を戻した日時。
    """
    import calendar

    year, month = divmod(value.year * 12 + value.month - 1 - months, 12)
    month += 1
    return value.replace(year=year, month=month, day=min(value.day, calendar.monthrange(year, month)[1]))


def _delete_file(path: str | None) -> None:
    """絶対パスで指定されたZIPファイルを削除する。

    Args:
        path: 削除するファイルのパス。空の場合は何もしない。

    Raises:
        ValueError: パスが絶対パスでない、またはZIPファイルを指していない場合。
    """
    if not path:
        return
    target = Path(path)
    if target.suffix.lower() != ".zip" or not target.is_absolute():
        raise ValueError(f"削除対象のZIPパスが不正です: {path}")
    target.unlink(missing_ok=True)


def _delete_zip_rows(context, table: str, key: tuple[str, ...], cutoff: datetime | str, cutoff_column: str) -> None:
    """期限切れのZIPファイルと管理行を削除する。

    ファイルを先に削除し、再実行時には削除済みのファイルも許容する。

    Args:
        context: ログ出力に使うバッチコンテキスト。
        table: 管理テーブルの物理名。
        key: 管理行を識別する列名。
        cutoff: 削除対象を判定する境界日時または対象年月。
        cutoff_column: 境界値と比較する列名。
    """
    def delete_one(row):
        """対象のファイルを削除してから、対応する管理行を削除する。

        Args:
            row: 主キー列とファイルパスを含む管理行。
        """
        values = tuple(row[column] for column in key)
        _delete_file(row["file_path"])
        where = " AND ".join(f"{column} = :key_{i}" for i, column in enumerate(key))
        params = {"cutoff": cutoff, **{f"key_{i}": value for i, value in enumerate(values)}}
        with get_session() as session:
            session.execute(text(f"DELETE FROM db_corp.{table} WHERE {where} "
                                 f"AND {cutoff_column} < :cutoff"), params)

    cursor = None
    while True:
        order = ", ".join(key)
        after = "" if cursor is None else "AND (" + order + ") > (" + ", ".join(f":key_{i}" for i in range(len(key))) + ")"
        params = {"cutoff": cutoff, "limit": PAGE_SIZE}
        if cursor is not None:
            params.update({f"key_{i}": value for i, value in enumerate(cursor)})
        query = text(f"SELECT {order}, file_path FROM db_corp.{table} "
                     f"WHERE {cutoff_column} < :cutoff {after} ORDER BY {order} LIMIT :limit")
        with get_session() as session:
            rows = session.execute(query, params).mappings().all()
        if not rows:
            break
        cursor = tuple(rows[-1][column] for column in key)
        with ThreadPoolExecutor(max_workers=os.cpu_count() or 1) as pool:
            list(pool.map(delete_one, rows))
        context.logger.info("%s: %d件処理", table, len(rows))


def _delete_old_rows(context, table: str, column: str, cutoff: str) -> None:
    """期限切れの管理行を一定件数ずつ削除する。

    Args:
        context: ログ出力に使うバッチコンテキスト。
        table: 削除対象テーブルの物理名。
        column: 境界値と比較する列名。
        cutoff: 削除対象を判定する年月または年月日。
    """
    # 1トランザクションを制限し、数百万件の対象でもロックとWALの肥大化を抑える。
    query = text(f"DELETE FROM db_corp.{table} WHERE ctid IN ("
                 f"SELECT ctid FROM db_corp.{table} WHERE {column} < :cutoff LIMIT :limit)")
    total = 0
    while True:
        with get_session() as session:
            count = session.execute(query, {"cutoff": cutoff, "limit": DELETE_SIZE}).rowcount
        total += count
        if count < DELETE_SIZE:
            break
    context.logger.info("%s: %d件削除", table, total)


class PeriodicDeleteJob(BaseJob):
    """保持期間を過ぎたZIPファイルとDB行を物理削除する。"""

    def __init__(self, context, batch_at: datetime):
        """削除基準となる実行日時を設定する。

        Args:
            context: DB接続とログ出力に使うバッチコンテキスト。
            batch_at: 保持期間を計算する基準日時。

        Raises:
            TypeError: 基準日時がdatetimeでない場合。
        """
        super().__init__(context)
        if not isinstance(batch_at, datetime):
            raise TypeError("batch_at は datetime を指定してください")
        self.batch_at = batch_at

    def execute(self) -> None:
        """設計書の処理順で期限切れのデータを物理削除する。

        境界日時または境界年月と同じ値のデータは削除しない。
        """
        two_years = months_before(self.batch_at, 24)
        five_years = months_before(self.batch_at, 60)
        six_months = months_before(self.batch_at, 6)

        # 概要定義の保持期間は2年。詳細定義No.2の「5年」は概要と不一致。
        _delete_zip_rows(self.context, "t_user_power_report_mng_info", ("file_id",),
                         two_years.strftime("%Y%m"), "target_year_month")
        _delete_old_rows(self.context, "t_power_report_mng_info", "target_year_month", two_years.strftime("%Y%m"))
        _delete_old_rows(self.context, "t_ep_electricity_data_30min", "t01_get_ymd", five_years.strftime("%Y%m%d"))
        _delete_old_rows(self.context, "t_30min_import_mng", "target_year_month", five_years.strftime("%Y%m"))
        # テーブル定義の主キーは creation_id + org_id（詳細定義のファイルID列は存在しない）。
        _delete_zip_rows(self.context, "t_co2_summary_report_mng_info", ("creation_id", "org_id"),
                         self.batch_at - timedelta(hours=24), "file_created_at")
        _delete_old_rows(self.context, "t_historical_arve_customer_info", "acquisition_year_month", six_months.strftime("%Y%m"))
