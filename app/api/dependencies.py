from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.session import get_db_session


def db_session_dependency() -> Generator[Session, None, None]:
    yield from get_db_session()
