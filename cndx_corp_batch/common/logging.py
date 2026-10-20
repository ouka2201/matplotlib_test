# common/logging.py
from datetime import datetime
import logging
import os
from logging.handlers import RotatingFileHandler


# def setup_logging(batch_id: str, batch_name: str):
#     log_level = logging.INFO

#     base_logger = logging.getLogger("batch")
#     base_logger.setLevel(log_level)
#     base_logger.propagate = False

#     if base_logger.handlers:
#         return  # 二重登録防止

#     today = datetime.now().strftime("%Y%m%d")

#     log_dir = f"/bd-fs-mnt/TenantShare/log/batch/{batch_name}/{today}"
#     os.makedirs(log_dir, exist_ok=True)

#     log_file = os.path.join(
#         log_dir,
#         f"batch_{batch_id}.log"
#     )

#     formatter = logging.Formatter(
#         "%(asctime)s %(levelname)s %(batch_name)s"
#         "run:%(batch_id)s job:%(job_name)s "
#         "%(filename)s:%(lineno)d %(funcName)s "
#         "%(message)s"
#     )

#     # stdout
#     stream = logging.StreamHandler()
#     stream.setFormatter(formatter)

#     # file
#     file_handler = RotatingFileHandler(
#         log_file,
#         maxBytes=20 * 1024 * 1024,
#         backupCount=10,
#         encoding="utf-8",
#     )
#     file_handler.setFormatter(formatter)

#     base_logger.addHandler(stream)
#     base_logger.addHandler(file_handler)

def setup_logging(batch_id: str, batch_name: str):
    log_level = logging.INFO

    base_logger = logging.getLogger("batch")
    base_logger.setLevel(log_level)
    base_logger.propagate = False

    if base_logger.handlers:
        return

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(batch_name)s "
        "run:%(batch_id)s job:%(job_name)s "
        "%(filename)s:%(lineno)d %(funcName)s "
        "%(message)s"
    )

    # stdout のみ
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    base_logger.addHandler(stream)


def attach_file_logger(batch_id: str, batch_name: str):
    logger = logging.getLogger("batch")

    today = datetime.now().strftime("%Y%m%d")
    log_dir = f"/bd-fs-mnt/TenantShare/log/batch/{batch_name}/{today}"
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"batch_{batch_id}.log")

    formatter = logger.handlers[0].formatter

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=20 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
