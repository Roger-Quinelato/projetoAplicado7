"""E-12 (ADR-002, ADR-003, AUD-33): migrações em SQLite.

A) upgrade a partir de cada revisão intermediária, com dados, até a cabeça.
B) caminhos de volta com dados (head -> 0003 -> 0002 -> 0001 -> base) e volta ao head.
C) bloqueio de downgrade com fatura FINAL (ADR-003).
D) banco sem alembic_version (casos de borda, AUD-33).
E) política AST das migrações (operações destrutivas no upgrade) e cabeça única.
PostgreSQL: coberto por tests/test_migration_convergence.py no job postgresql da CI (não executado localmente).
"""
import ast
from collections import Counter

from dad_common import ISO, setup

setup("e12_scratch.db")
from alembic import command  # noqa: E402
from alembic.autogenerate import compare_metadata  # noqa: E402
from alembic.migration import MigrationContext  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from archcorp.infrastructure.migrate import alembic_config, load_models, upgrade_to_head  # noqa: E402

REVISOES = ["0001_baseline", "0002_customer_active", "0003_contract_closing",
            "0004_finance_lifecycle", "0004_support_sla_history", "0005_merge_finance_support"]
TABELAS = ["crm_customers", "contracts_contracts", "finance_invoices", "finance_payments", "support_tickets"]


def banco(nome):
    caminho = ISO / "tmp" / nome
    if caminho.exists():
        caminho.unlink()
    return create_engine("sqlite:///" + caminho.as_posix())


def semear(conn):
    """Dados que existem desde a 0001 (colunas comuns): clientes, contrato, fatura OPEN com pagamento, chamado."""
    conn.execute(text("INSERT INTO crm_customers (customer_id, name, email, eligible, consent_service) VALUES "
                      "('00000000-0000-4000-8000-000000000001', 'Cliente Legado', 'legado@example.com', 1, 1)"))
    conn.execute(text("INSERT INTO contracts_contracts (contract_id, customer_id, customer_name, customer_email, service_code, "
                      "starts_on, amount, currency, billing_cycle, sla_hours, status) VALUES "
                      "('00000000-0000-4000-8000-0000000000c1', '00000000-0000-4000-8000-000000000001', 'Cliente Legado', "
                      "'legado@example.com', 'RENTAL-FLEX', '2026-10-01', 123.45, 'BRL', 'MONTHLY', 8, 'ACTIVE')"))
    conn.execute(text("INSERT INTO finance_invoices (invoice_id, contract_id, customer_id, amount, currency, due_date, status) VALUES "
                      "('00000000-0000-4000-8000-0000000000f1', '00000000-0000-4000-8000-0000000000c1', "
                      "'00000000-0000-4000-8000-000000000001', 123.45, 'BRL', '2026-10-11', 'OPEN')"))
    conn.execute(text("INSERT INTO finance_payments (payment_id, invoice_id, amount, currency, reference) VALUES "
                      "('00000000-0000-4000-8000-0000000000a1', '00000000-0000-4000-8000-0000000000f1', 50, 'BRL', 'LEG-PAY-1')"))
    conn.execute(text("INSERT INTO support_tickets (ticket_id, customer_id, contract_id, service_code, category, description, "
                      "status, priority) VALUES ('00000000-0000-4000-8000-0000000000d1', '00000000-0000-4000-8000-000000000001', "
                      "'00000000-0000-4000-8000-0000000000c1', 'RENTAL-FLEX', 'OUTAGE', 'Chamado legado sintético', 'OPEN', 'HIGH')"))
    conn.execute(text("INSERT INTO integration_idempotency (key, operation, response, created_at) VALUES "
                      "('k-legado', 'create_contract_draft', '{}', CURRENT_TIMESTAMP)"))


def estado(conn):
    return {t: conn.execute(text(f"SELECT count(*) FROM {t}")).scalar() for t in TABELAS}


def divergencias(conn):
    return len(compare_metadata(MigrationContext.configure(conn), load_models().metadata))


print("== A: upgrade a partir de cada revisão intermediária, com dados")
for rev in REVISOES:
    eng = banco(f"e12_{rev}.db")
    with eng.begin() as conn:
        command.upgrade(alembic_config(conn), rev)
        semear(conn)
    with eng.begin() as conn:
        command.upgrade(alembic_config(conn), "head")
    with eng.connect() as conn:
        cabeca = MigrationContext.configure(conn).get_current_heads()
        print(f"{rev}: cabeca={cabeca} divergencias_modelo={divergencias(conn)} dados={estado(conn)} "
              f"faturas(status,kind)={conn.execute(text('SELECT status, kind FROM finance_invoices')).all()}")

