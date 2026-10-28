"""F-CFG, itens 1 e 2 do checklist: configuração (config.py) e guardas de inicialização (main.py).

Uso (PowerShell, com PY = venv-auditoria):
    PY -I exp_config.py <ISO> <LOGS>

Cada caso roda num subprocesso `python -I` separado, com cwd na cópia isolada (ou numa pasta
temporária dentro de <ISO>\\tmp) e SQLite dentro de <ISO>\\tmp\\exp_config. Nenhum PostgreSQL ou
RabbitMQ é usado: os casos de broker apontam para uma porta fechada (127.0.0.1:1).
Valores de token são sintéticos e aparecem só pelo comprimento; URLs têm a credencial redigida.
Saídas: <LOGS>\\exp_config.txt (legível) e <LOGS>\\exp_config.json (estruturada).
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ISO = Path(sys.argv[1]).resolve()
LOGS = Path(sys.argv[2]).resolve()
SRC = ISO / "src"
TMP = ISO / "tmp" / "exp_config"
CWD_ENV = TMP / "cwd_env"
CWD_ENV.mkdir(parents=True, exist_ok=True)
(CWD_ENV / ".env").write_text("RETRY_LIMIT=7\n", encoding="utf-8")

PREFIXOS = ("RETRY_LIMIT", "CRM_READER", "RABBITMQ_", "DATABASE_URL", "PUBLIC_DEMO",
            "DEMO_ACCESS_TOKEN", "FINANCE_ALLOW_FUTURE_AS_OF", "CONTRACT_ADAPTER", "PORT")
CLEAN = {k: v for k, v in os.environ.items() if not k.startswith(PREFIXOS)}
TOKEN_SINTETICO = "sintetico-" + "k" * 31          # 40 caracteres, sem prefixo demo-
TOKEN_CURTO = "curto-" + "k" * 4                    # 10 caracteres
TOKEN_DEMO_PREFIXO = "demo-" + "k" * 30             # prefixo demo-, 35 caracteres
TOKEN_DEMO_MAIUSCULO = "Demo-" + "k" * 30           # prefixo com maiúscula (o guard é sensível a caixa)
TOKEN_24_FRACO = "a" * 24                           # comprimento mínimo, sem entropia
AMQP_FECHADO = "amqp://guest:guest@127.0.0.1:1/%2F"  # porta fechada: nada escuta em 127.0.0.1:1


def db(nome: str) -> str:
    return "sqlite:///" + (TMP / f"{nome}.db").as_posix()


PREAMBULO = f"""
import sys, json, os, time
sys.path.insert(0, {str(SRC)!r})
def emit(obj):
    print('RESULTADO=' + json.dumps(obj, ensure_ascii=False, default=str))
def tentar(fn):
    try:
        r = fn()
        return {{'ok': True, **(r or {{}})}}
    except BaseException as exc:
        return {{'ok': False, 'excecao': type(exc).__name__, 'mensagem': str(exc)[:200]}}
def importar_main():
    from archcorp.config import settings
    import archcorp.main  # noqa: F401  (importa todos os módulos e monta o app)
    return {{'retry_limit': settings.retry_limit}}
def reader_test(usar_sleep_real=False):
    from archcorp.config import settings
    from archcorp.contracts.adapters import ResilientCustomerReader
    chamadas, esperas = [], []
    class Inner:
        def get(self, session, customer_id):
            chamadas.append(1)
            raise TimeoutError('simulado')
    leitor = ResilientCustomerReader(
        Inner(), timeout_seconds=settings.crm_reader_timeout_seconds,
        max_attempts=settings.crm_reader_max_attempts,
        base_delay_seconds=settings.crm_reader_base_delay_seconds,
        sleep=(time.sleep if usar_sleep_real else (lambda s: esperas.append(s))))
    try:
        leitor.get(None, 'x')
        erro = None
    except Exception as exc:
        erro = type(exc).__name__ + ': ' + str(exc)[:120]
    return {{'timeout': settings.crm_reader_timeout_seconds,
            'max_attempts': settings.crm_reader_max_attempts,
            'base_delay': settings.crm_reader_base_delay_seconds,
            'chamadas_ao_crm': len(chamadas), 'esperas': esperas, 'erro': erro}}
