from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker[Session]:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def new_db_session() -> Session:
    return _session_factory()()


def get_db_session() -> Generator[Session, None, None]:
    session = new_db_session()
    try:
        yield session
    finally:
        session.close()