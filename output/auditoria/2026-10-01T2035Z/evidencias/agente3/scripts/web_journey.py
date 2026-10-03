"""Jornada real no frontend compilado (web/dist) servido pelo FastAPI (Agente 3).
Uso: python web_journey.py <base_url> <pg_dsn>"""
import json
import sys
import uuid

import psycopg
from playwright.sync_api import sync_playwright

BASE, DSN = sys.argv[1], sys.argv[2]
A = "/tmp/claude-0/-home-user-projetoAplicado7/ec00d59b-c354-5d1f-b4d6-080b88ac1d06/scratchpad/agente3"
SHOTS = f"{A}/shots"
AXE = f"{A}/axe/node_modules/axe-core/axe.min.js"
log = []


def note(msg):
    print(msg)
    log.append(msg)


def db(sql, *args):
    with psycopg.connect(DSN) as conn:
        return conn.execute(sql, args).fetchall()


def axe(page, label):
    page.add_script_tag(path=AXE)
    res = page.evaluate("async () => { const r = await axe.run(document, {resultTypes:['violations']}); return r.violations.map(v => ({id:v.id, impact:v.impact, n:v.nodes.length, help:v.help, sample: v.nodes.slice(0,2).map(n=>n.target.join(' '))})) }")
    note(f"AXE[{label}] violações={len(res)}")
    for v in res:
        note(f"   - {v['id']} ({v['impact']}) nós={v['n']}: {v['help']} ex={v['sample']}")
    return res


def notice(page):
    loc = page.locator(".notice, .alert")
    return loc.first.inner_text(timeout=3000).replace("\n", " ") if loc.count() else "(sem aviso)"


