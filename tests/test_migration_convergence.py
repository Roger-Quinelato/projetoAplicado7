"""Convergência sem renumerar revisões publicadas; PostgreSQL exige banco de testes."""
import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from archcorp.infrastructure.migrate import alembic_config, load_models


@pytest.fixture(params=["sqlite", "postgresql"])
def migration_engine(request, tmp_path):
    if request.param == "sqlite":
        engine = create_engine(f"sqlite:///{tmp_path / 'convergence.db'}")
        yield engine
        engine.dispose()
        return
    url = os.environ.get("TEST_DATABASE_URL")
    if not url or not url.startswith("postgresql"):
        pytest.skip("TEST_DATABASE_URL PostgreSQL não configurada")
    schema = "migration_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        admin.dispose()


@pytest.mark.parametrize("start", ["0003_contract_closing", "0004_finance_lifecycle", "0004_support_sla_history"])
def test_upgrade_de_cada_frente_preserva_dados_e_converge(migration_engine, start):
    engine = migration_engine
    with engine.begin() as connection:
        command.upgrade(alembic_config(connection), start)
        connection.execute(text("INSERT INTO support_tickets (ticket_id, customer_id, contract_id, service_code, category, description, status, priority) "
                                "VALUES ('t1', 'cu', 'c1', 'RENTAL-FLEX', 'QUESTION', 'Chamado sintético legado', 'OPEN', 'NORMAL')"))
        connection.execute(text("INSERT INTO finance_invoices (invoice_id, contract_id, customer_id, amount, currency, due_date, status) "
                                "VALUES ('i1', 'c1', 'cu', 100, 'BRL', '2026-10-15', 'OPEN')"))
    with engine.begin() as connection:
        command.upgrade(alembic_config(connection), "head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT description FROM support_tickets")).scalar_one() == "Chamado sintético legado"
        assert connection.execute(text("SELECT kind FROM finance_invoices")).scalar_one() == "INITIAL"
        assert compare_metadata(MigrationContext.configure(connection), load_models().metadata) == []
        assert MigrationContext.configure(connection).get_current_heads() == ("0005_merge_finance_support",)


def test_head_unica_e_downgrade_final_preserva_esquema_e_dados(migration_engine):
    engine = migration_engine
    assert ScriptDirectory.from_config(alembic_config()).get_heads() == ["0005_merge_finance_support"]
    with engine.begin() as connection:
        command.upgrade(alembic_config(connection), "head")
        connection.execute(text("INSERT INTO finance_invoices (invoice_id, contract_id, customer_id, amount, currency, due_date, status, kind) "
                                "VALUES ('f1', 'c1', 'cu', 100, 'BRL', '2026-10-15', 'OPEN', 'FINAL')"))
    with engine.connect() as connection:
        before = inspect(connection).get_table_names()
    with pytest.raises(RuntimeError, match="FINAL"), engine.begin() as connection:
        command.downgrade(alembic_config(connection), "0003_contract_closing")
    with engine.connect() as connection:
        assert inspect(connection).get_table_names() == before
        assert connection.execute(text("SELECT kind FROM finance_invoices")).scalar_one() == "FINAL"
        assert MigrationContext.configure(connection).get_current_heads() == ("0005_merge_finance_support",)


def test_banco_vazio_converge_para_head_unica_sem_divergencia(migration_engine):
    with migration_engine.begin() as connection:
        command.upgrade(alembic_config(connection), "head")
    with migration_engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), load_models().metadata) == []
        assert MigrationContext.configure(connection).get_current_heads() == ("0005_merge_finance_support",)
