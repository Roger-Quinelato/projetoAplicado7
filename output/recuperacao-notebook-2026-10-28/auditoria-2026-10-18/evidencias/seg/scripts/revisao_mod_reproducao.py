# -*- coding: utf-8 -*-
"""Revisão cruzada (F-SEG sobre F-MOD): reprodução barata e independente, somente em SQLite.

Cópia isolada iso-seg (commit 44b8325). Sem PostgreSQL, RabbitMQ, Docker ou instalação.
Cada bloco reproduz uma alegação de MOD-nn do arquivo evidencias\\mod\\achados.md.
Saída: logs\\revisao_mod_reproducao.txt e logs\\revisao_mod_reproducao.json (sem credenciais).
"""
import ast
import datetime
import json
import os
import pathlib
import sys
import uuid

sys.stdout.reconfigure(encoding="utf-8")
ISO = r"C:\Users\roger\.claude\jobs\f5019419\tmp\iso-seg"
PKG = r"C:\Users\roger\projetoAplicado7\.claude\worktrees\auditoria-2026-10-18\output\auditoria\2026-10-18T2018Z\evidencias\seg"
LOGS = os.path.join(PKG, "logs")
SRC = pathlib.Path(ISO, "src", "archcorp")
banco = os.path.join(ISO, "tmp", "revisao_mod.db")
if os.path.exists(banco):
    os.remove(banco)
os.environ["DATABASE_URL"] = "sqlite:///" + banco.replace("\\", "/")
for variavel in ("PUBLIC_DEMO", "DEMO_ACCESS_TOKEN", "RABBITMQ_URL", "TEST_DATABASE_URL"):
    os.environ.pop(variavel, None)
sys.path.insert(0, os.path.join(ISO, "src"))

from fastapi.testclient import TestClient  # noqa: E402
from archcorp.main import app, dispatcher  # noqa: E402
from archcorp.infrastructure.db import SessionLocal  # noqa: E402
from archcorp.contracts.service import ContractService  # noqa: E402
from archcorp.contracts.models import Contract  # noqa: E402

R = {}
L = []
ADMIN = {"Authorization": "Bearer demo-admin"}
CONTEXTOS = {"crm", "contracts", "finance", "support", "workflow"}


def registrar(chave_, valor):
    R[chave_] = valor
    L.append(f"{chave_}: {valor}")


def H(extra=None):
    cabecalhos = dict(ADMIN)
    if extra:
        cabecalhos.update(extra)
    return cabecalhos


def chave():
    return str(uuid.uuid4())


def inicio_em(dias):
    return (datetime.date.today() + datetime.timedelta(days=dias)).isoformat()


def criar_cliente(c, nome="Cliente Revisão Sintético"):
    email = f"rev-{uuid.uuid4().hex[:8]}@cliente-sintetico.example.com"
    r = c.post("/api/v1/crm/customers", headers=H(), json={"name": nome, "email": email})
    assert r.status_code == 201, r.text
    return r.json()["customerId"]


