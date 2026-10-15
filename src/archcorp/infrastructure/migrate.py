"""Migrações de banco versionadas com Alembic (ADR-002).

A aplicação executa `upgrade_to_head` na inicialização. Um banco com as tabelas
do protótipo e sem `alembic_version` foi criado por `create_all`: se o esquema já
coincide com os modelos, recebe o carimbo de `head`; caso contrário, recebe o da
revisão base e as migrações seguintes são aplicadas.
"""
import logging
from importlib import import_module
from pathlib import Path

logging.getLogger("alembic.runtime.plugins").setLevel(logging.WARNING)

from alembic import command  # noqa: E402
from alembic.autogenerate import compare_metadata  # noqa: E402
from alembic.migration import MigrationContext  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import Connection, inspect  # noqa: E402

from archcorp.infrastructure.db import Base  # noqa: E402

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
BASELINE_REVISION = "0001_baseline"
MODEL_MODULES = (
    "archcorp.crm.models",
    "archcorp.contracts.models",
    "archcorp.finance.models",
    "archcorp.support.models",
    "archcorp.workflow.models",
    "archcorp.integration.models",
)


def load_models() -> type[Base]:
    """Importa os modelos de todos os módulos para preencher os metadados."""
    for module in MODEL_MODULES:
        import_module(module)
    return Base


def alembic_config(connection: Connection | None = None) -> Config:
    """Monta a configuração do Alembic, opcionalmente com uma conexão já aberta."""
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def upgrade_to_head(connection: Connection) -> None:
    """Carimba bancos criados por create_all e aplica as migrações até `head`."""
    config = alembic_config(connection)
    tables = set(inspect(connection).get_table_names())
    if "alembic_version" not in tables and "crm_customers" in tables:
        drift = compare_metadata(MigrationContext.configure(connection), load_models().metadata)
        command.stamp(config, "head" if not drift else BASELINE_REVISION)
    command.upgrade(config, "head")
