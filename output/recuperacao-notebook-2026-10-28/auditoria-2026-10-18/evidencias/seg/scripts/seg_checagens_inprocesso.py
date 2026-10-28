# -*- coding: utf-8 -*-
"""F-SEG, item 5 (erros), item 4 (entrada) e item 4 da heurística de dados sensíveis.

TestClient + SQLite na cópia isolada. Inclui uma rota de sonda que levanta exceção; ela existe
apenas nesta execução (memória do processo), não é gravada no código da cópia nem no repositório.
"""
import datetime
import json
import os
import sys
import uuid

sys.stdout.reconfigure(encoding="utf-8")
ISO = r"C:\Users\roger\.claude\jobs\f5019419\tmp\iso-seg"
LOGS = r"C:\Users\roger\projetoAplicado7\.claude\worktrees\auditoria-2026-10-18\output\auditoria\2026-10-18T2018Z\evidencias\seg\logs"
banco = os.path.join(ISO, "tmp", "checagens.db")
if os.path.exists(banco):
    os.remove(banco)
os.environ["DATABASE_URL"] = "sqlite:///" + banco.replace("\\", "/")
for variavel in ("PUBLIC_DEMO", "DEMO_ACCESS_TOKEN", "RABBITMQ_URL"):
    os.environ.pop(variavel, None)
sys.path.insert(0, os.path.join(ISO, "src"))

from fastapi.testclient import TestClient  # noqa: E402
from archcorp.main import app  # noqa: E402
from archcorp.support.domain import contains_sensitive_data  # noqa: E402

R = {}
ADMIN = {"Authorization": "Bearer demo-admin"}


def sonda_erro():
    raise RuntimeError("erro sintético de sonda (E-SEG)")


rota = app.add_api_route("/__sonda_erro", sonda_erro, methods=["GET"], include_in_schema=False)
ultima = app.router.routes.pop()
app.router.routes.insert(0, ultima)


def registrar(nome, resp, marcador=None):
    tipo = resp.headers.get("content-type", "")
    chaves = None
    if "json" in tipo:
        try:
            corpo = resp.json()
            chaves = sorted(corpo.keys()) if isinstance(corpo, dict) else type(corpo).__name__
        except ValueError:
            chaves = "json inválido"
    entrada = {"status": resp.status_code, "content-type": tipo, "chaves": chaves,
               "vaza_traceback": ("Traceback" in resp.text or 'File "' in resp.text)}
    if marcador is not None:
        entrada["ecoa_entrada"] = marcador in resp.text
    R[nome] = entrada
    return resp


def corpo_reserva(cid, **campos):
    base = {"customerId": cid, "vehicleGroup": "SUV-COMPACTO", "protectionCode": "BASICA", "serviceCode": "RENTAL-FLEX",
            "startsOn": (datetime.date.today() + datetime.timedelta(days=30)).isoformat(),
            "endsOn": (datetime.date.today() + datetime.timedelta(days=33)).isoformat(),
            "amount": 750.0, "currency": "BRL", "billingCycle": "ONCE", "slaHours": 8}
    base.update(campos)
    return base


