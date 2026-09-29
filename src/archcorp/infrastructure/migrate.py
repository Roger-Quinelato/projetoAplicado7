"""Migrações de banco versionadas com Alembic (ADR-002).

A aplicação executa `upgrade_to_head` na inicialização. Um banco criado antes
das migrações, com as tabelas do protótipo e sem `alembic_version`, recebe o
carimbo da revisão base antes do upgrade para não recriar tabelas existentes.
"""
import logging
from importlib import import_module
from pathlib import Path

logging.getLogger("alembic.runtime.plugins").setLevel(logging.WARNING)

from alembic import command  # noqa: E402
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
    for module in MODEL_MODULES:
        import_module(module)
    return Base


def alembic_config(connection: Connection | None = None) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def upgrade_to_head(connection: Connection) -> None:
    config = alembic_config(connection)
    tables = set(inspect(connection).get_table_names())
    if "alembic_version" not in tables and "crm_customers" in tables:
        command.stamp(config, BASELINE_REVISION)
    command.upgrade(config, "head")
