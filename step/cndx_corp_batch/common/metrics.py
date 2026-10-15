# app/metrics.py
import logging
import time

log = logging.getLogger(__name__)


class Metric:
    def __init__(self, name: str):
        self.name = name

    def __enter__(self):
        self.start = time.time()
        log.info("metric start: %s", self.name)
        return self

    def __exit__(self, exc_type, exc, tb):
        elapsed = time.time() - self.start
        log.info("metric end: %s elapsed=%.2fs", self.name, elapsed)
