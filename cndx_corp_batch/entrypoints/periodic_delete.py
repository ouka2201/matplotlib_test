"""期限切れデータを物理削除する日次バッチ。"""

import argparse
import sys
from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo

from cndx_corp_batch.common.config import load_config
from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.logging import setup_logging
from cndx_corp_batch.domains.periodic_delete.jobs.periodic_delete_job import (
    PeriodicDeleteJob,
)


def main(argv=None) -> int:
    """定期削除バッチを起動する。

    Args:
        argv: コマンドライン引数。省略時は実行時の引数を使う。

    Returns:
        正常終了時は0、削除処理で例外が発生した場合は1。
    """
    parser = argparse.ArgumentParser(description="定期削除 (BLMMRCRDELETE)")
    parser.add_argument("--batch-date", type=datetime.fromisoformat, help="再実行日時 (YYYY-MM-DD[THH:MM:SS])")
    args = parser.parse_args(argv)
    config = replace(load_config(), batch_name="BLMMRCRDELETE")
    with BatchContext(config) as context:
        setup_logging(context.batch_id, context.batch_name)
        try:
            batch_at = args.batch_date or datetime.now(ZoneInfo(config.timezone)).replace(tzinfo=None)
            PeriodicDeleteJob(context, batch_at).run()
            return 0
        except Exception:
            context.logger.exception("定期削除バッチに失敗しました。")
            return 1


if __name__ == "__main__":
    sys.exit(main())