def startup():
    from fastapi.testclient import TestClient
    from archcorp.main import app
    tok = os.environ.get('DEMO_ACCESS_TOKEN')
    with TestClient(app) as client:
        res = {{'health_live': client.get('/health/live').status_code,
               'demo_state_sem_credencial': client.get('/api/v1/demo/state').status_code}}
        if tok:
            res['demo_state_com_token_configurado'] = client.get(
                '/api/v1/demo/state', headers={{'Authorization': 'Bearer ' + tok}}).status_code
        res['demo_state_com_demo_admin'] = client.get(
            '/api/v1/demo/state', headers={{'Authorization': 'Bearer demo-admin'}}).status_code
        return res
def publicar():
    from archcorp.config import settings
    from archcorp.integration.service import EventDispatcher
    t0 = time.monotonic()
    try:
        EventDispatcher._publish_broker({{'eventType': 'Teste.v1', 'eventId': 'x'}})
        erro = None
    except BaseException as exc:
        erro = type(exc).__name__ + ': ' + str(exc)[:160]
    return {{'socket_timeout': settings.rabbitmq_socket_timeout_seconds,
            'blocked_timeout': settings.rabbitmq_blocked_timeout_seconds,
            'heartbeat': settings.rabbitmq_heartbeat_seconds,
            'duracao_s': round(time.monotonic() - t0, 3), 'erro': erro}}
class Evento:
    def __init__(self):
        self.attempts = 0
        self.status = 'PENDING'
        self.last_error = None
def registro():
    from archcorp.config import settings
    from archcorp.integration.service import EventDispatcher
    e = Evento()
    EventDispatcher._register_failure(e)
    primeira = e.status
    EventDispatcher._register_failure(e)
    return {{'retry_limit': settings.retry_limit, 'status_apos_1a_falha': primeira,
            'status_apos_2a_falha': e.status, 'attempts': e.attempts}}
def mutar():
    from archcorp.config import settings
    from archcorp.integration.service import EventDispatcher
    settings.retry_limit = 'abc'
    e = Evento()
    try:
        EventDispatcher._register_failure(e)
        erro = None
    except Exception as exc:
        erro = type(exc).__name__ + ': ' + str(exc)[:120]
    return {{'atribuicao_aceita': settings.retry_limit == 'abc', 'erro_no_uso': erro}}
