from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from cndx_corp_batch.domains.periodic_delete.jobs import periodic_delete_job as job


def test_cutoffs_and_table_order():
    """各テーブルの境界値と削除対象を確認する。"""
    context = SimpleNamespace(logger=MagicMock())
    with patch.object(job, "_delete_zip_rows") as zip_rows, patch.object(job, "_delete_old_rows") as old_rows:
        instance = object.__new__(job.PeriodicDeleteJob)
        instance.context = context
        instance.logger = context.logger
        instance.batch_at = datetime(2026, 11, 17, 2)
        instance.execute()

    assert [call.args[1] for call in zip_rows.call_args_list] == [
        "t_user_power_report_mng_info", "t_co2_summary_report_mng_info"
    ]
    assert zip_rows.call_args_list[0].args[3] == "202411"
    assert zip_rows.call_args_list[1].args[3] == datetime(2026, 11, 16, 2)
    assert [(call.args[1], call.args[3]) for call in old_rows.call_args_list] == [
        ("t_power_report_mng_info", "202411"),
        ("t_ep_electricity_data_30min", "20211117"),
        ("t_30min_import_mng", "202111"),
        ("t_historical_arve_customer_info", "202605"),
    ]


def test_zip_file_must_be_removed_before_management_row(tmp_path):
    """ZIPファイルを削除してから管理行を削除することを確認する。

    Args:
        tmp_path: テスト用のZIPファイルを置く一時ディレクトリ。
    """
    target = tmp_path / "report.zip"
    target.write_bytes(b"zip")
    row = {"file_id": 7, "file_path": str(target)}
    session = MagicMock()
    # First SELECT returns one row; the next page is empty.
    selected = iter([[row], []])

    def execute(sql, params):
        """DB応答を模擬し、管理行の削除順を確認する。

        Args:
            sql: 実行するSQL。
            params: SQLに渡すパラメータ。

        Returns:
            検索結果または削除件数を持つ模擬結果。
        """
        if str(sql).startswith("SELECT"):
            return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: next(selected)))
        assert not target.exists()
        return SimpleNamespace(rowcount=1)

    session.execute.side_effect = execute
    manager = MagicMock()
    manager.__enter__.return_value = session
    with patch.object(job, "get_session", return_value=manager):
        job._delete_zip_rows(SimpleNamespace(logger=MagicMock()),
                             "t_user_power_report_mng_info", ("file_id",), "202411", "target_year_month")
    assert not target.exists()


def test_invalid_file_path_does_not_delete_management_row():
    """相対パスを削除対象として受け付けないことを確認する。"""
    with pytest.raises(ValueError):
        job._delete_file("../other/report.zip")
