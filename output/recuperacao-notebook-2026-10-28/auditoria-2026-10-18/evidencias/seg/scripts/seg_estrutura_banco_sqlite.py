# -*- coding: utf-8 -*-
"""F-SEG, item 8 (E-06, parte executada em SQLite): tabelas criadas pelas migrações versus as
tabelas que protect_public_demo_tables() percorre (Base.metadata.sorted_tables, db.py:49).

A proteção de RLS/REVOKE só roda em PostgreSQL; aqui se verifica, de forma estrutural, quais
relações o banco possui e quais delas o código de proteção não enxerga. Não substitui o teste
em PostgreSQL (ver seg_e06_rls_postgres.py, não executado).
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ISO = r"C:\Users\roger\.claude\jobs\f5019419\tmp\iso-seg"
banco = os.path.join(ISO, "tmp", "estrutura_sqlite.db")
if os.path.exists(banco):
    os.remove(banco)
os.environ["DATABASE_URL"] = "sqlite:///" + banco.replace("\\", "/")
for variavel in ("PUBLIC_DEMO", "DEMO_ACCESS_TOKEN", "RABBITMQ_URL"):
    os.environ.pop(variavel, None)
sys.path.insert(0, os.path.join(ISO, "src"))

from sqlalchemy import inspect as sa_inspect  # noqa: E402
from archcorp.infrastructure.db import Base, engine  # noqa: E402
from archcorp.infrastructure.migrate import upgrade_to_head  # noqa: E402

with engine.begin() as conexao:
    upgrade_to_head(conexao)

inspetor = sa_inspect(engine)
tabelas_banco = sorted(inspetor.get_table_names())
tabelas_modelo = sorted(t.name for t in Base.metadata.sorted_tables)
fora_do_laco = sorted(set(tabelas_banco) - set(tabelas_modelo))
print("dialeto:", engine.dialect.name)
print("tabelas no banco apos upgrade:", len(tabelas_banco))
print("tabelas em Base.metadata.sorted_tables (percorridas por protect_public_demo_tables):", len(tabelas_modelo))
print("relações no banco fora do laço de proteção:", fora_do_laco)
print("alembic_version existe:", "alembic_version" in tabelas_banco)
print("sequências: não existem em SQLite; a verificação de sequências é feita apenas no script de PostgreSQL")
