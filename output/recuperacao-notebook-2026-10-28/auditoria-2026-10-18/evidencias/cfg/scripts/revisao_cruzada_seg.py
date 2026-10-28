"""F-CFG, revisão cruzada da F-SEG: reexecução barata, em SQLite, dos achados médios.

Uso (PowerShell, com PY = venv-auditoria):
    PY -I revisao_cruzada_seg.py <ISO> <LOGS>

Cada caso roda num subprocesso `python -I` separado, com cwd na cópia isolada (iso-cfg) e SQLite
dentro de <ISO>\\tmp\\revisao_seg. Não usa Docker, PostgreSQL, RabbitMQ, npm ci nem instalação.
Não lê os logs da F-SEG: tudo é reexecutado aqui. Tokens são sintéticos (só o comprimento aparece).
O caso de cabeçalhos (SEG-07) sobe um uvicorn na porta 18104 e o encerra ao final.
Saídas: <LOGS>\\revisao_seg.json (estruturada) e <LOGS>\\revisao_seg.txt (legível).
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ISO = Path(sys.argv[1]).resolve()
LOGS = Path(sys.argv[2]).resolve()
SRC = ISO / "src"
TMP = ISO / "tmp" / "revisao_seg"
TMP.mkdir(parents=True, exist_ok=True)
PORTA = 18104
PREFIXOS = ("RETRY_LIMIT", "CRM_READER", "RABBITMQ_", "DATABASE_URL", "PUBLIC_DEMO",
            "DEMO_ACCESS_TOKEN", "FINANCE_ALLOW_FUTURE_AS_OF", "CONTRACT_ADAPTER", "PORT")
CLEAN = {k: v for k, v in os.environ.items() if not k.startswith(PREFIXOS)}
TOKEN = "sintetico-" + "k" * 31  # 40 caracteres, sem prefixo demo-


def db(nome: str) -> str:
    return "sqlite:///" + (TMP / f"{nome}.db").as_posix()


PREAMBULO = f"""
import sys, json, os, re, time
sys.path.insert(0, {str(SRC)!r})
def emit(obj):
    print('RESULTADO=' + json.dumps(obj, ensure_ascii=False, default=str))
"""

# ------------------------------------------------------------------ SEG-01 (modo público)
CASO_SEG01 = r"""
from fastapi.testclient import TestClient
from fastapi.routing import APIRoute
from archcorp.main import app
tok = os.environ['DEMO_ACCESS_TOKEN']
res = {}
def h(t):
    return {'Authorization': 'Bearer ' + t}
with TestClient(app) as c:
    res['finance_invoices_com_token_publico'] = c.get('/api/v1/finance/invoices', headers=h(tok)).status_code
    res['support_tickets_com_token_publico'] = c.get('/api/v1/support/tickets', headers=h(tok)).status_code
    res['demo_state_com_demo_finance_no_modo_publico'] = c.get('/api/v1/demo/state', headers=h('demo-finance')).status_code
    res['demo_state_com_demo_admin_no_modo_publico'] = c.get('/api/v1/demo/state', headers=h('demo-admin')).status_code
    codigos = []
    inicio = time.monotonic()
    for i in range(300):
        codigos.append(c.get('/api/v1/demo/state', headers=h('x' * 40 + str(i))).status_code)
    res['forca_bruta_300_erros'] = {
        'tentativas': len(codigos),
        'por_status': {str(s): codigos.count(s) for s in sorted(set(codigos))},
        'segundos': round(time.monotonic() - inicio, 2),
    }
    res['token_valido_apos_300_erros'] = c.get('/api/v1/demo/state', headers=h(tok)).status_code
    protegidas, acessiveis, sem_401 = 0, 0, []
    for rota in app.routes:
        if not isinstance(rota, APIRoute):
            continue
        for metodo in sorted(rota.methods - {'HEAD', 'OPTIONS'}):
            caminho = re.sub(r'\{[^}]+\}', '00000000-0000-4000-8000-000000000000', rota.path)
            if c.request(metodo, caminho).status_code != 401:
                sem_401.append(metodo + ' ' + rota.path)
                continue
            protegidas += 1
            if c.request(metodo, caminho, headers=h(tok)).status_code not in (401, 403):
                acessiveis += 1
    res['matriz_modo_publico'] = {
        'rotas_protegidas_por_401_sem_credencial': protegidas,
        'acessiveis_com_o_token_publico': acessiveis,
        'rotas_sem_401_sem_credencial': sem_401,
    }
