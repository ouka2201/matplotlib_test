import os

from cndx_corp_batch.common.config import load_config
from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.logging import setup_logging
from cndx_corp_batch.domains.generate_all_power_report.jobs.generate_all_power_report_job import (
    GenerateAllPowerReportJob,
)
from cndx_corp_batch.domains.generate_all_power_report.rendering.sections.no0_contract import (
    draw_no0,
)
from cndx_corp_batch.domains.generate_all_power_report.services.chart_service import (
    ChartService,
)


def setup_local_env():
    """
    Local debug 用の環境変数設定
    ※ 本番では絶対に import しない
    """

    os.environ.setdefault("BATCH_NAME", "electric_vis")
    os.environ.setdefault("FLASK_ENV", "local")
    os.environ.setdefault("TZ", "Asia/Tokyo")

    # DATABASE_URL、TABLEAU_USERNAME、TABLEAU_PASSWORDは実行環境から受け取る。

    os.environ.setdefault("SQLALCHEMY_POOL_SIZE", "5")
    os.environ.setdefault("SQLALCHEMY_MAX_OVERFLOW", "10")
    os.environ.setdefault("SQLALCHEMY_POOL_TIMEOUT", "30")

    # --- Tableau ---
    os.environ.setdefault("TABLEAU_SERVER_URL", "http://10.191.33.99")
    os.environ.setdefault("TABLEAU_SITE_NAME", "")
    os.environ.setdefault("API_VERSION", "3.21")
    os.environ.setdefault(
        "ElectricPowerReportFormatName_value", "電力見える化_STEP3_maint"
    )
    os.environ.setdefault(
        "ElectricPowerDataSourceName_value_row",
        "electric_power_datasource_step3_row_postgre_maint",
    )
    os.environ.setdefault(
        "ElectricPowerDataSourceName_value_col",
        "electric_power_datasource_step3_col_postgre_maint",
    )

    # --- Optional ---
    os.environ.setdefault("HDFS_BASE_PATH", "/tmp/file")

    # os.environ.setdefault("DRY_RUN", "true")
    # os.environ.setdefault("BATCH_LOCK_ENABLED", "false")


def main():
    """
    ローカルデバッグ用エントリポイント
    """
    # ===== ローカル用環境変数 =====
    setup_local_env()

    setup_logging("electric_vis", "name")

    config = load_config()
    context = BatchContext(config)

    job = GenerateAllPowerReportJob(context)
    job.run()


if __name__ == "__main__":
    main()
