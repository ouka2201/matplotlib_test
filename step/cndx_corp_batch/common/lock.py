# app/lock.py
import logging
from common.db import get_session

log = logging.getLogger(__name__)


def acquire_lock(lock_key: int) -> bool:
    session = get_session()
    try:
        locked = session.execute(
            "SELECT pg_try_advisory_lock(:key)",
            {"key": lock_key},
        ).scalar()
        session.commit()
        return locked
    finally:
        session.close()


def release_lock(lock_key: int):
    session = get_session()
    try:
        session.execute(
            "SELECT pg_advisory_unlock(:key)",
            {"key": lock_key},
        )
        session.commit()
    finally:
        session.close()
