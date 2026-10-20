import argparse
import sys
from dataclasses import replace
from datetime import date

from cndx_corp_batch.common.config import load_config
from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.logging import setup_logging
from cndx_corp_batch.domains.sales_user_handover.jobs.sales_user_handover_job import (
    SalesUserHandoverJob,
)


def main(argv=None) -> int:
    """担当者引継ぎ実行バッチのエントリーポイント。"""
    parser = argparse.ArgumentParser(description="担当者引継ぎ実行")
    parser.add_argument("--batch-date", type=date.fromisoformat, help="実行日（YYYY-MM-DD）")
    args = parser.parse_args(argv)

    config = load_config()
    config = replace(config, batch_name=config.batch_name or "BLMMGMGHANDOVER")
    with BatchContext(config) as context:
        setup_logging(context.batch_id, context.batch_name)
        try:
            SalesUserHandoverJob(context, args.batch_date).run()
            return 0
        except Exception:
            context.logger.exception("担当者引継ぎ実行バッチに失敗しました。")
            return 1


if __name__ == "__main__":
    sys.exit(main())
