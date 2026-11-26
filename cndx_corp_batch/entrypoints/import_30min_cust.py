import argparse
import sys
from datetime import date

from cndx_corp_batch.common.config import load_config
from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.logging import setup_logging
from cndx_corp_batch.domains.import_30min_cust.jobs.import_30min_cust_Job import (
    Import30minCustJob,
)


def main(argv=None) -> int:
    """30分値・顧客情報取込バッチの起動ポイント。個別の例外はジョブ側で制御し全体の例外のみ異常終了とする"""
    parser = argparse.ArgumentParser(description="30分値・顧客情報取込")
    parser.add_argument(
        "--batch-date", type=date.fromisoformat, help="バッチ実行日（YYYY-MM-DD）"
    )
    args = parser.parse_args(argv)
    config = load_config()
    context: BatchContext = BatchContext(config)
    setup_logging(context.batch_id, context.batch_name)

    try:
        Import30minCustJob(context, batch_date=args.batch_date).run()
        return 0
    except Exception:
        context.logger.error("30分値・顧客情報取込に失敗しました。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