emit(res)
"""

# ------------------------------------------------------------------ SEG-02 (chamado com dado sensível)
CASO_SEG02 = r"""
from fastapi.testclient import TestClient
from archcorp.main import app
from archcorp.support.domain import contains_sensitive_data
H = {'Authorization': 'Bearer demo-admin', 'X-Correlation-ID': '11111111-1111-4111-8111-111111111111'}
res = {}
with TestClient(app) as c:
    cliente = c.post('/api/v1/crm/customers', headers=H,
                     json={'name': 'Empresa Revisao', 'email': 'revisao@example.com', 'legacyId': 'REV-1'}).json()
    contrato = c.post('/api/v1/contracts/drafts', headers={**H, 'Idempotency-Key': 'rev-draft-1'}, json={
        'customerId': cliente['customerId'], 'serviceCode': 'RENTAL-FLEX', 'startsOn': '2026-10-01',
        'billing': {'amount': 2500, 'currency': 'BRL', 'cycle': 'MONTHLY'}, 'slaHours': 8}).json()
    res['ativacao_contrato'] = c.post(f"/api/v1/contracts/{contrato['contractId']}/activate",
                                      headers={**H, 'Idempotency-Key': 'rev-activate'}).status_code
    descricoes = {
        'cpf_com_pontos': 'Cliente informou CPF 123.456.789-09 no balcão',
        'cartao_teste': 'Cartão 4111 1111 1111 1111 recusado',
        'telefone_com_parenteses': 'Ligar para (31) 99999-9999 para retirar',
        'telefone_com_mais55': 'Ligar para +55 31 99999-9999',
        'placa': 'Veículo placa ABC1D23 parado',
        'email': 'Contato gestor@cliente.com.br',
    }
    chamados = {}
    for indice, (rotulo, texto) in enumerate(descricoes.items()):
        corpo = {'customerId': cliente['customerId'], 'contractId': contrato['contractId'],
                 'serviceCode': 'RENTAL-FLEX', 'category': 'OUTAGE', 'description': texto}
        resposta = c.post('/api/v1/support/tickets', headers={**H, 'Idempotency-Key': f'rev-ticket-{indice}'}, json=corpo)
        item = {'status_abertura': resposta.status_code}
        if resposta.status_code == 201:
            ticket = resposta.json()['ticketId']
            leitura = c.get(f'/api/v1/support/tickets/{ticket}', headers=H)
            dados = leitura.json()
            item['status_leitura'] = leitura.status_code
            item['chaves_da_leitura'] = sorted(dados.keys()) if isinstance(dados, dict) else None
            item['descricao_devolvida_igual'] = (dados.get('description') == texto) if isinstance(dados, dict) else None
        chamados[rotulo] = item
    res['chamados'] = chamados
    res['heuristica_contains_sensitive_data'] = {rotulo: contains_sensitive_data(texto) for rotulo, texto in descricoes.items()}
emit(res)
"""

# ------------------------------------------------------------------ SEG-06 (padrão sem PUBLIC_DEMO)
CASO_SEG06 = r"""
from fastapi.testclient import TestClient
from archcorp.config import settings
from archcorp.main import app
res = {'public_demo_padrao': settings.public_demo}
with TestClient(app) as c:
    res['demo_state_sem_credencial'] = c.get('/api/v1/demo/state').status_code
    res['demo_state_com_demo_admin'] = c.get('/api/v1/demo/state', headers={'Authorization': 'Bearer demo-admin'}).status_code
    res['demo_state_com_demo_support'] = c.get('/api/v1/demo/state', headers={'Authorization': 'Bearer demo-support'}).status_code
