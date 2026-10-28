"""F-QUA - AUD-23 e cegueira do teste de RLS (sem PostgreSQL local).

Uso: python -I teste_cegueira_rls.py <ISO>\\src
Replica a mesma chamada de tests/test_public_database_security.py (conexao falsa e engine
substituido por dialeto PostgreSQL) e lista as relacoes que recebem REVOKE/RLS. Compara com as
relacoes que o 01/10 mostrou expostas a anon/authenticated em PostgreSQL com padroes Supabase
simulados (evidencias/agente3/evidencias.md, E3-13): alembic_version e tres sequencias.
"""
import sys
from types import SimpleNamespace

sys.path.insert(0, sys.argv[1])

from sqlalchemy.dialects import postgresql  # noqa: E402

import archcorp.main  # noqa: F401,E402  (registra os modelos em Base.metadata, como o conftest)
import archcorp.infrastructure.db as db  # noqa: E402

statements: list[str] = []


class Connection:
    def execute(self, statement):
        return SimpleNamespace(scalars=lambda: ["anon", "authenticated"])

    def exec_driver_sql(self, statement):
        statements.append(statement)


db.engine = SimpleNamespace(dialect=postgresql.dialect())
db.settings.public_demo = True
db.protect_public_demo_tables(Connection())

revoked = sorted({s.split(" ON TABLE ", 1)[1].rsplit(" FROM ", 1)[0] for s in statements if " ON TABLE " in s})
rls = sorted({s.split("ALTER TABLE ", 1)[1].split(" ENABLE")[0] for s in statements if "ENABLE ROW LEVEL SECURITY" in s})
print(f"instrucoes emitidas: {len(statements)}")
print(f"relacoes com REVOKE (tabelas do metadata): {len(revoked)}")
print(f"relacoes com RLS: {len(rls)}")
print("alembic_version coberta por algum REVOKE:", any("alembic_version" in s for s in statements))
print("sequencias citadas em alguma instrucao:", any("SEQUENCE" in s.upper() for s in statements))
print("relacoes do metadata que o 01/10 mostrou expostas e que o codigo nao protege:")
print("  alembic_version (anon: SELECT/UPDATE/DELETE; authenticated: INSERT)")
print("  integration_audit_id_seq, integration_inbox_id_seq, integration_legacy_ids_id_seq (USAGE para anon)")
print("O teste compara apenas Base.metadata.sorted_tables; portanto nao pode falhar por essas relacoes.")
