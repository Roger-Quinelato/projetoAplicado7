from collections.abc import Generator
from typing import TypeVar

from sqlalchemy import Connection, Engine, create_engine, event, func, select
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from archcorp.config import settings
from archcorp.exceptions import NotFoundError


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


ModelT = TypeVar("ModelT", bound=Base)


def get_or_raise(session: Session, model: type[ModelT], entity_id: str, message: str) -> ModelT:
    """Devolve a entidade pela chave primária ou levanta NotFoundError com a mensagem informada."""
    entity = session.get(model, entity_id)
    if entity is None:
        raise NotFoundError(message)
    return entity


def count_rows(session: Session, model: type[Base]) -> int:
    """Conta as linhas da tabela do modelo."""
    return session.scalar(select(func.count()).select_from(model))


def get_session() -> Generator[Session, None, None]:
    """Dependência FastAPI que abre uma sessão por requisição e a fecha ao final."""
    with SessionLocal() as session:
        yield session
