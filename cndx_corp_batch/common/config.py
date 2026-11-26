import os
from dataclasses import dataclass

from cndx_corp_batch.common.api_client import ApiConfig
from cndx_corp_batch.common.tableau import TableauConfig


@dataclass(frozen=True)
class BatchConfig:
    batch_name: str
    # 基本
    env: str
    timezone: str
    db_url: str

    # SQLAlchemy
    sqlalchemy_pool_size: int
    sqlalchemy_max_overflow: int
    sqlalchemy_pool_timeout: int

    # Tableau
    # api_version: str = "3.21"
    # tableau_server_url: str
    # tableau_username: str | None
    # tableau_password: str | None
    tableau: TableauConfig

    report_output_dir: str

    cut_off_day: int
    report_month_offset_before: int
    report_month_offset_after: int

    # TDV連携
    arve: ApiConfig
    ep_regular_data: ApiConfig
    ep_newcommer_data: ApiConfig
    ep_contract_power: ApiConfig

    # 見える化レポート一括作成
    cut_off_day: int
    report_month_offset_before: int
    report_month_offset_after: int
    arve_cust_month_offset_before: int
    arve_cust_month_offset_after: int

    regular_chunk_size: int

    new_chunk_size: int

    api_service_time_hour_from: int
    api_service_time_minute_from: int
    api_service_time_hour_to: int
    api_service_time_minute_to: int

    # 担当者別ZIPファイル作成
    final_meter_reading_date: int
    offset_month_1: int
    offset_month_2: int
    user_power_report_file_path: str

    # batch制御
    # dry_run: bool
    # batch_lock_enabled: bool

    # 固定値
    hdfs_base_path: str = "dtap://TenantStorage"


def load_config() -> BatchConfig:

    from cndx_corp_batch.common.utils import env_bool

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is required")

    return BatchConfig(
        batch_name=os.getenv("BATCH_NAME"),
        env=os.getenv("FLASK_ENV", "maint"),
        timezone=os.getenv("TZ", "Asia/Tokyo"),
        db_url=db_url,
        sqlalchemy_pool_size=int(os.getenv("SQLALCHEMY_POOL_SIZE", 10)),
        sqlalchemy_max_overflow=int(os.getenv("SQLALCHEMY_MAX_OVERFLOW", 20)),
        sqlalchemy_pool_timeout=int(os.getenv("SQLALCHEMY_POOL_TIMEOUT", 30)),
        tableau=TableauConfig(
            server_url=os.getenv("TABLEAU_SERVER_URL", "http://10.191.33.99"),
            username=os.getenv("TABLEAU_USERNAME"),
            password=os.getenv("TABLEAU_PASSWORD"),
            site_name=os.getenv("TABLEAU_SITE_NAME", ""),
            api_version=os.getenv("API_VERSION"),
        ),
        report_output_dir=os.getenv("REPORT_OUTPUT_DIR"),
        cut_off_day=int(os.getenv("CUT_OFF_DAY", 15)),
        report_month_offset_before=int(os.getenv("REPORT_MONTH_OFFSET_BEFORE", 3)),
        report_month_offset_after=int(os.getenv("REPORT_MONTH_OFFSET_AFTER", 2)),
        # 担当者別ZIPファイル作成
        final_meter_reading_date=os.getenv("FINAL_METER_READING_DATE", 14),
        offset_month_1=os.getenv("OFFSET_MONTH_1", 3),
        offset_month_2=os.getenv("OFFSET_MONTH_2", 2),
        user_power_report_file_path=os.getenv("USER_POWER_REPORT_FILE_PATH", ""),
        arve=ApiConfig(
            server_url=os.getenv("TDV_SERVER_URL"),
            endpoint=os.getenv("ARVE_ENDPOINT"),
            username=os.getenv("TDV_USERNAME"),
            password=os.getenv("TDV_PASSWORD"),
            retry_count=int(os.getenv("ARVE_RETRY_COUNT", 0)),
            retry_interval=int(os.getenv("ARVE_RETRY_INTERVAL", 120)),
            verify=env_bool(os.getenv("ARVE_VERIFY", "True")),
            timeout=int(os.getenv("ARVE_TIMEOUT", 120)),
        ),
        ep_regular_data=ApiConfig(
            server_url=os.getenv("TDV_SERVER_URL"),
            endpoint=os.getenv("EP_REGULAR_ENDPOINT"),
            username=os.getenv("TDV_USERNAME"),
            password=os.getenv("TDV_PASSWORD"),
            retry_count=int(os.getenv("EP_RETRY_COUNT", 0)),
            retry_interval=int(os.getenv("EP_RETRY_INTERVAL", 120)),
            verify=env_bool(os.getenv("EP_VERIFY", "True")),
            timeout=int(os.getenv("EP_TIMEOUT", 120)),
        ),
        ep_newcommer_data=ApiConfig(
            server_url=os.getenv("TDV_SERVER_URL"),
            endpoint=os.getenv("EP_NEWCOMMER_ENDPOINT"),
            username=os.getenv("TDV_USERNAME"),
            password=os.getenv("TDV_PASSWORD"),
            retry_count=int(os.getenv("EP_RETRY_COUNT", 0)),
            retry_interval=int(os.getenv("EP_RETRY_INTERVAL", 120)),
            verify=env_bool(os.getenv("EP_VERIFY", "True")),
            timeout=int(os.getenv("EP_TIMEOUT", 120)),
        ),
        ep_contract_power=ApiConfig(
            server_url=os.getenv("TDV_SERVER_URL"),
            endpoint=os.getenv("EP_CONTRACTED_POWER_ENDPOINT"),
            username=os.getenv("TDV_USERNAME"),
            password=os.getenv("TDV_PASSWORD"),
            retry_count=int(os.getenv("EP_RETRY_COUNT", 0)),
            retry_interval=int(os.getenv("EP_RETRY_INTERVAL", 120)),
            verify=env_bool(os.getenv("EP_VERIFY", "True")),
            timeout=int(os.getenv("EP_TIMEOUT", 120)),
        ),
        arve_cust_month_offset_before=os.getenv("ARVE_CUST_MONTH_OFFSET_BEFORE", 2),
        arve_cust_month_offset_after=os.getenv("ARVE_CUST_MONTH_OFFSET_AFTER", 1),
        regular_chunk_size=os.getenv("REGILAR_CHUNK_SIZE", 100),
        new_chunk_size=os.getenv("NEW_CHUNK_SIZE", 100),
        api_service_time_hour_from=int(os.getenv("API_SERVICE_TIME_HOUR_FROM", 12)),
        api_service_time_minute_from=int(os.getenv("API_SERVICE_TIME_MINUTE_FROM", 0)),
        api_service_time_hour_to=int(os.getenv("API_SERVICE_TIME_HOUR_TO", 22)),
        api_service_time_minute_to=int(os.getenv("API_SERVICE_TIME_MINUTE_TO", 0)),
        # dry_run=env_bool("DRY_RUN", False),
        # batch_lock_enabled=env_bool("BATCH_LOCK_ENABLED", True),
        hdfs_base_path=os.getenv("HDFS_BASE_PATH"),
    )
