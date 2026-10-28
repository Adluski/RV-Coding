from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from . import config


def _normalize(url: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


_url = _normalize(config.DATABASE_URL)
if _url.startswith("sqlite"):
    engine = create_engine(_url, connect_args={"check_same_thread": False})
else:
    # NullPool: serverless functions should not hold idle connections.
    engine = create_engine(_url, poolclass=NullPool, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Columns added after the first release. create_all() does not alter existing tables, so add them here.
_NEW_COLUMNS = [
    ("problems", "difficulty", "VARCHAR(8) DEFAULT 'Easy'"),
    ("problems", "hint", "TEXT"),
    ("problems", "time_complexity", "VARCHAR(64)"),
    ("problems", "space_complexity", "VARCHAR(64)"),
    ("submissions", "claimed_time", "VARCHAR(64)"),
    ("submissions", "claimed_space", "VARCHAR(64)"),
    ("submissions", "test_results", "TEXT"),
]


def init_db():
    """Create tables and add missing columns. Safe to run concurrently (two serverless cold starts may race)."""
    from sqlalchemy import inspect, text
    from sqlalchemy.exc import DBAPIError

    try:
        Base.metadata.create_all(engine)
    except DBAPIError:
        Base.metadata.create_all(engine)  # another instance created a table between check and create
    is_pg = engine.dialect.name == "postgresql"
    insp = inspect(engine)
    for table, col, ddl in _NEW_COLUMNS:
        if col in {c["name"] for c in insp.get_columns(table)}:
            continue
        stmt = f"ALTER TABLE {table} ADD COLUMN {'IF NOT EXISTS ' if is_pg else ''}{col} {ddl}"
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
        except DBAPIError:
            # Lost a race with another instance; fine if the column now exists.
            if col not in {c["name"] for c in inspect(engine).get_columns(table)}:
                raise