emit(res)
"""

# ------------------------------------------------------------------ SEG-11 (tabelas fora da proteção)
CASO_SEG11 = r"""
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from archcorp.main import app
from archcorp.infrastructure.db import Base, engine
with TestClient(app):
    pass
no_banco = set(inspect(engine).get_table_names())
nos_modelos = {t.name for t in Base.metadata.sorted_tables}
emit({
    'dialeto': engine.dialect.name,
    'tabelas_no_banco_apos_migracao': len(no_banco),
    'tabelas_dos_modelos': len(nos_modelos),
    'fora_do_laco_de_Base_metadata': sorted(no_banco - nos_modelos),
})
"""

# ------------------------------------------------------------------ SEG-15 (limites de entrada)
CASO_SEG15 = r"""
from fastapi.testclient import TestClient
from archcorp.main import app
from archcorp.support.schemas import TicketCreate
from archcorp.contracts.schemas import Billing
from archcorp.contracts.routes import ReservationInput
from uuid import uuid4
from pydantic import ValidationError
res = {}
def aceita(fabrica):
    try:
        fabrica()
        return True
    except ValidationError as exc:
        return 'recusado: ' + exc.errors()[0]['type']
res['schema_ticket_serviceCode_5000'] = aceita(lambda: TicketCreate(
    customerId=uuid4(), contractId=uuid4(), serviceCode='A' * 5000, category='OUTAGE', description='relato de teste'))
res['schema_billing_amount_1e20'] = aceita(lambda: Billing(amount=1e20, currency='BRL', cycle='MONTHLY'))
res['schema_reserva_amount_1e20'] = aceita(lambda: ReservationInput(
    customerId=uuid4(), vehicleGroup='SUV', protectionCode='BASIC', serviceCode='RENTAL-FLEX',
    startsOn='2026-12-01', endsOn='2026-12-05', amount=1e20))
H = {'Authorization': 'Bearer demo-admin', 'X-Correlation-ID': '11111111-1111-4111-8111-111111111111'}
with TestClient(app) as c:
    cliente = c.post('/api/v1/crm/customers', headers=H,
                     json={'name': 'Empresa Limites', 'email': 'limites@example.com', 'legacyId': 'LIM-1'}).json()
    rascunho = c.post('/api/v1/contracts/drafts', headers={**H, 'Idempotency-Key': 'lim-draft-1'}, json={
        'customerId': cliente['customerId'], 'serviceCode': 'RENTAL-FLEX', 'startsOn': '2026-10-01',
        'billing': {'amount': 1e20, 'currency': 'BRL', 'cycle': 'MONTHLY'}, 'slaHours': 8})
    res['api_rascunho_amount_1e20_status'] = rascunho.status_code
    reserva = c.post('/api/v1/contracts/reservations', headers={**H, 'Idempotency-Key': 'lim-res-1'}, json={
        'customerId': cliente['customerId'], 'vehicleGroup': 'SUV', 'protectionCode': 'BASIC', 'serviceCode': 'RENTAL-FLEX',
        'startsOn': '2026-12-01', 'endsOn': '2026-12-05', 'amount': 1e20, 'currency': 'BRL', 'billingCycle': 'MONTHLY', 'slaHours': 8})
    res['api_reserva_amount_1e20_status'] = reserva.status_code
    contrato = rascunho.json() if rascunho.status_code == 201 else None
    if contrato is None:
        contrato = c.post('/api/v1/contracts/drafts', headers={**H, 'Idempotency-Key': 'lim-draft-2'}, json={
            'customerId': cliente['customerId'], 'serviceCode': 'RENTAL-FLEX', 'startsOn': '2026-10-01',
            'billing': {'amount': 2500, 'currency': 'BRL', 'cycle': 'MONTHLY'}, 'slaHours': 8}).json()
    c.post(f"/api/v1/contracts/{contrato['contractId']}/activate", headers={**H, 'Idempotency-Key': 'lim-activate'})
    chamado = c.post('/api/v1/support/tickets', headers={**H, 'Idempotency-Key': 'lim-ticket-1'}, json={
        'customerId': cliente['customerId'], 'contractId': contrato['contractId'], 'serviceCode': 'A' * 5000,
        'category': 'OUTAGE', 'description': 'relato de teste'})
    corpo = chamado.json()
    res['api_chamado_serviceCode_5000_status'] = chamado.status_code
    res['api_chamado_serviceCode_5000_codigo'] = corpo.get('code') if isinstance(corpo, dict) else None
