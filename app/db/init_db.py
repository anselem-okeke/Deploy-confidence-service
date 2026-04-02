from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.db import models  # noqa: F401


def check_database_connection() -> bool:
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


def create_all_tables() -> None:
    Base.metadata.create_all(bind=engine)