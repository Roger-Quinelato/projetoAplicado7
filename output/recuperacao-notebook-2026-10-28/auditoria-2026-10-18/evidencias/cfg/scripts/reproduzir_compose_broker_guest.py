"""F-CFG, CFG-05 (roteiro pronto, NÃO EXECUTADO nesta auditoria): o serviço api do Compose
consegue publicar no RabbitMQ usando o usuário padrão `guest`?

Status: não executado. Exige Docker, e a decisão do usuário (18/10/2026) proíbe usar Docker nesta
auditoria. Rodar somente numa máquina com Docker, para confirmar CFG-05 (de confiança média para alta).

Uso (em outra máquina, com Docker; a partir de uma cópia do repositório, nunca do worktree):
    python reproduzir_compose_broker_guest.py <CÓPIA_DO_REPO> <LOGS>

Passos:
  1. Lê docker-compose.yml da cópia e obtém a URL do broker do serviço api (sem imprimir a credencial).
  2. Sobe postgres e rabbitmq com um nome de projeto próprio (archcorp-cfg-audit) e o api.
  3. Dentro do contêiner api, tenta abrir conexão AMQP com a mesma URL e registra a exceção.
  4. Lê o log do rabbitmq e procura a recusa "can only connect via localhost" (documentação oficial).
  5. Do host, consulta a API de gerenciamento em 127.0.0.1:15672 com as mesmas credenciais
     (esperado: 401 se a recusa por loopback também ocorrer no painel).
  6. Encerra e remove os volumes do projeto (docker compose down -v).
Critério: se o passo 3 terminar com ACCESS_REFUSED / ProbableAuthenticationError, CFG-05 é confirmado.
Se conectar, CFG-05 é refutado e deve ser rebaixado ou removido.
"""
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import base64

import yaml

COPIA = Path(sys.argv[1]).resolve()
LOGS = Path(sys.argv[2]).resolve()
PROJETO = "archcorp-cfg-audit"
linhas = []


def p(texto: str = "") -> None:
    linhas.append(texto)


def redigir(texto: str) -> str:
    return re.sub(r"://[^@\s]+@", "://<REDACTED>@", texto)


def compose(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "compose", "-p", PROJETO, "-f", str(COPIA / "docker-compose.yml"), *args],
                          cwd=str(COPIA), capture_output=True, text=True, encoding="utf-8", errors="replace")


compose_yml = yaml.safe_load((COPIA / "docker-compose.yml").read_text(encoding="utf-8"))
ambiente_api = compose_yml["services"]["api"]["environment"]
url = ambiente_api["RABBITMQ_URL"]
usuario, senha = re.match(r"^[a-z+]+://([^:]+):([^@]+)@", url).groups()
p(f"RABBITMQ_URL do api (credencial redigida): {redigir(url)}")

subida = compose("up", "-d", "--wait", "postgres", "rabbitmq", "api")
p(f"up exit={subida.returncode}")
if subida.returncode == 0:
    teste = (
        "import os, pika\n"
        "p = pika.URLParameters(os.environ['RABBITMQ_URL'])\n"
        "try:\n"
        "    pika.BlockingConnection(p)\n"
        "    print('CONECTOU')\n"
        "except Exception as exc:\n"
        "    print('FALHOU', type(exc).__name__, str(exc)[:200])\n"
    )
    res = subprocess.run(["docker", "compose", "-p", PROJETO, "-f", str(COPIA / "docker-compose.yml"), "exec", "-T", "api",
                          "python", "-c", teste], cwd=str(COPIA), capture_output=True, text=True, encoding="utf-8", errors="replace")
    p(f"passo 3 (conexao do api ao broker): {redigir(res.stdout.strip() or res.stderr.strip())[:400]}")
    logs = compose("logs", "rabbitmq")
    achados = [l for l in logs.stdout.splitlines() if "localhost" in l or "refused" in l.lower()]
    p(f"passo 4 (recusa no log do rabbitmq): {len(achados)} linha(s) relevante(s)")
    for linha in achados[:5]:
        p("   " + redigir(linha)[:300])
    try:
        req = Request("http://127.0.0.1:15672/api/whoami")
        req.add_header("Authorization", "Basic " + base64.b64encode(f"{usuario}:{senha}".encode()).decode())
        with urlopen(req, timeout=10) as resp:
            p(f"passo 5 (painel, host): HTTP {resp.status}")
    except HTTPError as exc:
        p(f"passo 5 (painel, host): HTTP {exc.code}")
    except URLError as exc:
        p(f"passo 5 (painel, host): erro de conexao {type(exc.reason).__name__}")
compose("down", "-v")
p("passo 6: down -v executado")
(LOGS / "reproducao_compose_broker_guest.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")
print("\n".join(linhas))
