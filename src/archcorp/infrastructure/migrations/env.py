from alembic import context
from archcorp.config import settings
from archcorp.infrastructure.db import engine
from archcorp.infrastructure.migrate import load_models

target_metadata = load_models().metadata


def run(connection) -> None:
    """Executa as migrações na conexão informada, em modo batch no SQLite."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=connection.dialect.name == "sqlite",
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


connection = context.config.attributes.get("connection")
if context.is_offline_mode():
    context.configure(
        url=context.config.get_main_option("sqlalchemy.url") or settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()
elif connection is not None:
    run(connection)
else:
    with engine.connect() as standalone:
        run(standalone)
        standalone.commit()
