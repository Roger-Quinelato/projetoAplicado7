# -*- coding: utf-8 -*-
"""F-SEG, E-10 e E-11 e itens 2 e 4: sondas HTTP contra o uvicorn da cópia isolada (porta 18101).

Uso: python seg_sondas_http.py local|publico
- local: cabeçalhos, CORS, Range, travessia de caminho, formatos de erro, /metrics, chamado com dado
  sensível e corpo grande.
- publico: docs públicos, token único, força bruta sem limite, cabeçalho não ASCII e /metrics.
Tokens são lidos de arquivos ou de constantes; nenhum valor de credencial é gravado no relatório.
"""
import datetime
import glob
import json
import os
import secrets
import socket
import sys
import time
import uuid

import httpx

sys.stdout.reconfigure(encoding="utf-8")
# Timeout de 120 s por requisição (o padrão de 5 s derrubou a sonda de cardinalidade em 1ª execução).
_originais = {nome: getattr(httpx, nome) for nome in ("get", "post", "options", "patch")}


def _com_timeout(nome):
    def chamada(*args, **kwargs):
        kwargs.setdefault("timeout", 120)
        return _originais[nome](*args, **kwargs)
    return chamada


for _nome in _originais:
    setattr(httpx, _nome, _com_timeout(_nome))
MODO = sys.argv[1] if len(sys.argv) > 1 else "local"
ISO = r"C:\Users\roger\.claude\jobs\f5019419\tmp\iso-seg"
LOGS = r"C:\Users\roger\projetoAplicado7\.claude\worktrees\auditoria-2026-10-18\output\auditoria\2026-10-18T2018Z\evidencias\seg\logs"
BASE = "http://127.0.0.1:18101"
PORTA = 18101
CABECALHOS_SEG = ["content-security-policy", "x-content-type-options", "x-frame-options",
                  "referrer-policy", "strict-transport-security", "permissions-policy"]
