from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def configure_database(database_url: str):
    global engine

    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    SessionLocal.configure(bind=engine)
    return engine


def init_db() -> None:
    import src.db.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