def criar_contrato_ativo(c, cid):
    r = c.post("/api/v1/contracts/drafts", headers=H({"Idempotency-Key": chave()}), json={
        "customerId": cid, "serviceCode": "RENTAL-FLEX", "startsOn": inicio_em(5),
        "billing": {"amount": 1000, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8})
    assert r.status_code == 201, r.text
    contrato = r.json()["contractId"]
    a = c.post(f"/api/v1/contracts/{contrato}/activate", headers=H({"Idempotency-Key": chave()}))
    assert a.status_code == 200, a.text
    return contrato


def despachar(c):
    return c.post("/api/v1/integration/outbox/dispatch", headers=H())


def processo_onboarding(c, contrato):
    processos = c.get("/api/v1/workflow/processes", headers=H()).json()
    return next(p for p in processos if p["processType"] == "ONBOARDING" and p["referenceId"] == contrato)


def tarefas(c, pid):
    return c.get(f"/api/v1/workflow/tasks?processId={pid}", headers=H()).json()


def estado_processo(c, pid):
    return c.get(f"/api/v1/workflow/processes/{pid}", headers=H()).json()["state"]


# ---------------- Predicados copiados dos quatro testes de fronteira (MOD-04) ----------------
def t1_modelos_de_outro_contexto(codigo, contexto):
    """Réplica de test_modulos_de_negocio_nao_importam_models_de_outro_contexto (só ImportFrom)."""
    for nodo in ast.walk(ast.parse(codigo)):
        if isinstance(nodo, ast.ImportFrom) and nodo.module:
            partes = nodo.module.split(".")
            if len(partes) >= 3 and partes[0] == "archcorp" and partes[1] in CONTEXTOS - {contexto} and partes[2] == "models":
                return True
    return False


def t2_composicao_sem_modelos(codigo):
    """Réplica de test_composicao_da_aplicacao_nao_le_modelos_dos_contextos (só ImportFrom)."""
    contextos = CONTEXTOS | {"integration"}
    for nodo in ast.walk(ast.parse(codigo)):
        if isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.module.startswith("archcorp.") \
                and nodo.module.endswith(".models") and nodo.module.split(".")[1] in contextos:
            return True
    return False


def t3_fachada_integracao(codigo):
    """Réplica de test_negocios_usam_apenas_fachada_publica_da_integracao (só ImportFrom)."""
    for nodo in ast.walk(ast.parse(codigo)):
        if isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.module.startswith("archcorp.integration.") \
                and nodo.module != "archcorp.integration.public":
            return True
    return False


def t4_dominio_puro(codigo):
    """Réplica de test_dominios_nao_dependem_de_infraestrutura_ou_http (só ImportFrom)."""
    for nodo in ast.walk(ast.parse(codigo)):
        if isinstance(nodo, ast.ImportFrom) and nodo.module:
            if nodo.module.split(".")[0] in {"sqlalchemy", "fastapi", "pydantic"} \
                    or any(parte in nodo.module for parte in (".models", ".routes", ".service", ".infrastructure")):
                return True
    return False


with TestClient(app, raise_server_exceptions=False) as c:
    # ---------------- MOD-01: transições de tarefa ----------------
    cid_a = criar_cliente(c)
    ctr_a = criar_contrato_ativo(c, cid_a)
    despachar(c)
    pid_a = processo_onboarding(c, ctr_a)["processId"]
    tid_a = tarefas(c, pid_a)[0]["taskId"]
    seq_a = []
    for estado in ["CANCELLED", "IN_PROGRESS", "DONE", "OPEN"]:
        r = c.patch(f"/api/v1/workflow/tasks/{tid_a}", headers=H(), json={"state": estado})
        seq_a.append({"para": estado, "http": r.status_code, "detalhe": r.json().get("detail") if r.status_code >= 400 else None,
                      "processo_depois": estado_processo(c, pid_a)})
    registrar("MOD-01 cenario A (processo com uma tarefa)", seq_a)

    cid_b = criar_cliente(c)
    ctr_b = criar_contrato_ativo(c, cid_b)
    despachar(c)
    pid_b = processo_onboarding(c, ctr_b)["processId"]
    extra = c.post("/api/v1/workflow/tasks", headers=H(), json={"processId": pid_b, "title": "Conferir documentos da retirada", "owner": "operations"})
    registrar("MOD-01 segunda tarefa criada (HTTP)", extra.status_code)
    tid_b = next(t["taskId"] for t in tarefas(c, pid_b) if t["taskId"] != extra.json().get("taskId"))
    seq_b = []
    for estado in ["CANCELLED", "IN_PROGRESS", "DONE", "OPEN"]:
        r = c.patch(f"/api/v1/workflow/tasks/{tid_b}", headers=H(), json={"state": estado})
        seq_b.append({"para": estado, "http": r.status_code, "processo_depois": estado_processo(c, pid_b)})
    registrar("MOD-01 cenario B (processo com duas tarefas; a segunda segue aberta)", seq_b)

    # ---------------- MOD-02: encerramento e chamado aberto ----------------
    cid_c = criar_cliente(c)
    ctr_c = criar_contrato_ativo(c, cid_c)
    despachar(c)
    pid_c = processo_onboarding(c, ctr_c)["processId"]
    chamado = c.post("/api/v1/support/tickets", headers=H({"Idempotency-Key": chave()}), json={
        "customerId": cid_c, "contractId": ctr_c, "serviceCode": "RENTAL-FLEX", "category": "OUTAGE",
        "description": "Chamado de reprodução da revisão cruzada"})
    registrar("MOD-02 chamado aberto (HTTP, status do chamado)",
              [chamado.status_code, chamado.json().get("status") if chamado.status_code == 201 else None])
    tid_chamado = chamado.json()["ticketId"]
    despachar(c)
    fechamento = c.post(f"/api/v1/contracts/{ctr_c}/close", headers=H())
    registrar("MOD-02 encerramento do contrato (HTTP)", fechamento.status_code)
    despachar(c)
    registrar("MOD-02 chamado depois do encerramento (status)", c.get(f"/api/v1/support/tickets/{tid_chamado}", headers=H()).json().get("status"))
    resolucao = c.post(f"/api/v1/support/tickets/{tid_chamado}/resolve", headers=H())
    registrar("MOD-02 resolver chamado de contrato encerrado (HTTP)", resolucao.status_code)
    registrar("MOD-02 processo ONBOARDING depois do encerramento", estado_processo(c, pid_c))
    registrar("MOD-02 tarefas ONBOARDING depois do encerramento", [t["state"] for t in tarefas(c, pid_c)])
    faturas = c.get(f"/api/v1/finance/invoices?contractId={ctr_c}", headers=H()).json()
    registrar("MOD-02 tipos de fatura do contrato", sorted(f["kind"] for f in faturas))
    registrar("MOD-02 consumidores de ContractClosed.v1 (main.py:54-62)",
              [nome for nome, _ in dispatcher.handlers.get("ContractClosed.v1", [])])
    registrar("MOD-02 consumidores cujo nome começa com support",
              [nome for _, lista in dispatcher.handlers.items() for nome, _ in lista if nome.startswith("support")])

    # ---------------- MOD-06: 404 contra 422 e normalização UTC ----------------
    fantasma = str(uuid.uuid4())
    reserva = c.post("/api/v1/contracts/reservations", headers=H(), json={
        "customerId": fantasma, "vehicleGroup": "SUV-COMPACTO", "protectionCode": "BASICA", "serviceCode": "RENTAL-FLEX",
        "startsOn": inicio_em(30), "endsOn": inicio_em(33), "amount": 750, "currency": "BRL",
        "billingCycle": "ONCE", "slaHours": 8})
    registrar("MOD-06 reserva com cliente inexistente (status, detalhe)", [reserva.status_code, reserva.json().get("detail")])
    rascunho = c.post("/api/v1/contracts/drafts", headers=H({"Idempotency-Key": chave()}), json={
        "customerId": fantasma, "serviceCode": "RENTAL-FLEX", "startsOn": inicio_em(5),
        "billing": {"amount": 100, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8})
    registrar("MOD-06 rascunho com cliente inexistente (status, detalhe)", [rascunho.status_code, rascunho.json().get("detail")])

    from archcorp.finance.domain import as_utc as fin_as_utc
    from archcorp.support.domain import as_utc as sup_as_utc
    from archcorp.finance.service import iso_utc as fin_iso_utc
    from archcorp.workflow.service import _parse_utc as wf_parse_utc
    ingenuo = datetime.datetime(2026, 10, 20, 9, 0, 0)
    try:
        resultado_fin = fin_as_utc(ingenuo).isoformat()
    except ValueError as exc:
        resultado_fin = f"ValueError: {exc}"
    registrar("MOD-06 horário sem fuso em finance.domain.as_utc", resultado_fin)
    registrar("MOD-06 horário sem fuso em support.domain.as_utc", sup_as_utc(ingenuo).isoformat())
    registrar("MOD-06 horário sem fuso em finance.service.iso_utc", fin_iso_utc(ingenuo))
    registrar("MOD-06 horário sem fuso em workflow.service._parse_utc", wf_parse_utc("2026-10-20T09:00:00").isoformat())

    # ---------------- MOD-08: projeção de cliente com evento antigo ----------------
    cid_p = criar_cliente(c, nome="Nome Versao 1")
    ctr_p = criar_contrato_ativo(c, cid_p)
    c.patch(f"/api/v1/crm/customers/{cid_p}", headers=H(), json={"name": "Nome Versao 2"})
    with SessionLocal() as sessao:
        ContractService.apply_customer_update(sessao, {"payload": {"customerId": cid_p, "name": "Nome Versao 2", "email": "v2@cliente-sintetico.example.com"}})
        sessao.commit()
        ContractService.apply_customer_update(sessao, {"payload": {"customerId": cid_p, "name": "Nome Versao 1", "email": "v1@cliente-sintetico.example.com"}})
        sessao.commit()
        projecao = sessao.get(Contract, ctr_p).customer_name
    registrar("MOD-08 projeção depois de v2 e do v1 antigo (customer_name)", projecao)
    registrar("MOD-08 nome oficial no CRM", c.get(f"/api/v1/crm/customers/{cid_p}", headers=H()).json()["name"])
    registrar("MOD-08 campos do contrato na API", sorted(c.get(f"/api/v1/contracts/{ctr_p}", headers=H()).json().keys()))
    arquivos_que_leem = []
    for arq in SRC.rglob("*.py"):
        if arq.name == "models.py" or "migrations" in arq.parts:
            continue
        texto = arq.read_text(encoding="utf-8")
        if "customer_name" in texto or "customer_email" in texto:
            arquivos_que_leem.append(arq.relative_to(ISO).as_posix())
    registrar("MOD-08 arquivos fora de modelos e migrações que citam customer_name ou customer_email", arquivos_que_leem)

    # ---------------- MOD-05: fronteiras de camadas (AST, sem execução) ----------------
    proibidos = []
    for arq in list(SRC.glob("*/service.py")) + list(SRC.glob("*/domain.py")):
        for nodo in ast.walk(ast.parse(arq.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.ImportFrom) and nodo.module:
                if nodo.module.split(".")[0] == "fastapi" or any(a.name == "HTTPException" for a in nodo.names):
                    proibidos.append(f"{arq.relative_to(ISO).as_posix()}:{nodo.lineno}")
            if isinstance(nodo, ast.Import) and any(a.name.split(".")[0] == "fastapi" for a in nodo.names):
                proibidos.append(f"{arq.relative_to(ISO).as_posix()}:{nodo.lineno}")
    registrar("MOD-05 imports de fastapi ou HTTPException em service.py e domain.py", proibidos)
    registrar("MOD-05 arquivos que importam pika",
              [arq.relative_to(ISO).as_posix() for arq in SRC.rglob("*.py") if "import pika" in arq.read_text(encoding="utf-8")])

    # ---------------- MOD-04: cegueira dos testes de fronteira ----------------
    casos = [
        (1, "from archcorp.contracts.models import Contract", "crm/service.py", "modelo de outro contexto, from"),
        (2, "from archcorp.contracts import models", "crm/service.py", "from pacote importando models"),
        (3, "import archcorp.contracts.models as m", "crm/service.py", "import com alias"),
        (4, "from archcorp.contracts.service import ContractService", "crm/service.py", "serviço interno de outro contexto"),
        (5, "import archcorp.integration.service", "crm/service.py", "import simples de integração interna"),
        (6, "from archcorp.integration import models", "crm/service.py", "from pacote importando models da integração"),
        (7, "from archcorp.integration.service import audit", "crm/service.py", "from integração interna"),
        (8, "import sqlalchemy", "contracts/domain.py", "import simples de infraestrutura no domínio"),
        (9, "from sqlalchemy import select", "contracts/domain.py", "from infraestrutura no domínio"),
        (10, "from archcorp.contracts.models import Contract", "main.py", "modelo na composição, from"),
        (11, "from archcorp.contracts import models", "main.py", "from pacote importando models na composição"),
        (12, "import archcorp.contracts.models", "main.py", "import simples de modelo na composição"),
    ]
    tabela = []
    for numero, codigo, arquivo, descricao in casos:
        contexto = arquivo.split("/")[0] if "/" in arquivo else None
        testes = {}
        if contexto in CONTEXTOS:
            testes["T1_modelos"] = t1_modelos_de_outro_contexto(codigo, contexto)
            testes["T3_fachada"] = t3_fachada_integracao(codigo)
        if arquivo == "main.py":
            testes["T2_composicao"] = t2_composicao_sem_modelos(codigo)
        if arquivo.endswith("domain.py"):
            testes["T4_dominio"] = t4_dominio_puro(codigo)
        tabela.append({"caso": numero, "descricao": descricao, "codigo": codigo, "arquivo": arquivo,
                       "testes": testes, "detectado": any(testes.values())})
    registrar("MOD-04 casos sintéticos detectados por algum teste (de 12)", sum(1 for x in tabela if x["detectado"]))
    registrar("MOD-04 casos sintéticos não detectados (número)", [x["caso"] for x in tabela if not x["detectado"]])

    # Varredura do código real com a mesma regra de fachada: qualquer forma de import que cruze contextos sem passar pelo public.
    cruzamentos = []
    for arq in SRC.rglob("*.py"):
        partes_rel = arq.relative_to(SRC).parts
        contexto = partes_rel[0] if len(partes_rel) > 1 and partes_rel[0] in CONTEXTOS else None
        if contexto is None:
            continue
        for nodo in ast.walk(ast.parse(arq.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.Import):
                nomes = [a.name for a in nodo.names]
            elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                nomes = [f"{nodo.module}.{a.name}" for a in nodo.names]
            else:
                continue
            for nome in nomes:
                partes = nome.split(".")
                if len(partes) < 2 or partes[0] != "archcorp":
                    continue
                alvo = partes[1]
                if alvo == contexto:
                    continue
                if alvo in CONTEXTOS | {"integration"} and not (len(partes) >= 3 and partes[2] == "public"):
                    cruzamentos.append(f"{arq.relative_to(ISO).as_posix()}:{nodo.lineno}:{nome}")
    registrar("MOD-04 cruzamentos reais entre contextos sem passar por public (varredura AST de qualquer forma)", cruzamentos)

with open(os.path.join(LOGS, "revisao_mod_reproducao.json"), "w", encoding="utf-8") as arq:
    json.dump({"resultados": R, "fronteira_casos": tabela}, arq, ensure_ascii=False, indent=1, default=str)
with open(os.path.join(LOGS, "revisao_mod_reproducao.txt"), "w", encoding="utf-8") as arq:
    arq.write("\n".join(L) + "\n")
print("\n".join(L))
