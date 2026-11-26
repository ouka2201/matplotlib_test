import argparse
import sys
from collections.abc import Sequence
from dataclasses import replace
from datetime import date

from cndx_corp_batch.common.config import load_config
from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.logging import setup_logging
from cndx_corp_batch.domains.user_power_report.jobs.user_power_report_Jobs import (
    UserPowerReportJob,
)


def main(argv: Sequence[str] | None = None) -> int:
    """担当者別zip化実行バッチのエントリーポイント。"""
    parser = argparse.ArgumentParser(description="担当者別zip化実行")
    parser.add_argument(
        "--batch-date",
        type=date.fromisoformat,
        default=None,
        help="実行日（YYYY-MM-DD）",
    )
    args = parser.parse_args(argv)

    config = load_config()
    config = replace(config, batch_name=config.batch_name or "BLMMRCRZIPCREATE")
    with BatchContext(config) as context:
        setup_logging(context.batch_id, context.batch_name)
        try:
            UserPowerReportJob(context, args.batch_date).run()
            return 0
        except Exception as e:
            context.logger.exception(f"担当者別zip化バッチに失敗しました。{e}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
