"""Experimento de migrações (Agente 3). Executar com cwd = cópia isolada, PYTHONPATH=src.
Uso: python mig_exp.py <url_sqlalchemy> <rótulo>
Não altera o repositório; usa somente o banco descartável informado."""
import os
import subprocess
import sys

URL, LABEL = sys.argv[1], sys.argv[2]
os.environ["DATABASE_URL"] = URL
from sqlalchemy import create_engine, inspect, text  # noqa: E402
from alembic.autogenerate import compare_metadata  # noqa: E402
from alembic.migration import MigrationContext  # noqa: E402

from archcorp.infrastructure.migrate import load_models, upgrade_to_head  # noqa: E402

PY = sys.executable
ENV = {**os.environ, "DATABASE_URL": URL, "PYTHONPATH": "src"}
ALEMBIC = [PY, "-m", "alembic", "-c", "alembic.ini"]
engine = create_engine(URL)


def alembic(*args):
    r = subprocess.run(ALEMBIC + list(args), env=ENV, capture_output=True, text=True)
    tail = (r.stdout + r.stderr).strip().splitlines()[-1:] if r.returncode else []
    print(f"  alembic {' '.join(args)} -> rc={r.returncode} {tail}")
    return r.returncode


def reset():
    with engine.begin() as c:
        if engine.dialect.name == "postgresql":
            c.exec_driver_sql("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        else:
            for t in inspect(c).get_table_names():
                c.exec_driver_sql(f'DROP TABLE "{t}"')


def state():
    with engine.connect() as c:
        rev = MigrationContext.configure(c).get_current_revision()
        diff = compare_metadata(MigrationContext.configure(c), load_models().metadata)
    return rev, diff


print(f"== [{LABEL}] dialeto={engine.dialect.name}")
# 1. Banco vazio -> upgrade head (CLI)
reset()
print("1. banco vazio -> upgrade head")
alembic("upgrade", "head")
rev, diff = state()
print(f"  revisão={rev} divergências_modelo={len(diff)} {diff[:3]}")

# 2. downgrade base e novo upgrade
print("2. downgrade base -> upgrade head (reversibilidade)")
alembic("downgrade", "base")
with engine.connect() as c:
    print(f"  tabelas após downgrade base: {sorted(set(inspect(c).get_table_names()) - {'alembic_version'})}")
alembic("upgrade", "head")
rev, diff = state()
print(f"  revisão={rev} divergências={len(diff)}")

# 3. Banco legado em 0001 com dados -> upgrade head
print("3. banco legado em 0001 com dados -> upgrade head")
reset()
alembic("upgrade", "0001_baseline")
with engine.begin() as c:
    c.execute(text("INSERT INTO crm_customers (customer_id,name,email,eligible,consent_service) VALUES "
                   "('00000000-0000-4000-8000-000000000001','Legado Sintetico','legado@example.com',true,true)"))
    c.execute(text("INSERT INTO contracts_contracts (contract_id,customer_id,customer_name,customer_email,service_code,starts_on,amount,currency,billing_cycle,sla_hours,status) VALUES "
                   "('00000000-0000-4000-8000-0000000000c1','00000000-0000-4000-8000-000000000001','Legado Sintetico','legado@example.com','RENTAL-FLEX','2026-10-01',123.45,'BRL','MONTHLY',8,'ACTIVE')"))
    c.execute(text("INSERT INTO integration_idempotency (key,operation,response,created_at) VALUES ('k-legado','draft','{}', CURRENT_TIMESTAMP)"))
alembic("upgrade", "head")
rev, diff = state()
with engine.connect() as c:
    cust = c.execute(text("SELECT name,email,active FROM crm_customers")).all()
    con = c.execute(text("SELECT amount,status,ends_on,close_reason FROM contracts_contracts")).all()
    idem = c.execute(text("SELECT key,request_hash FROM integration_idempotency")).all()
    uniques = {t: [u["column_names"] for u in inspect(c).get_unique_constraints(t)] for t in ("crm_customers", "contracts_contracts")}
print(f"  revisão={rev} divergências={len(diff)}")
print(f"  clientes={cust} contratos={con} idempotência={idem}")
print(f"  unicidades preservadas={uniques}")
with engine.begin() as c:
    try:
        c.execute(text("INSERT INTO crm_customers (customer_id,name,email,eligible,consent_service,active) VALUES "
                       "('00000000-0000-4000-8000-000000000002','Dup','legado@example.com',true,true,true)"))
        print("  RESTRIÇÃO email único: NÃO aplicada (inserção duplicada aceita)")
    except Exception as exc:  # esperado
        print(f"  RESTRIÇÃO email único aplicada: {type(exc).__name__}")

# 4. Banco legado sem alembic_version (criado por create_all em 0001) -> upgrade_to_head da aplicação
print("4. legado 0001 sem alembic_version -> upgrade_to_head (inicialização)")
reset()
alembic("upgrade", "0001_baseline")
with engine.begin() as c:
    c.exec_driver_sql("DROP TABLE alembic_version")
    c.execute(text("INSERT INTO crm_customers (customer_id,name,email,eligible,consent_service) VALUES "
                   "('00000000-0000-4000-8000-000000000003','Sem Carimbo','sc@example.com',true,true)"))
with engine.begin() as c:
    upgrade_to_head(c)
rev, diff = state()
with engine.connect() as c:
    print(f"  revisão={rev} divergências={len(diff)} clientes={c.execute(text('SELECT email,active FROM crm_customers')).all()}")

# 5. Caso de borda: esquema em 0002 sem alembic_version -> upgrade_to_head
print("5. borda: esquema em 0002 sem alembic_version -> upgrade_to_head")
reset()
alembic("upgrade", "0002_customer_active")
with engine.begin() as c:
    c.exec_driver_sql("DROP TABLE alembic_version")
try:
    with engine.begin() as c:
        upgrade_to_head(c)
    rev, diff = state()
    print(f"  resultado: revisão={rev} divergências={len(diff)}")
except Exception as exc:
    print(f"  FALHA na inicialização: {type(exc).__name__}: {str(exc).splitlines()[0][:200]}")

# 6. offline SQL
print("6. alembic upgrade head --sql (offline)")
r = subprocess.run(ALEMBIC + ["upgrade", "head", "--sql"], env=ENV, capture_output=True, text=True)
print(f"  rc={r.returncode} linhas_sql={len(r.stdout.splitlines())}")
