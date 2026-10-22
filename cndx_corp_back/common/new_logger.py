# common/new_logger.py

import logging


class NewLogger:
    """
    標準 logging.Logger に準拠したラッパー。
    Flask の current_app.logger を拡張して、 *args に対応。
    """

    def __init__(self, base_logger=None):
        self.logger = base_logger or logging.getLogger(__name__)

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)
