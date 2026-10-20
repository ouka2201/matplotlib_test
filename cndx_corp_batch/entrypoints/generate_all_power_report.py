import argparse
import sys
from datetime import date
from typing import Any

from cndx_corp_batch.common.config import load_config
from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.logging import setup_logging
from cndx_corp_batch.domains.generate_all_power_report.jobs import (
    generate_all_power_report_job,
)


def main(argv: Any = None) -> int:
    """バッチ起動・処理27の終了。個別の対象で失敗してもジョブ側で後続の処理を続け、バッチ全体の例外が発生した場合のみ異常終了する。"""
    parser = argparse.ArgumentParser(description="電力見える化レポート一括作成")
    parser.add_argument(
        "--batch-date", type=date.fromisoformat, help="バッチ実行日（YYYY-MM-DD）"
    )
    args = parser.parse_args(argv)
    config = load_config()
    context: BatchContext = BatchContext(config)
    setup_logging(context.batch_id, context.batch_name)

    try:
        generate_all_power_report_job.GenerateAllPowerReportJob(
            context, batch_date=args.batch_date
        ).run()
        return 0
    except Exception:
        context.logger.exception("電力見える化レポート一括作成失敗しました。")
        return 1
    finally:
        context.close()


if __name__ == "__main__":
    sys.exit(main())
