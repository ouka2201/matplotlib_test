import sys

from cndx_corp_batch.common.config import load_config
from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.logging import setup_logging
from cndx_corp_batch.domains.generate_all_power_report.jobs.generate_all_power_report_job import (
    GenerateAllPowerReportJob,
)


def main() -> int:
    config = load_config()
    context: BatchContext = BatchContext(config)
    setup_logging(context.batch_id, context.batch_name)

    try:
        GenerateAllPowerReportJob(context).run()
        return 0
    except Exception:
        context.logger.error("電力見える化レポート一括作成失敗しました。")
        return 1
    # finally:
    #     context.close()


if __name__ == "__main__":
    sys.exit(main())
