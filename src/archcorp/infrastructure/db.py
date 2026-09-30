from collections.abc import Generator
from typing import TypeVar

from sqlalchemy import Connection, create_engine, func, select, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from archcorp.config import settings
from archcorp.exceptions import NotFoundError


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


ModelT = TypeVar("ModelT", bound=Base)


def get_or_raise(session: Session, model: type[ModelT], entity_id: str, message: str) -> ModelT:
    entity = session.get(model, entity_id)
    if entity is None:
        raise NotFoundError(message)
    return entity


def count_rows(session: Session, model: type[Base]) -> int:
    return session.scalar(select(func.count()).select_from(model))


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
