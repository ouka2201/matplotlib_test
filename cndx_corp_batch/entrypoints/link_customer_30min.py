import argparse
from dataclasses import replace
from datetime import date
import sys

from cndx_corp_batch.common.config import load_config
from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.logging import setup_logging
from cndx_corp_batch.domains.link_customer_30min.jobs.link_customer_30min_job import (
    LinkCustomer30MinJob,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="顧客情報と30分値データの連携")
    parser.add_argument("--batch-date", type=date.fromisoformat, help="実行日（YYYY-MM-DD）")
    parser.add_argument("--batch-size", type=int, default=1000, help="1回の取得件数（既定：1000）")
    args = parser.parse_args(argv)
    if args.batch_size <= 0:
        parser.error("--batch-size は1以上を指定してください。")
    config = load_config()
    config = replace(config, batch_name=config.batch_name or "BLMMVMVBUILDING")
    with BatchContext(config) as context:
        setup_logging(context.batch_id, context.batch_name)
        try:
            LinkCustomer30MinJob(context, args.batch_date, args.batch_size).run()
            return 0
        except Exception:
            context.logger.exception("顧客情報と30分値データの連携に失敗しました。")
            return 1


if __name__ == "__main__":
    sys.exit(main())