R = {"modo": MODO, "inicio_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
ADMIN = {"Authorization": "Bearer demo-admin"}
OPERACOES = {"Authorization": "Bearer demo-operations"}
SUPORTE = {"Authorization": "Bearer demo-support"}


def cru(bytes_req, limite=60):
    inicio = time.perf_counter()
    s = socket.create_connection(("127.0.0.1", PORTA), timeout=limite)
    s.sendall(bytes_req)
    dados = b""
    try:
        while True:
            parte = s.recv(65536)
            if not parte:
                break
            dados += parte
    except socket.timeout:
        pass
    finally:
        s.close()
    return dados, round(time.perf_counter() - inicio, 3)


def linha_status(dados):
    return dados.split(b"\r\n", 1)[0].decode("latin-1", "replace") if dados else ""


def corpo_de(dados):
    return dados.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in dados else b""


def resumo_problema(resp):
    tipo = resp.headers.get("content-type", "")
    chaves = None
    if "json" in tipo:
        try:
            corpo = resp.json()
            chaves = sorted(corpo.keys()) if isinstance(corpo, dict) else type(corpo).__name__
        except ValueError:
            chaves = "json inválido"
    return {"status": resp.status_code, "content-type": tipo, "chaves": chaves,
            "vaza_traceback": "Traceback" in resp.text or 'File "' in resp.text}


def sonda_local():
    r = httpx.get(BASE + "/")
    R["cabecalhos_pagina_inicial"] = {k: r.headers.get(k) for k in CABECALHOS_SEG + ["server", "content-type"]}
    r = httpx.get(BASE + "/health/live")
    R["cabecalhos_health"] = {k: r.headers.get(k) for k in CABECALHOS_SEG + ["server"]}
    r = httpx.options(BASE + "/api/v1/crm/customers",
                      headers={"Origin": "https://origem-externa.example", "Access-Control-Request-Method": "GET"})
    R["preflight_cors"] = {"status": r.status_code, "allow-origin": r.headers.get("access-control-allow-origin"),
                           "allow-methods": r.headers.get("access-control-allow-methods")}
    r = httpx.get(BASE + "/health/live", headers={"Origin": "https://origem-externa.example"})
    R["get_com_origin_externa"] = {"status": r.status_code, "allow-origin": r.headers.get("access-control-allow-origin")}

    arquivos = sorted(glob.glob(os.path.join(ISO, "web", "dist", "assets", "*.js")))
    url = BASE + "/assets/" + os.path.basename(arquivos[0])
    r = httpx.get(url, headers={"Range": "bytes=0-9"})
    R["range_simples"] = {"status": r.status_code, "content-range": r.headers.get("content-range"),
                          "tamanho_corpo": len(r.content)}
    R["range_multiplos"] = {}
    for n in (100, 1000, 3000):
        cabecalho = "bytes=" + ",".join(["0-0"] * n)
        inicio = time.perf_counter()
        r = httpx.get(url, headers={"Range": cabecalho}, timeout=120)
        R["range_multiplos"][str(n)] = {"status": r.status_code, "tamanho_corpo": len(r.content),
                                        "segundos": round(time.perf_counter() - inicio, 3),
                                        "bytes_cabecalho_range": len(cabecalho)}

    alvos = {
        "ponto_ponto_bruto": b"/assets/../../src/archcorp/config.py",
        "ponto_ponto_codificado": b"/assets/%2e%2e/%2e%2e/src/archcorp/config.py",
        "raiz_bruta": b"/../src/archcorp/config.py",
        "barra_codificada": b"/assets/..%2f..%2fsrc%2farchcorp%2fconfig.py",
    }
    R["travessia"] = {}
    for nome, caminho in alvos.items():
        dados, seg = cru(b"GET " + caminho + b" HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
        corpo = corpo_de(dados)
        R["travessia"][nome] = {"linha_status": linha_status(dados), "tamanho_corpo": len(corpo),
                                "vazou_config": (b"pydantic_settings" in corpo or b"class Settings" in corpo),
                                "segundos": seg}

    r = httpx.patch(BASE + "/health/live")
    R["erro_405"] = resumo_problema(r) | {"allow": r.headers.get("allow")}
    R["erro_404_api"] = resumo_problema(httpx.get(BASE + "/api/v1/nao-existe"))
    R["erro_400_correlacao"] = resumo_problema(httpx.get(BASE + "/api/v1/demo/state",
                                                         headers={**ADMIN, "X-Correlation-ID": "nao-uuid"}))
    R["erro_401"] = resumo_problema(httpx.get(BASE + "/api/v1/demo/state"))
    R["erro_403"] = resumo_problema(httpx.get(BASE + "/api/v1/demo/state", headers=SUPORTE))

    email_sintetico = "sonda-log@cliente-sintetico.example.com"
    R["lista_por_email_status"] = httpx.get(BASE + "/api/v1/crm/customers", params={"email": email_sintetico},
                                            headers=ADMIN).status_code
    R["metrics_sem_token"] = httpx.get(BASE + "/metrics").status_code
    antes = httpx.get(BASE + "/metrics", headers=OPERACOES).text
    series_antes = len([l for l in antes.splitlines() if l.startswith("archcorp_requests_total{")])
    for _ in range(300):
        httpx.get(f"{BASE}/api/v1/crm/customers/{uuid.uuid4()}", headers=ADMIN)
    depois = httpx.get(BASE + "/metrics", headers=OPERACOES).text
    series_depois = len([l for l in depois.splitlines() if l.startswith("archcorp_requests_total{")])
    R["metrics_cardinalidade"] = {"series_antes": series_antes, "series_depois_300_uuids": series_depois}

    sufixo = uuid.uuid4().hex[:8]
    cliente = httpx.post(BASE + "/api/v1/crm/customers", headers=ADMIN, json={
        "name": "Cliente Sintético Sonda", "email": f"sonda-{sufixo}@cliente-sintetico.example.com",
        "legacyId": "SONDA-" + sufixo}).json()
    cid = cliente["customerId"]
    inicio = (datetime.date.today() + datetime.timedelta(days=3)).isoformat()
    rascunho = httpx.post(BASE + "/api/v1/contracts/drafts",
                          headers={**ADMIN, "Idempotency-Key": "seg-rasc-" + sufixo},
                          json={"customerId": cid, "serviceCode": "RENTAL-FLEX", "startsOn": inicio,
                                "billing": {"amount": 500, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8})
    contrato = rascunho.json()["contractId"]
    ativacao = httpx.post(BASE + f"/api/v1/contracts/{contrato}/activate",
                          headers={**ADMIN, "Idempotency-Key": "seg-ativ-" + sufixo})
    descricao = ("Veículo sem partida. CPF 000.000.000-00; cartão 4111 1111 1111 1111; "
                 "fone +55 31 99999-9999; placa ABC1D23; contato teste.sintetico@cliente-sintetico.example.com")
    chamado = httpx.post(BASE + "/api/v1/support/tickets",
                         headers={**ADMIN, "Idempotency-Key": "seg-chamado-" + sufixo},
                         json={"customerId": cid, "contractId": contrato, "serviceCode": "RENTAL-FLEX",
                               "category": "OUTAGE", "description": descricao})
    R["chamado_dado_sensivel"] = {"ativacao_status": ativacao.status_code, "criacao_status": chamado.status_code}
    if chamado.status_code == 201:
        tid = chamado.json()["ticketId"]
        lido = httpx.get(BASE + f"/api/v1/support/tickets/{tid}", headers=SUPORTE)
        R["chamado_dado_sensivel"]["leitura_status"] = lido.status_code
        R["chamado_dado_sensivel"]["descricao_gravada_e_devolvida_igual"] = lido.json().get("description") == descricao
        R["chamado_dado_sensivel"]["ticket_sonda_id"] = tid
    R["chamado_dado_sensivel"]["sufixo_sonda"] = sufixo

    corpo_grande = {"name": "A" * (20 * 1024 * 1024)}
    inicio = time.perf_counter()
    r = httpx.post(BASE + "/api/v1/crm/customers", headers=ADMIN, json=corpo_grande, timeout=180)
    R["corpo_20mb"] = {"status": r.status_code, "segundos": round(time.perf_counter() - inicio, 3),
                       "content-type": r.headers.get("content-type")}


def sonda_publico():
    with open(os.path.join(ISO, "tmp", "seg_token_publico.txt"), encoding="ascii") as arq:
        token = arq.read().strip()
    R["docs_publicos"] = {c: httpx.get(BASE + c).status_code for c in ("/docs", "/redoc", "/openapi.json")}
    R["demo_state"] = {
        "sem_token": httpx.get(BASE + "/api/v1/demo/state").status_code,
        "demo_admin_local": httpx.get(BASE + "/api/v1/demo/state", headers=ADMIN).status_code,
        "token_publico": httpx.get(BASE + "/api/v1/demo/state", headers={"Authorization": f"Bearer {token}"}).status_code,
    }
    contagem = {}
    inicio = time.perf_counter()
    for _ in range(300):
        s = httpx.get(BASE + "/api/v1/demo/state",
                      headers={"Authorization": "Bearer " + secrets.token_hex(16)}).status_code
        contagem[str(s)] = contagem.get(str(s), 0) + 1
    R["forca_bruta_300_tentativas"] = {"contagem_status": contagem,
                                       "segundos": round(time.perf_counter() - inicio, 2)}
    R["apos_forca_bruta_token_valido"] = httpx.get(
        BASE + "/api/v1/demo/state", headers={"Authorization": f"Bearer {token}"}).status_code
    req_nao_ascii = (b"GET /api/v1/demo/state HTTP/1.1\r\nHost: 127.0.0.1\r\n"
                     b"Authorization: Bearer \xc3\xa7\xc3\xa3o-nao-ascii\r\nConnection: close\r\n\r\n")
    dados, seg = cru(req_nao_ascii)
    R["cabecalho_nao_ascii"] = {"linha_status": linha_status(dados), "segundos": seg,
                                "content-type": (dados.split(b"Content-Type: ", 1)[1].split(b"\r\n", 1)[0].decode("latin-1")
                                                 if b"Content-Type: " in dados else None),
                                "corpo_resumo": corpo_de(dados)[:160].decode("utf-8", "replace"),
                                "vaza_traceback": b"Traceback" in dados}
    req_ascii = (b"GET /api/v1/demo/state HTTP/1.1\r\nHost: 127.0.0.1\r\n"
                 b"Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123\r\nConnection: close\r\n\r\n")
    R["cabecalho_ascii_errado"] = linha_status(cru(req_ascii)[0])
    R["metrics_publico_sem_token"] = httpx.get(BASE + "/metrics").status_code
    R["metrics_publico_com_token"] = httpx.get(BASE + "/metrics",
                                               headers={"Authorization": f"Bearer {token}"}).status_code


if MODO == "local":
    sonda_local()
else:
    sonda_publico()
R["fim_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
with open(os.path.join(LOGS, f"sondas_{MODO}.json"), "w", encoding="utf-8") as arq:
    json.dump(R, arq, ensure_ascii=False, indent=1)
print(json.dumps(R, ensure_ascii=False, indent=1)[:6000])
