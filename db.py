from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

from paths import get_database_url

Base = declarative_base()


def _build_engine():
    url = get_database_url()
    kwargs: dict = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_pre_ping"] = True
    return create_engine(url, **kwargs)


engine = _build_engine()


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key enforcement on every new SQLite connection.

    SQLite disables FK checks by default. Without this, inserting a
    JournalEntryLine with a non-existent account_id would silently succeed
    instead of raising an IntegrityError.

    P3.2-B: dialect-guarded so a future PostgreSQL engine does not receive PRAGMA.
    """
    if engine.dialect.name != "sqlite":
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)
