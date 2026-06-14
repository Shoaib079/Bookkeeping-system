from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

from paths import DATABASE_URL

Base = declarative_base()

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)


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