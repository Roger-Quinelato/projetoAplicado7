from collections.abc import Generator

from sqlalchemy import Connection, Engine, create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from archcorp.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)


def use_explicit_sqlite_transactions(target: Engine) -> None:
    """Faz o pysqlite abrir a transação no BEGIN do SQLAlchemy.

    Sem isso o driver adia o BEGIN até o primeiro DML; um SAVEPOINT aberto
    depois de apenas SELECTs vira a transação externa e o RELEASE confirma os
    dados. Receita documentada pelo SQLAlchemy para o dialeto pysqlite.
    """
    if target.dialect.name != "sqlite":
        return

    @event.listens_for(target, "connect")
    def _disable_driver_transactions(dbapi_connection, _record) -> None:
        dbapi_connection.isolation_level = None

    @event.listens_for(target, "begin")
    def _begin(connection: Connection) -> None:
        connection.exec_driver_sql("BEGIN")


use_explicit_sqlite_transactions(engine)
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