email = f"jornada-{uuid.uuid4().hex[:6]}@example.com"
with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1366, "height": 900})
    page = ctx.new_page()
    reqs = []
    page.on("request", lambda r: reqs.append((r.method, r.url.replace(BASE, ""), r.headers.get("idempotency-key"))) if "/api/" in r.url and r.method != "GET" else None)
    console = []
    page.on("console", lambda m: console.append(f"{m.type}: {m.text}"))

    page.goto(BASE + "/", wait_until="networkidle")
    page.screenshot(path=f"{SHOTS}/01_gate.png", full_page=True)
    note(f"01 título={page.title()!r} gate_visível={page.locator('.gate').count() == 1}")
    axe(page, "gate")

    # token inválido
    page.fill("input[type=password]", "token-errado")
    page.click("text=Acessar demonstração")
    page.wait_for_timeout(1200)
    page.screenshot(path=f"{SHOTS}/02_token_errado.png", full_page=True)
    note(f"02 token errado -> aviso={notice(page)!r}; ainda no gate={page.locator('.gate').count() == 1}")
    stored = page.evaluate("sessionStorage.getItem('archcorp-demo-token')")
    note(f"02b token inválido persistido em sessionStorage={stored is not None}")

    # token sem permissão (papel support) -> painel carrega?
    page.fill("input[type=password]", "demo-support")
    page.click("text=Acessar demonstração")
    page.wait_for_timeout(1200)
    note(f"03 token demo-support -> aviso={notice(page)!r}; gate={page.locator('.gate').count() == 1}")
    page.screenshot(path=f"{SHOTS}/03_token_support.png", full_page=True)

    # token admin
    page.fill("input[type=password]", "demo-admin")
    page.click("text=Acessar demonstração")
    page.wait_for_selector(".shell", timeout=8000)
    page.screenshot(path=f"{SHOTS}/04_painel.png", full_page=True)
    note("04 painel carregado com demo-admin")
    axe(page, "painel-visao-geral")

    # CRM: criar cliente
    page.click("nav >> text=CRM")
    page.fill("form >> nth=0 >> input[name=name]", "Cliente Jornada Sintetica")
    page.fill("form >> nth=0 >> input[name=email]", email)
    page.click("text=Cadastrar cliente")
    page.wait_for_timeout(1200)
    note(f"05 criar cliente -> aviso={notice(page)!r}; na tabela={page.locator('td', has_text=email).count() > 0}")
    page.screenshot(path=f"{SHOTS}/05_crm_cliente.png", full_page=True)
    axe(page, "crm")

    # CRM: e-mail duplicado -> mensagem de erro e preservação do formulário
    page.fill("form >> nth=0 >> input[name=name]", "Cliente Duplicado")
    page.fill("form >> nth=0 >> input[name=email]", email)
    page.click("text=Cadastrar cliente")
    page.wait_for_timeout(1200)
    kept = page.input_value("form >> nth=0 >> input[name=name]")
    note(f"06 e-mail duplicado -> aviso={notice(page)!r}; campo nome preservado após erro={kept!r}")
    page.screenshot(path=f"{SHOTS}/06_crm_duplicado.png", full_page=True)

    # Reservas
    page.click("nav >> text=Reservas e contratos")
    form = page.locator("form").first
    form.locator("select[name=customerId]").select_option(label="Cliente Jornada Sintetica")
    form.locator("input[name=startsOn]").fill("2027-04-01")
    form.locator("input[name=endsOn]").fill("2027-04-05")
    form.locator("input[name=amount]").fill("450.00")
    form.locator("button[type=submit]").dblclick()
    page.wait_for_timeout(1500)
    cust = db("SELECT customer_id FROM crm_customers WHERE email=%s", email)[0][0]
    nres = db("SELECT count(*) FROM contracts_reservations WHERE customer_id=%s", cust)[0][0]
    note(f"07 reserva (duplo clique no submit) -> aviso={notice(page)!r}; reservas no banco={nres}")
    page.screenshot(path=f"{SHOTS}/07_reserva.png", full_page=True)

    # Gerar contrato (duplo clique)
    page.locator("button", has_text="Gerar contrato").first.dblclick()
    page.wait_for_timeout(1500)
    ncon = db("SELECT count(*) FROM contracts_contracts WHERE customer_id=%s", cust)[0][0]
    note(f"08 gerar contrato (duplo clique) -> aviso={notice(page)!r}; contratos={ncon}")
    # Ativar (duplo clique)
    page.locator("button", has_text="Ativar").first.dblclick()
    page.wait_for_timeout(2000)
    cid = db("SELECT contract_id, status FROM contracts_contracts WHERE customer_id=%s", cust)
    nev = db("SELECT count(*) FROM integration_outbox WHERE event_type='ContractActivated.v1' AND payload->>'contractId'=%s", cid[0][0])[0][0]
    note(f"09 ativar (duplo clique) -> aviso={notice(page)!r}; contrato={cid[0][1]}; eventos ContractActivated={nev}")
    page.screenshot(path=f"{SHOTS}/08_contrato_ativo.png", full_page=True)

    # Despachar
    page.click("nav >> text=Visão geral")
    page.click("text=Despachar eventos pendentes")
    page.wait_for_timeout(1500)
    note(f"10 despacho -> aviso={notice(page)!r}")
    page.screenshot(path=f"{SHOTS}/09_despacho.png", full_page=True)

    page.click("nav >> text=Financeiro")
    page.wait_for_timeout(500)
    ninv = db("SELECT count(*) FROM finance_invoices WHERE contract_id=%s", cid[0][0])[0][0]
    note(f"11 financeiro -> faturas do contrato no banco={ninv}; linhas na tabela={page.locator('table >> tbody tr').count()}")
    page.screenshot(path=f"{SHOTS}/10_financeiro.png", full_page=True)
    axe(page, "financeiro")

    page.click("nav >> text=Workflow")
    page.wait_for_timeout(500)
    nproc = db("SELECT count(*) FROM workflow_instances WHERE reference_id=%s", cid[0][0])[0][0]
    note(f"12 workflow -> processos do contrato={nproc}; tabela processos={page.locator('table').first.locator('tbody tr').count()}")
    page.screenshot(path=f"{SHOTS}/11_workflow.png", full_page=True)

    # Atendimento com validação mínima (descrição curta -> 422)
    page.click("nav >> text=Atendimento")
    f = page.locator("form").first
    f.locator("select[name=customerId]").select_option(label="Cliente Jornada Sintetica")
    f.locator("select[name=contractId]").select_option(index=1)
    f.locator("select[name=category]").select_option("OUTAGE")
    f.locator("input[name=description]").fill("ab")
    f.locator("button[type=submit]").click()
    page.wait_for_timeout(1200)
    note(f"13 chamado com descrição curta -> aviso={notice(page)!r}")
    page.screenshot(path=f"{SHOTS}/12_atendimento_erro.png", full_page=True)
    axe(page, "atendimento")

    # Viewport móvel
    m = browser.new_context(viewport={"width": 390, "height": 844})
    mp = m.new_page()
    mp.goto(BASE + "/")
    mp.evaluate("sessionStorage.setItem('archcorp-demo-token','demo-admin')")
    mp.reload(wait_until="networkidle")
    mp.screenshot(path=f"{SHOTS}/13_mobile.png", full_page=True)
    sw = mp.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    note(f"14 viewport 390px -> scrollWidth/innerWidth={sw}")

    note("REQ mutáveis (método, caminho, Idempotency-Key presente):")
    for r in reqs:
        note(f"   {r[0]} {r[1]} key={'sim' if r[2] else 'não'}{' ' + r[2][:8] if r[2] else ''}")
    note(f"CONSOLE: {console[:8]}")
    browser.close()
json.dump(log, open(f"{A}/logs/web_journey.json", "w"), ensure_ascii=False, indent=1)
