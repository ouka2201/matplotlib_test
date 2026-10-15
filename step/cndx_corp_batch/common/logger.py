import logging


class BatchLogger(logging.LoggerAdapter):
    """
    バッチ処理用ロガー
    """

    def __init__(self, batch_id: str, batch_name: str):
        base_logger = logging.getLogger("batch")
        super().__init__(
            base_logger,
            {
                "batch_id": batch_id,
                "batch_name": batch_name,
                "job_name": "-",
            },
        )