with TestClient(app, raise_server_exceptions=False) as c:
    registrar("401_sem_token", c.get("/api/v1/demo/state"))
    registrar("403_papel_errado", c.get("/api/v1/demo/state", headers={"Authorization": "Bearer demo-support"}))
    registrar("404_recurso", c.get(f"/api/v1/crm/customers/{uuid.uuid4()}", headers=ADMIN))
    registrar("405_metodo", c.patch("/health/live"))
    registrar("400_correlacao", c.get("/api/v1/demo/state", headers={**ADMIN, "X-Correlation-ID": "nao-uuid"}))
    email = f"dup-{uuid.uuid4().hex[:6]}@cliente-sintetico.example.com"
    criado = c.post("/api/v1/crm/customers", headers=ADMIN, json={"name": "Cliente Duplicado Sintético", "email": email})
    registrar("409_conflito", c.post("/api/v1/crm/customers", headers=ADMIN,
                                     json={"name": "Cliente Duplicado Sintético", "email": email}))
    marcador = "sintetico-marcador-" + uuid.uuid4().hex[:8]
    registrar("422_entrada_nao_ecoada", c.post("/api/v1/crm/customers", headers=ADMIN,
                                               json={"email": marcador, "token": marcador}), marcador)
    registrar("500_erro_nao_tratado", c.get("/__sonda_erro"))
    R["500_erro_nao_tratado"]["mensagem_original_ecoada"] = "erro sintético de sonda" in c.get("/__sonda_erro").text

    cliente = c.post("/api/v1/crm/customers", headers=ADMIN, json={
        "name": "Cliente Limites Sintético", "email": f"lim-{uuid.uuid4().hex[:6]}@cliente-sintetico.example.com"}).json()
    cid = cliente["customerId"]
    fake_contrato = str(uuid.uuid4())
    fake_fatura = str(uuid.uuid4())
    registrar("reserva_amount_zero", c.post("/api/v1/contracts/reservations", headers=ADMIN, json=corpo_reserva(cid, amount=0)))
    registrar("reserva_amount_1e20", c.post("/api/v1/contracts/reservations", headers=ADMIN, json=corpo_reserva(cid, amount=1e20)))
    registrar("draft_billing_amount_1e20", c.post("/api/v1/contracts/drafts", headers={**ADMIN, "Idempotency-Key": "lim-" + uuid.uuid4().hex[:8]},
                                                  json={"customerId": cid, "serviceCode": "RENTAL-FLEX",
                                                        "startsOn": (datetime.date.today() + datetime.timedelta(days=30)).isoformat(),
                                                        "billing": {"amount": 1e20, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8}))
    registrar("nome_1_caractere", c.post("/api/v1/crm/customers", headers=ADMIN, json={"name": "A", "email": f"n1-{uuid.uuid4().hex[:6]}@cliente-sintetico.example.com"}))
    registrar("nome_151_caracteres", c.post("/api/v1/crm/customers", headers=ADMIN, json={"name": "A" * 151, "email": f"n151-{uuid.uuid4().hex[:6]}@cliente-sintetico.example.com"}))
    registrar("nome_150_caracteres", c.post("/api/v1/crm/customers", headers=ADMIN, json={"name": "B" * 150, "email": f"n150-{uuid.uuid4().hex[:6]}@cliente-sintetico.example.com"}))
    registrar("email_invalido", c.post("/api/v1/crm/customers", headers=ADMIN, json={"name": "Cliente Sintético", "email": "x@"}))
    registrar("paginacao_limit_201", c.get("/api/v1/crm/customers", params={"limit": 201}, headers=ADMIN))
    registrar("paginacao_offset_negativo", c.get("/api/v1/crm/customers", params={"offset": -1}, headers=ADMIN))
    registrar("idempotency_key_101", c.post("/api/v1/contracts/drafts", headers={**ADMIN, "Idempotency-Key": "k" * 101},
                                            json={"customerId": cid, "serviceCode": "RENTAL-FLEX", "startsOn": "2027-01-04",
                                                  "billing": {"amount": 100, "currency": "BRL", "cycle": "MONTHLY"}}))
    registrar("chamado_descricao_2001", c.post("/api/v1/support/tickets", headers={**ADMIN, "Idempotency-Key": "d-" + uuid.uuid4().hex[:8]},
                                               json={"customerId": cid, "contractId": fake_contrato, "serviceCode": "RENTAL-FLEX",
                                                     "category": "OUTAGE", "description": "x" * 2001}))
    registrar("chamado_servico_5000_caracteres", c.post("/api/v1/support/tickets", headers={**ADMIN, "Idempotency-Key": "s-" + uuid.uuid4().hex[:8]},
                                                        json={"customerId": cid, "contractId": fake_contrato, "serviceCode": "S" * 5000,
                                                              "category": "OUTAGE", "description": "Relato sintético de teste"}))
    registrar("pagamento_amount_1e15", c.post(f"/api/v1/finance/invoices/{fake_fatura}/payments", headers=ADMIN,
                                              json={"amount": 1e15, "currency": "BRL", "reference": "SIM-LIMITE-1"}))
    registrar("pagamento_amount_0_001", c.post(f"/api/v1/finance/invoices/{fake_fatura}/payments", headers=ADMIN,
                                               json={"amount": 0.001, "currency": "BRL", "reference": "SIM-LIMITE-2"}))

casos = [
    ("CPF com pontos e traço", "Cliente informou CPF 000.000.000-00 no balcão", True),
    ("CPF sem separadores", "CPF 00000000000 informado", True),
    ("CNPJ sem separadores", "CNPJ 12345678000190 do cliente", True),
    ("cartão com espaços", "Cartão 4111 1111 1111 1111 recusado", True),
    ("telefone com DDD entre parênteses", "Ligar para (31) 99999-9999", True),
    ("telefone com DDI e espaços", "Ligar para +55 31 99999-9999", True),
    ("placa Mercosul", "Veículo placa ABC1D23 parado", True),
    ("placa no formato antigo", "Veículo placa ABC-1234 parado", True),
    ("e-mail", "Contato teste.sintetico@cliente-sintetico.example.com", True),
    ("nome de pessoa sem número", "Maria da Silva, gestora da frota", False),
    ("relato legítimo", "Pneu furado na rodovia km 12, aguardando guincho", False),
    ("SLA em horas", "SLA de 8 h para o grupo SUV", False),
]
R["heuristica_contains_sensitive_data"] = []
for nome, texto, esperado in casos:
    obtido = contains_sensitive_data(texto)
    R["heuristica_contains_sensitive_data"].append(
        {"caso": nome, "esperado_desejado": esperado, "obtido": obtido, "resultado": "ok" if obtido == esperado else "falha"})
with open(os.path.join(LOGS, "checagens_inprocesso.json"), "w", encoding="utf-8") as arq:
    json.dump(R, arq, ensure_ascii=False, indent=1)
for chave, valor in R.items():
    if chave != "heuristica_contains_sensitive_data":
        print(chave, "->", valor)
for item in R["heuristica_contains_sensitive_data"]:
    print("heuristica:", item["caso"], "| desejado", item["esperado_desejado"], "| obtido", item["obtido"], "|", item["resultado"])
