"""定期削除バッチのテストデータ作成Jobを起動する。"""

import argparse
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from cndx_corp_batch.common.config import load_config
from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.logging import setup_logging
from cndx_corp_batch.domains.periodic_delete.jobs.prepare_periodic_delete_data_job import (
    PreparePeriodicDeleteDataJob,
)


def main(argv=None) -> int:
    """引数に指定された基準日時でテストデータを作成する。

    Args:
        argv: コマンドライン引数。省略時は実行時の引数を使う。

    Returns:
        正常終了時は0、作成に失敗した場合は1。
    """
    parser = argparse.ArgumentParser(description="定期削除バッチのテストデータ作成")
    parser.add_argument("--batch-date", type=datetime.fromisoformat, required=True,
                        help="バッチに渡す実行日時 (YYYY-MM-DDTHH:MM:SS)")
    parser.add_argument("--output-dir", type=Path, default=Path("output/periodic_delete_seed"),
                        help="ZIPを作成する親ディレクトリ")
    args = parser.parse_args(argv)
    config = replace(load_config(), batch_name="BLMMRCRDELETE-SEED")
    with BatchContext(config) as context:
        setup_logging(context.batch_id, context.batch_name)
        try:
            manifest = PreparePeriodicDeleteDataJob(context, args.batch_date, args.output_dir).run()
            print(f"テストデータを作成しました: {manifest}")
            return 0
        except Exception:
            context.logger.exception("定期削除のテストデータ作成に失敗しました。")
            return 1


if __name__ == "__main__":
    sys.exit(main())
