"""電力見える化レポート一括作成ジョブのDB連携部分を検証する。"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from cndx_corp_batch.common.logger import BatchLogger
from cndx_corp_batch.domains.generate_all_power_report.jobs.get_power_report_target import (
    GetPowerReportTarget,
)
from cndx_corp_batch.domains.generate_all_power_report.jobs.register_unregistered_report_target_job import (
    RegisterUnregisteredReportTargetJob,
)
from cndx_corp_batch.domains.generate_all_power_report.services.report_job_source import (
    customer_column_mapping,
)


def context():
    return SimpleNamespace(
        batch_id="test", batch_name="electric_vis",
        logger=BatchLogger("test", "electric_vis"),
        config=SimpleNamespace(),
    )


def db_session(session):
    class Context:
        def __enter__(self):
            return session

        def __exit__(self, *args):
            return False

    return Context()


def test_register_job_executes_insert_sql_once():
    session = Mock()
    with patch(
        "cndx_corp_batch.domains.generate_all_power_report.jobs.register_unregistered_report_target_job.get_session",
        return_value=db_session(session),
    ), patch(
        "cndx_corp_batch.domains.generate_all_power_report.jobs.register_unregistered_report_target_job.load_sql_file",
        return_value="INSERT_SQL",
    ):
        RegisterUnregisteredReportTargetJob(context(), date(2026, 6, 1)).run()
    session.execute.assert_called_once()
    assert "INSERT_SQL" in str(session.execute.call_args.args[0])
    assert session.execute.call_args.args[1]["report_ym"] == "202606"


def test_get_target_job_returns_only_the_db_result():
    session = Mock()
    expected = [("0001", "C001", True)]
    session.execute.return_value.all.return_value = expected
    with patch(
        "cndx_corp_batch.domains.generate_all_power_report.jobs.get_power_report_target.get_session",
        return_value=db_session(session),
    ), patch(
        "cndx_corp_batch.domains.generate_all_power_report.jobs.get_power_report_target.load_sql_file",
        return_value="SELECT_SQL",
    ):
        result = GetPowerReportTarget(context(), date(2026, 6, 1)).run()
    assert result == expected
    assert session.execute.call_args.args[1] == {"report_ym": "202606"}


def test_customer_column_mapping_uses_explicit_customer_name_column():
    """設定で名義列を指定した場合は、既定列と指定値を組み合わせる。"""
    table = SimpleNamespace(c=[])

    mapping = customer_column_mapping(
        table,
        {"customer_columns": {"customer_name": "CUSTOMER_NAME"}},
    )

    assert mapping == {
        "customer_name": "CUSTOMER_NAME",
        "customer_number": "cmn_oldcustomernum__c",
        "address": "cmn_demandlocationaddress__c",
    }


def test_customer_column_mapping_infers_the_only_name_column():
    """名義候補が1列だけの場合は、その物理列名を採用する。"""
    table = SimpleNamespace(
        c=[
            SimpleNamespace(name="CMN_DEMANDLOCATIONFULLNAME__C"),
            SimpleNamespace(name="OTHER_COLUMN"),
        ]
    )

    mapping = customer_column_mapping(table, {})

    assert mapping["customer_name"] == "CMN_DEMANDLOCATIONFULLNAME__C"


def test_customer_column_mapping_rejects_missing_or_ambiguous_name_column():
    """名義候補を一意に特定できない場合は設定エラーにする。"""
    for columns in ([], [SimpleNamespace(name="CMN_DEMANDLOCATIONFULLNAME_A"),
                        SimpleNamespace(name="CMN_DEMANDLOCATIONFULLNAME_B")]):
        with pytest.raises(ValueError, match="customer_columns.customer_name"):
            customer_column_mapping(SimpleNamespace(c=columns), {})
