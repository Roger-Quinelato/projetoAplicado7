# -*- coding: utf-8 -*-
"""F-SEG, E-06 (PostgreSQL): verificação de RLS e de privilégios com papéis anon/authenticated simulados.

STATUS: NÃO EXECUTADO nesta auditoria (sem PostgreSQL local; sem Docker). Foi escrito para rodar em
um banco PostgreSQL DESCARTÁVEL. Não use um banco real.

Variável obrigatória: SEG_PG_URL = URL do banco descartável com um papel dono (ex.: postgres),
que tenha CREATEROLE. A mesma URL é usada para criar os papéis, para as migrações da aplicação
(como faz o Supabase, em que o dono das tabelas é o papel postgres) e para as consultas.
Não imprima a URL; ela contém senha.

Passos:
1. Cria os papéis anon e authenticated (NOLOGIN) e as privilégios padrão do Supabase
   (ALTER DEFAULT PRIVILEGES ... GRANT ALL em tabelas e sequências do schema public).
2. Sobe a aplicação com PUBLIC_DEMO=true e DEMO_ACCESS_TOKEN aleatório, executando o lifespan
   (upgrade_to_head + protect_public_demo_tables).
3. Lista todas as relações do schema public (tabelas e sequências) e registra RLS e privilégios
   de anon e authenticated.
4. Testes negativos com SET ROLE anon: leitura de uma tabela do modelo, leitura de alembic_version
   e DELETE em alembic_version (dentro de transação com ROLLBACK).
Saída: JSON em logs/ com as relações e os resultados (sem credenciais).
"""
import datetime
import json
import os
import secrets
import sys

import psycopg
from psycopg import sql

sys.stdout.reconfigure(encoding="utf-8")
ISO = r"C:\Users\roger\.claude\jobs\f5019419\tmp\iso-seg"
LOGS = r"C:\Users\roger\projetoAplicado7\.claude\worktrees\auditoria-2026-10-18\output\auditoria\2026-10-18T2018Z\evidencias\seg\logs"

url_psycopg = os.environ["SEG_PG_URL"]
url_sqlalchemy = url_psycopg.replace("postgresql://", "postgresql+psycopg://", 1)
resultado = {"executado_em_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "passos": {}}

with psycopg.connect(url_psycopg, autocommit=True) as admin:
    for papel in ("anon", "authenticated"):
        try:
            admin.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(sql.Identifier(papel)))
        except psycopg.errors.DuplicateObject:
            pass
    admin.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO anon, authenticated"))
    admin.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon, authenticated")
    admin.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO anon, authenticated")

os.environ["DATABASE_URL"] = url_sqlalchemy
os.environ["PUBLIC_DEMO"] = "true"
os.environ["DEMO_ACCESS_TOKEN"] = secrets.token_hex(32)
os.environ.pop("RABBITMQ_URL", None)
sys.path.insert(0, os.path.join(ISO, "src"))
from fastapi.testclient import TestClient  # noqa: E402
from archcorp.main import app  # noqa: E402

with TestClient(app):
    resultado["passos"]["lifespan"] = "migrações e protect_public_demo_tables executadas"

with psycopg.connect(url_psycopg) as conexao:
    relacoes = conexao.execute(
        """SELECT c.relname, c.relkind, c.relrowsecurity
             FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind IN ('r', 'S')
            ORDER BY c.relkind, c.relname"""
    ).fetchall()
    inventario = []
    for nome, tipo, rls in relacoes:
        if tipo == "r":
            anon = conexao.execute("SELECT has_table_privilege('anon', %s, 'SELECT'), has_table_privilege('anon', %s, 'UPDATE'), has_table_privilege('anon', %s, 'DELETE')",
                                   (nome, nome, nome)).fetchone()
            auth = conexao.execute("SELECT has_table_privilege('authenticated', %s, 'SELECT'), has_table_privilege('authenticated', %s, 'INSERT')",
                                   (nome, nome)).fetchone()
            inventario.append({"relacao": nome, "tipo": "tabela", "rls": rls,
                               "anon_select_update_delete": list(anon), "authenticated_select_insert": list(auth)})
        else:
            uso = conexao.execute("SELECT has_sequence_privilege('anon', %s, 'USAGE')", (nome,)).fetchone()
            inventario.append({"relacao": nome, "tipo": "sequencia", "anon_usage": uso[0]})
    resultado["passos"]["inventario"] = inventario
    exposicoes = [i["relacao"] for i in inventario if (i["tipo"] == "tabela" and (any(i["anon_select_update_delete"]) or i["rls"] is False))
                  or (i["tipo"] == "sequencia" and i["anon_usage"])]
    resultado["passos"]["relacoes_expostas_ou_sem_rls"] = exposicoes

with psycopg.connect(url_psycopg) as conexao:
    testes = {}
    conexao.execute("SET ROLE anon")
    try:
        conexao.execute("SELECT count(*) FROM crm_customers")
        testes["anon_le_crm_customers"] = "permitido (falha de isolamento)"
    except psycopg.errors.InsufficientPrivilege:
        testes["anon_le_crm_customers"] = "bloqueado"
    conexao.rollback()
    conexao.execute("SET ROLE anon")
    try:
        conexao.execute("SELECT count(*) FROM alembic_version")
        testes["anon_le_alembic_version"] = "permitido (exposto)"
    except psycopg.errors.InsufficientPrivilege:
        testes["anon_le_alembic_version"] = "bloqueado"
    conexao.rollback()
    conexao.execute("SET ROLE anon")
    try:
        apagadas = conexao.execute("DELETE FROM alembic_version").rowcount
        testes["anon_apaga_alembic_version_rollback"] = f"permitido, linhas afetadas={apagadas} (revertido)"
    except psycopg.errors.InsufficientPrivilege:
        testes["anon_apaga_alembic_version_rollback"] = "bloqueado"
    conexao.rollback()
    resultado["passos"]["negativos_anon"] = testes

with open(os.path.join(LOGS, "e06_rls_postgres_resultado.json"), "w", encoding="utf-8") as arq:
    json.dump(resultado, arq, ensure_ascii=False, indent=1, default=str)
print(json.dumps(resultado["passos"].get("negativos_anon"), ensure_ascii=False, indent=1))
print("relações expostas ou sem RLS:", resultado["passos"].get("relacoes_expostas_ou_sem_rls"))
