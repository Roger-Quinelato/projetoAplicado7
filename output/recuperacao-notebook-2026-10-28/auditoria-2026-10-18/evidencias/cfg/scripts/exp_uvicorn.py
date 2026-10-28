"""F-CFG, itens 1, 2 e 6: sobe o uvicorn real na porta 18104 da cópia isolada, consulta e encerra.

Uso (PowerShell, com PY = venv-auditoria):
    PY -I exp_uvicorn.py <ISO> <LOGS>

Cenários (um por vez, o mesmo processo é encerrado antes do próximo):
  dev_padrao              sem variáveis de demo (padrões do config.py)
  publico_token_curto     PUBLIC_DEMO=true com token de 10 caracteres (deve recusar a subida)
  publico_token_valido    PUBLIC_DEMO=true com token sintético de 40 caracteres, em SQLite

Somente leitura da API (GET). Sem Docker, sem PostgreSQL, sem RabbitMQ. O token sintético não é
gravado nas saídas. A porta 18104 é a da frente F-CFG.
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
TMP = ISO / "tmp" / "exp_uvicorn"
TMP.mkdir(parents=True, exist_ok=True)
PORTA = 18104
BASE = f"http://127.0.0.1:{PORTA}"
PREFIXOS = ("RETRY_LIMIT", "CRM_READER", "RABBITMQ_", "DATABASE_URL", "PUBLIC_DEMO",
            "DEMO_ACCESS_TOKEN", "FINANCE_ALLOW_FUTURE_AS_OF", "CONTRACT_ADAPTER", "PORT")
CLEAN = {k: v for k, v in os.environ.items() if not k.startswith(PREFIXOS)}
TOKEN_SINTETICO = "sintetico-" + "k" * 31


def db(nome: str) -> str:
    return "sqlite:///" + (TMP / f"{nome}.db").as_posix()


def porta_ocupada() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", PORTA), timeout=1):
            return True
    except OSError:
        return False


def pedir(caminho: str, token: str | None = None) -> int:
    cabecalhos = {"Authorization": f"Bearer {token}"} if token else {}
    req = urllib.request.Request(BASE + caminho, headers=cabecalhos, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def cenario(nome: str, env_extra: dict, consultas: list) -> dict:
    if porta_ocupada():
        raise SystemExit(f"porta {PORTA} ocupada antes do cenario {nome}; abortado")
    env = dict(CLEAN)
    env.update(env_extra)
    log = LOGS / f"uvicorn_18104_{nome}.txt"
    with open(log, "w", encoding="utf-8") as fh:
        processo = subprocess.Popen(
            [sys.executable, "-I", "-m", "uvicorn", "archcorp.main:app", "--app-dir", str(SRC),
             "--host", "127.0.0.1", "--port", str(PORTA)],
            cwd=str(ISO), env=env, stdout=fh, stderr=subprocess.STDOUT)
        resultado = {"cenario": nome, "subiu": False, "codigo_saida": None, "consultas": {}}
        inicio = time.monotonic()
        try:
            while time.monotonic() - inicio < 90:
                if processo.poll() is not None:
                    break
                try:
                    if pedir("/health/live") == 200:
                        resultado["subiu"] = True
                        resultado["segundos_ate_subir"] = round(time.monotonic() - inicio, 1)
                        break
                except OSError:
                    pass
                time.sleep(0.5)
            if resultado["subiu"]:
                for rotulo, caminho, token_chave in consultas:
                    if token_chave == "DEMO_ADMIN":
                        token = "demo-admin"
                    elif token_chave:
                        token = env.get(token_chave)
                    else:
                        token = None
                    resultado["consultas"][rotulo] = pedir(caminho, token)
        finally:
            if processo.poll() is None:
                processo.terminate()
                try:
                    processo.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    processo.kill()
                    processo.wait(timeout=15)
            resultado["codigo_saida"] = processo.returncode
    fim = time.monotonic()
    while porta_ocupada() and time.monotonic() - fim < 15:
        time.sleep(0.5)
    resultado["porta_liberada"] = not porta_ocupada()
    return resultado


CONSULTAS_DEV = [
    ("health_live", "/health/live", None),
    ("health_ready", "/health/ready", None),
    ("demo_state_sem_credencial", "/api/v1/demo/state", None),
    ("demo_state_demo_admin", "/api/v1/demo/state", "DEMO_ADMIN"),
    ("metrics_demo_admin", "/metrics", "DEMO_ADMIN"),
    ("openapi_json", "/openapi.json", None),
    ("docs", "/docs", None),
]
CONSULTAS_PUBLICO = [
    ("health_live", "/health/live", None),
    ("health_ready", "/health/ready", None),
    ("demo_state_sem_credencial", "/api/v1/demo/state", None),
    ("demo_state_com_token_configurado", "/api/v1/demo/state", "DEMO_ACCESS_TOKEN"),
    ("demo_state_demo_admin", "/api/v1/demo/state", "DEMO_ADMIN"),
    ("openapi_json", "/openapi.json", None),
]


def main() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    resultados = []
    resultados.append(cenario("dev_padrao", {"DATABASE_URL": db("uv_dev")}, CONSULTAS_DEV))
    resultados.append(cenario("publico_token_curto", {"PUBLIC_DEMO": "true", "DEMO_ACCESS_TOKEN": "curto-kkkk",
                                                       "DATABASE_URL": db("uv_curto")}, []))
    resultados.append(cenario("publico_token_valido", {"PUBLIC_DEMO": "true", "DEMO_ACCESS_TOKEN": TOKEN_SINTETICO,
                                                        "DATABASE_URL": db("uv_pub")}, CONSULTAS_PUBLICO))
    (LOGS / "uvicorn_18104.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for r in resultados:
        print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