emit(res)
"""

CASOS = [
    ("seg01_modo_publico", {"PUBLIC_DEMO": "true", "DEMO_ACCESS_TOKEN": TOKEN, "DATABASE_URL": db("seg01")}, CASO_SEG01),
    ("seg02_chamado", {"DATABASE_URL": db("seg02")}, CASO_SEG02),
    ("seg06_padrao", {"DATABASE_URL": db("seg06")}, CASO_SEG06),
    ("seg11_tabelas", {"DATABASE_URL": db("seg11")}, CASO_SEG11),
    ("seg15_limites", {"DATABASE_URL": db("seg15")}, CASO_SEG15),
]


def rodar(nome: str, extra: dict, codigo: str) -> dict:
    env = dict(CLEAN)
    env.update(extra)
    proc = subprocess.run([sys.executable, "-I", "-c", PREAMBULO + codigo], cwd=str(ISO), env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    resultado = None
    for linha in proc.stdout.splitlines():
        if linha.startswith("RESULTADO="):
            resultado = json.loads(linha[len("RESULTADO="):])
    return {"caso": nome, "exit": proc.returncode, "resultado": resultado,
            "stderr_cauda": proc.stderr.strip().splitlines()[-3:]}


def porta_ocupada() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", PORTA), timeout=1):
            return True
    except OSError:
        return False


def cabecalhos_uvicorn() -> dict:
    """SEG-07: sobe o uvicorn em dev (SQLite), lê cabeçalhos reais e encerra."""
    if porta_ocupada():
        return {"erro": f"porta {PORTA} ocupada"}
    env = dict(CLEAN)
    env["DATABASE_URL"] = db("seg07")
    log = LOGS / "revisao_seg_uvicorn_18104.txt"
    with open(log, "w", encoding="utf-8") as fh:
        proc = subprocess.Popen([sys.executable, "-I", "-m", "uvicorn", "archcorp.main:app", "--app-dir", str(SRC),
                                 "--host", "127.0.0.1", "--port", str(PORTA)],
                                cwd=str(ISO), env=env, stdout=fh, stderr=subprocess.STDOUT)
    saida = {}
    try:
        inicio = time.monotonic()
        while time.monotonic() - inicio < 90:
            if proc.poll() is not None:
                break
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORTA}/health/live", timeout=5) as r:
                    if r.status == 200:
                        break
            except OSError:
                time.sleep(0.5)
        for caminho in ["/health/live", "/api/v1/demo/state"]:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORTA}{caminho}", timeout=10) as r:
                    saida[caminho] = {"status": r.status, "cabecalhos": dict(r.headers.items())}
            except urllib.error.HTTPError as exc:
                saida[caminho] = {"status": exc.code, "cabecalhos": dict(exc.headers.items())}
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=15)
    fim = time.monotonic()
    while porta_ocupada() and time.monotonic() - fim < 15:
        time.sleep(0.5)
    saida["porta_liberada"] = not porta_ocupada()
    return saida


def main() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    resultados = [rodar(nome, extra, codigo) for nome, extra, codigo in CASOS]
    resultados.append({"caso": "seg07_cabecalhos_uvicorn", "resultado": cabecalhos_uvicorn()})
    (LOGS / "revisao_seg.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    linhas = []
    for item in resultados:
        linhas.append(f"### {item['caso']}")
        linhas.append(json.dumps(item.get("resultado"), ensure_ascii=False, indent=1))
        if item.get("stderr_cauda"):
            linhas.append("stderr (ultimas linhas): " + " | ".join(item["stderr_cauda"])[:500])
        linhas.append("")
    (LOGS / "revisao_seg.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"casos: {len(resultados)}; saidas em {LOGS}")


if __name__ == "__main__":
    main()
