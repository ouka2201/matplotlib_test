import os
from dataclasses import dataclass

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

    cut_off_day: int
    report_month_offset_before: int
    report_month_offset_after: int

    # batch制御
    # dry_run: bool
    # batch_lock_enabled: bool

    # 固定値
    hdfs_base_path: str = "dtap://TenantStorage"


def load_config() -> BatchConfig:

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
            api_version=os.getenv("API_VERSION", "3.21"),
        ),
        cut_off_day=int(os.getenv("CUT_OFF_DAY", 15)),
        report_month_offset_before=int(os.getenv("REPORT_MONTH_OFFSET_BEFORE", 3)),
        report_month_offset_after=int(os.getenv("REPORT_MONTH_OFFSET_AFTER", 2)),
        # dry_run=env_bool("DRY_RUN", False),
        # batch_lock_enabled=env_bool("BATCH_LOCK_ENABLED", True),
        hdfs_base_path=os.getenv("HDFS_BASE_PATH"),
    )
