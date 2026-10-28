# -*- coding: utf-8 -*-
"""F-SEG, item 4 (entrada): ordem entre leitura/validação do corpo e a autenticação.

Sem token, um POST protegido com JSON inválido responde 422 (o corpo foi lido e validado antes
da dependência de autenticação) ou 401 (a autenticação veio primeiro)? Execução em TestClient
com SQLite da cópia isolada.
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ISO = r"C:\Users\roger\.claude\jobs\f5019419\tmp\iso-seg"
LOGS = r"C:\Users\roger\projetoAplicado7\.claude\worktrees\auditoria-2026-10-18\output\auditoria\2026-10-18T2018Z\evidencias\seg\logs"
banco = os.path.join(ISO, "tmp", "preautenticacao.db")
if os.path.exists(banco):
    os.remove(banco)
os.environ["DATABASE_URL"] = "sqlite:///" + banco.replace("\\", "/")
for variavel in ("PUBLIC_DEMO", "DEMO_ACCESS_TOKEN", "RABBITMQ_URL"):
    os.environ.pop(variavel, None)
sys.path.insert(0, os.path.join(ISO, "src"))

from fastapi.testclient import TestClient  # noqa: E402
from archcorp.main import app  # noqa: E402

casos = {
    "json_invalido_sem_token": ({}, b"{"),
    "json_valido_sem_token": ({}, b"{}"),
    "json_invalido_com_token_admin": ({"Authorization": "Bearer demo-admin"}, b"{"),
    "corpo_nao_json_sem_token": ({"Content-Type": "application/json"}, b"xx" * 1000),
}
R = {}
with TestClient(app, raise_server_exceptions=False) as cliente:
    for nome, (cabecalhos, corpo) in casos.items():
        cabecalhos = {"Content-Type": "application/json", **cabecalhos}
        resp = cliente.post("/api/v1/crm/customers", headers=cabecalhos, content=corpo)
        try:
            codigo = resp.json().get("code")
        except ValueError:
            codigo = None
        R[nome] = {"status": resp.status_code, "code": codigo}
with open(os.path.join(LOGS, "preautenticacao_resultado.json"), "w", encoding="utf-8") as arq:
    json.dump(R, arq, ensure_ascii=False, indent=1)
for nome, valor in R.items():
    print(nome, "->", valor)