print("== B: caminhos de volta com dados")
eng = banco("e12_down.db")
with eng.begin() as conn:
    command.upgrade(alembic_config(conn), "head")
    semear(conn)
for alvo in ["0003_contract_closing", "0002_customer_active", "0001_baseline", "base"]:
    try:
        with eng.begin() as conn:
            command.downgrade(alembic_config(conn), alvo)
        print(f"downgrade -> {alvo}: OK")
    except Exception as exc:
        print(f"downgrade -> {alvo}: FALHOU {type(exc).__name__}: {str(exc)[:150]}")
        break
with eng.begin() as conn:
    command.upgrade(alembic_config(conn), "head")
with eng.connect() as conn:
    print("após voltar e subir ao head: cabeca =", MigrationContext.configure(conn).get_current_heads(),
          "| divergencias_modelo =", divergencias(conn))

print("== C: downgrade com fatura FINAL (ADR-003)")
eng = banco("e12_final.db")
with eng.begin() as conn:
    command.upgrade(alembic_config(conn), "head")
    semear(conn)
    conn.execute(text("INSERT INTO finance_invoices (invoice_id, contract_id, customer_id, amount, currency, due_date, status, kind) "
                      "VALUES ('00000000-0000-4000-8000-0000000000f2', '00000000-0000-4000-8000-0000000000c1', "
                      "'00000000-0000-4000-8000-000000000001', 50, 'BRL', '2026-11-01', 'OPEN', 'FINAL')"))
try:
    with eng.begin() as conn:
        command.downgrade(alembic_config(conn), "0003_contract_closing")
    print("downgrade com FINAL: NÃO bloqueado")
except Exception as exc:
    print(f"downgrade com FINAL: bloqueado {type(exc).__name__}: {str(exc)[:120]}")
with eng.connect() as conn:
    print("faturas após a tentativa (status, kind):",
          conn.execute(text("SELECT status, kind FROM finance_invoices ORDER BY kind")).all(),
          "| cabeca =", MigrationContext.configure(conn).get_current_heads())

print("== D: banco sem alembic_version (AUD-33)")
for rev in ["0001_baseline", "0002_customer_active"]:
    eng = banco(f"e12_sem_carimbo_{rev}.db")
    with eng.begin() as conn:
        command.upgrade(alembic_config(conn), rev)
        conn.exec_driver_sql("DROP TABLE alembic_version")
    try:
        with eng.begin() as conn:
            upgrade_to_head(conn)
        with eng.connect() as conn:
            print(f"sem carimbo em {rev}: OK | cabeca={MigrationContext.configure(conn).get_current_heads()} "
                  f"| divergencias_modelo={divergencias(conn)}")
    except Exception as exc:
        print(f"sem carimbo em {rev}: FALHOU {type(exc).__name__}: {str(exc)[:160]}")

print("== E: política AST das migrações (upgrade) e cabeça única")
DESTRUTIVAS = {"drop_table", "drop_column", "alter_column", "rename_table", "drop_constraint", "drop_index"}
SQL_PROIBIDO = ("UPDATE", "DELETE", "DROP", "ALTER", "RENAME", "TRUNCATE")
for arq in sorted((ISO / "src/archcorp/infrastructure/migrations/versions").glob("*.py")):
    arvore = ast.parse(arq.read_text(encoding="utf-8"))
    upgrade = next(n for n in arvore.body if isinstance(n, ast.FunctionDef) and n.name == "upgrade")
    cont = Counter()
    for no in ast.walk(upgrade):
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute):
            if no.func.attr in DESTRUTIVAS:
                cont[no.func.attr] += 1
            if no.func.attr == "execute":
                arg = no.args[0] if no.args else None
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    primeira = arg.value.strip().split()[0].upper()
                    if primeira in SQL_PROIBIDO:
                        cont[f"execute {primeira}"] += 1
                else:
                    cont["execute nao literal"] += 1
    print(f"{arq.name}: {dict(cont) or 'sem operações destrutivas no upgrade'}")
print("cabeças:", ScriptDirectory.from_config(alembic_config()).get_heads())
