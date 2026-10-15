from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_engine = None
_Session = None


def init_db(db_url: str):
    global _engine, _Session
    _engine = create_engine(
        db_url,
        pool_size=2,
        max_overflow=1,
        connect_args={"options": "-csearch_path=db_corp,db_common"},
    )
    _Session = sessionmaker(
        bind=_engine,
        expire_on_commit=False,
    )


# def get_session():
#     if _Session is None:
#         raise RuntimeError("DB not initialized")
#     return _Session()


@contextmanager
def get_session():
    if _Session is None:
        raise RuntimeError("DB not initialized")

    session = _Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
