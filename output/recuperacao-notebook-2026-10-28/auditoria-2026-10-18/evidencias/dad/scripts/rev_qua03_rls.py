"""Revisão cruzada de QUA-03 (independente): o que protect_public_demo_tables emite para um dialeto PostgreSQL falso.

Não conecta a banco algum: a conexão é um objeto que registra as instruções. Mesmo procedimento de
tests/test_public_database_security.py, sem pytest."""
from types import SimpleNamespace

from sqlalchemy.dialects import postgresql

from dad_common import setup

setup("rev_qua03.db")
import archcorp.infrastructure.db as db  # noqa: E402

statements = []


class Conexao:
    def execute(self, statement):
        return SimpleNamespace(scalars=lambda: ["anon", "authenticated"])

    def exec_driver_sql(self, statement):
        statements.append(statement)


engine_original, publico_original = db.engine, db.settings.public_demo
db.engine = SimpleNamespace(dialect=postgresql.dialect())
db.settings.public_demo = True
try:
    db.protect_public_demo_tables(Conexao())
finally:
    db.engine, db.settings.public_demo = engine_original, publico_original
print("relações no metadata:", len(db.Base.metadata.sorted_tables))
print("instruções emitidas:", len(statements),
      "| RLS:", sum("ROW LEVEL SECURITY" in s for s in statements),
      "| REVOKE:", sum("REVOKE" in s for s in statements))
print("cita alembic_version:", any("alembic_version" in s for s in statements))
print("cita sequências:", any("SEQUENCE" in s.upper() for s in statements))