"""

# (id, descrição, variáveis extras, cwd, trecho executado)
CASOS = [
    ("A01", "RETRY_LIMIT=0 (importação de archcorp.main)", {"RETRY_LIMIT": "0", "DATABASE_URL": db("a01")}, ISO, "emit(tentar(importar_main))"),
    ("A02", "RETRY_LIMIT=-1 (importação)", {"RETRY_LIMIT": "-1", "DATABASE_URL": db("a02")}, ISO, "emit(tentar(importar_main))"),
    ("A03", "RETRY_LIMIT=abc (tipo inválido, controle)", {"RETRY_LIMIT": "abc", "DATABASE_URL": db("a03")}, ISO, "emit(tentar(importar_main))"),
    ("A04", "CRM_READER_MAX_ATTEMPTS=0 (importação)", {"CRM_READER_MAX_ATTEMPTS": "0", "DATABASE_URL": db("a04")}, ISO, "emit(tentar(importar_main))"),
    ("A05", "CRM_READER_TIMEOUT_SECONDS=-1 (execução do leitor, sleep simulado)", {"CRM_READER_TIMEOUT_SECONDS": "-1", "DATABASE_URL": db("a05")}, ISO, "emit(tentar(lambda: reader_test(False)))"),
    ("A06", "Controle: CRM_READER padrão (execução do leitor, sleep simulado)", {"DATABASE_URL": db("a06")}, ISO, "emit(tentar(lambda: reader_test(False)))"),
    ("A07", "CRM_READER_BASE_DELAY_SECONDS=-1 (execução, sleep real)", {"CRM_READER_BASE_DELAY_SECONDS": "-1", "DATABASE_URL": db("a07")}, ISO, "emit(tentar(lambda: reader_test(True)))"),
    ("A08", "DATABASE_URL sem esquema (importação)", {"DATABASE_URL": "nao-e-uma-url"}, ISO, "emit(tentar(importar_main))"),
    ("A09", "DATABASE_URL vazia (importação)", {"DATABASE_URL": ""}, ISO, "emit(tentar(importar_main))"),
    ("A10", "DATABASE_URL PostgreSQL inacessível (inicialização)", {"DATABASE_URL": "postgresql+psycopg://u:p@127.0.0.1:1/x"}, ISO, "emit(tentar(startup))"),
    ("A11", "DATABASE_URL SQLite em diretório inexistente (inicialização)", {"DATABASE_URL": "sqlite:///" + (TMP / "nao_existe" / "x.db").as_posix()}, ISO, "emit(tentar(startup))"),
    ("B01", "PUBLIC_DEMO=true sem token (inicialização)", {"PUBLIC_DEMO": "true", "DATABASE_URL": db("b01")}, ISO, "emit(tentar(startup))"),
    ("B02", "PUBLIC_DEMO=true, token de 10 caracteres", {"PUBLIC_DEMO": "true", "DEMO_ACCESS_TOKEN": TOKEN_CURTO, "DATABASE_URL": db("b02")}, ISO, "emit(tentar(startup))"),
    ("B03", "PUBLIC_DEMO=true, token com prefixo demo- (35 caracteres)", {"PUBLIC_DEMO": "true", "DEMO_ACCESS_TOKEN": TOKEN_DEMO_PREFIXO, "DATABASE_URL": db("b03")}, ISO, "emit(tentar(startup))"),
    ("B04", "PUBLIC_DEMO=true, token com prefixo 'Demo-' (maiúscula)", {"PUBLIC_DEMO": "true", "DEMO_ACCESS_TOKEN": TOKEN_DEMO_MAIUSCULO, "DATABASE_URL": db("b04")}, ISO, "emit(tentar(startup))"),
    ("B05", "PUBLIC_DEMO=true, token de 24 caracteres sem entropia", {"PUBLIC_DEMO": "true", "DEMO_ACCESS_TOKEN": TOKEN_24_FRACO, "DATABASE_URL": db("b05")}, ISO, "emit(tentar(startup))"),
    ("B06", "PUBLIC_DEMO=true + FINANCE_ALLOW_FUTURE_AS_OF=true, token válido", {"PUBLIC_DEMO": "true", "DEMO_ACCESS_TOKEN": TOKEN_SINTETICO, "FINANCE_ALLOW_FUTURE_AS_OF": "true", "DATABASE_URL": db("b06")}, ISO, "emit(tentar(startup))"),
    ("B07", "PUBLIC_DEMO=true, token válido, SQLite (inicialização e espião do RLS)", {"PUBLIC_DEMO": "true", "DEMO_ACCESS_TOKEN": TOKEN_SINTETICO, "DATABASE_URL": db("b07")}, ISO,
     "r = tentar(startup)\n"
     "def espiao():\n"
     "    from archcorp.infrastructure import db as bd\n"
     "    class Espiao:\n"
     "        chamadas = 0\n"
     "        def execute(self, *a, **k):\n"
     "            Espiao.chamadas += 1\n"
     "        def exec_driver_sql(self, *a, **k):\n"
     "            Espiao.chamadas += 1\n"
     "    bd.protect_public_demo_tables(Espiao())\n"
     "    return {'dialeto': bd.engine.dialect.name, 'chamadas_ao_banco_pelo_rls': Espiao.chamadas}\n"
     "r['rls'] = tentar(espiao)\n"
     "emit(r)"),
    ("B08", "PUBLIC_DEMO=false + FINANCE_ALLOW_FUTURE_AS_OF=true (modo local)", {"FINANCE_ALLOW_FUTURE_AS_OF": "true", "DATABASE_URL": db("b08")}, ISO, "emit(tentar(startup))"),
    ("B09", "Padrões (nenhuma variável de demo): inicialização e credencial demo-admin", {"DATABASE_URL": db("b09")}, ISO, "emit(tentar(startup))"),
    ("C01", "Broker em porta fechada, timeouts padrão (despacho)", {"RABBITMQ_URL": AMQP_FECHADO}, ISO, "emit(tentar(publicar))"),
    ("C02", "Broker em porta fechada, RABBITMQ_SOCKET_TIMEOUT_SECONDS=-1", {"RABBITMQ_URL": AMQP_FECHADO, "RABBITMQ_SOCKET_TIMEOUT_SECONDS": "-1"}, ISO, "emit(tentar(publicar))"),
    ("C03", "Broker em porta fechada, RABBITMQ_BLOCKED_TIMEOUT_SECONDS=-1", {"RABBITMQ_URL": AMQP_FECHADO, "RABBITMQ_BLOCKED_TIMEOUT_SECONDS": "-1"}, ISO, "emit(tentar(publicar))"),
    ("C04", "Broker em porta fechada, RABBITMQ_HEARTBEAT_SECONDS=-1", {"RABBITMQ_URL": AMQP_FECHADO, "RABBITMQ_HEARTBEAT_SECONDS": "-1"}, ISO, "emit(tentar(publicar))"),
    ("C05", "RETRY_LIMIT=0 (primeira falha do despacho)", {"RETRY_LIMIT": "0"}, ISO, "emit(tentar(registro))"),
    ("C06", "RETRY_LIMIT=-1 (primeira falha do despacho)", {"RETRY_LIMIT": "-1"}, ISO, "emit(tentar(registro))"),
    ("C07", "Controle: RETRY_LIMIT padrão (primeira falha do despacho)", {}, ISO, "emit(tentar(registro))"),
    ("C08", "Atribuição de texto a retry_limit em tempo de execução", {}, ISO, "emit(tentar(mutar))"),
    ("C09", ".env com RETRY_LIMIT=7, lido a partir do cwd que contém o .env", {}, CWD_ENV, "emit(tentar(importar_main))"),
    ("C10", ".env com RETRY_LIMIT=7 e variável de ambiente RETRY_LIMIT=9 no mesmo cwd", {"RETRY_LIMIT": "9"}, CWD_ENV, "emit(tentar(importar_main))"),
    ("C11", "Mesmo .env, a partir do cwd da cópia (sem .env)", {}, ISO, "emit(tentar(importar_main))"),
]


def redigir(env: dict) -> dict:
    saida = {}
    for chave, valor in env.items():
        if "TOKEN" in chave:
            saida[chave] = f"<sintetico, len={len(valor)}>"
        elif "://" in valor and "@" in valor:
            saida[chave] = re.sub(r"://[^@]*@", "://<REDACTED>@", valor)
        else:
            saida[chave] = valor
    return saida


def rodar(caso):
    cid, descricao, extra, cwd, trecho = caso
    env = dict(CLEAN)
    env.update(extra)
    codigo = PREAMBULO + "\n" + trecho + "\n"
    proc = subprocess.run([sys.executable, "-I", "-c", codigo], cwd=str(cwd), env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
    resultado = None
    for linha in proc.stdout.splitlines():
        if linha.startswith("RESULTADO="):
            resultado = json.loads(linha[len("RESULTADO="):])
    cauda = [linha for linha in proc.stderr.strip().splitlines()[-3:]]
    return {"id": cid, "descricao": descricao, "cwd": str(cwd), "env": redigir(extra), "exit": proc.returncode,
            "resultado": resultado, "stderr_cauda": cauda}


def main() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    resultados = [rodar(caso) for caso in CASOS]
    (LOGS / "exp_config.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    linhas = []
    for r in resultados:
        linhas.append(f"### {r['id']} - {r['descricao']}")
        linhas.append(f"cwd: {r['cwd']}")
        linhas.append(f"variaveis: {json.dumps(r['env'], ensure_ascii=False)}")
        linhas.append(f"exit: {r['exit']}")
        linhas.append(f"resultado: {json.dumps(r['resultado'], ensure_ascii=False)}")
        if r["stderr_cauda"]:
            linhas.append("stderr (ultimas linhas):")
            linhas.extend("  " + s for s in r["stderr_cauda"])
        linhas.append("")
    (LOGS / "exp_config.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"casos executados: {len(resultados)}; saidas em {LOGS}")


if __name__ == "__main__":
    main()
