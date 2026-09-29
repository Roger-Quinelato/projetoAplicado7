from collections.abc import Generator

from sqlalchemy import Connection, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from archcorp.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def protect_public_demo_tables(connection: Connection) -> None:
    """Deny Supabase Data API roles access to tables owned by the demo app."""
    if not settings.public_demo or engine.dialect.name != "postgresql":
        return

    roles = set(connection.execute(text("SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')")).scalars())
    preparer = engine.dialect.identifier_preparer
    for table in Base.metadata.sorted_tables:
        identifier = preparer.format_table(table)
        connection.exec_driver_sql(f"ALTER TABLE {identifier} ENABLE ROW LEVEL SECURITY")
        for role in sorted(roles):
            connection.exec_driver_sql(f"REVOKE ALL PRIVILEGES ON TABLE {identifier} FROM {preparer.quote(role)}")


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
