# -*- coding: utf-8 -*-
"""F-SEG, E-09: matriz de autorização das operações de app.routes (TestClient + SQLite na cópia).

Uso: python seg_autorizacao_matriz.py local|publico
- local: tokens fixos de TOKEN_ROLES (demo-*), PUBLIC_DEMO desligado.
- publico: PUBLIC_DEMO ligado; token aleatório lido de tmp/seg_token_publico.txt (não é impresso).
Cada operação é chamada sem token, com papel errado, com papel certo e com demo-admin.
Payloads são {} (falham na validação, antes de qualquer gravação) e os IDs são inexistentes.
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
MODO = sys.argv[1] if len(sys.argv) > 1 else "local"
ISO = r"C:\Users\roger\.claude\jobs\f5019419\tmp\iso-seg"
LOGS = r"C:\Users\roger\projetoAplicado7\.claude\worktrees\auditoria-2026-10-18\output\auditoria\2026-10-18T2018Z\evidencias\seg\logs"

os.environ.pop("RABBITMQ_URL", None)
banco = os.path.join(ISO, "tmp", f"matriz_{MODO}.db")
if os.path.exists(banco):
    os.remove(banco)
os.environ["DATABASE_URL"] = "sqlite:///" + banco.replace("\\", "/")
TOKEN_PUBLICO = None
if MODO == "publico":
    with open(os.path.join(ISO, "tmp", "seg_token_publico.txt"), encoding="ascii") as arq:
        TOKEN_PUBLICO = arq.read().strip()
    os.environ["PUBLIC_DEMO"] = "true"
    os.environ["DEMO_ACCESS_TOKEN"] = TOKEN_PUBLICO
else:
    os.environ.pop("PUBLIC_DEMO", None)
    os.environ.pop("DEMO_ACCESS_TOKEN", None)
sys.path.insert(0, os.path.join(ISO, "src"))

from fastapi.routing import APIRoute  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from archcorp.main import app  # noqa: E402
from archcorp.security import TOKEN_ROLES  # noqa: E402

UUID_FAKE = "00000000-0000-4000-8000-000000000000"
VALORES = {"source_system": "CRM", "legacy_id": "INEXISTENTE"}
ORDEM_LOCAL = ["demo-commercial", "demo-contracts", "demo-finance", "demo-support", "demo-operations"]


def preencher(caminho):
    return re.sub(r"\{([a-zA-Z_]+)(?::[a-z]+)?\}", lambda m: VALORES.get(m.group(1), UUID_FAKE), caminho)


def dependencias(dep, acumulado):
    for sub in dep.dependencies:
        acumulado.append(sub)
        dependencias(sub, acumulado)
    return acumulado


def papeis_de(rota):
    permitidos = None
    for sub in dependencias(rota.dependant, []):
        fn = sub.call
        if getattr(fn, "__qualname__", "").startswith("require_roles.<locals>.dependency"):
            for celula in fn.__closure__ or ():
                valor = celula.cell_contents
                if isinstance(valor, tuple) and valor and all(isinstance(x, str) for x in valor):
                    permitidos = tuple(sorted(valor))
    return permitidos


def chamar(cliente, metodo, caminho, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    kwargs = {"headers": headers}
    if metodo in ("POST", "PUT", "PATCH"):
        kwargs["json"] = {}
    return cliente.request(metodo, caminho, **kwargs).status_code


def rotas_api(aplicacao):
    """Rotas APIRoute diretas e as dos include_router (FastAPI 0.143: _IncludedRouter.original_router)."""
    for item in aplicacao.routes:
        if isinstance(item, APIRoute):
            yield item
        elif type(item).__name__ == "_IncludedRouter":
            if getattr(item.include_context, "dependencies", None):
                raise RuntimeError("include_router com dependências de inclusão: a matriz precisa tratá-las")
            for sub in item.original_router.routes:
                if isinstance(sub, APIRoute):
                    yield sub


operacoes = []
for rota in rotas_api(app):
    if rota.include_in_schema:
        for metodo in sorted(rota.methods):
            operacoes.append((metodo, rota.path, rota))

linhas = []
with TestClient(app, raise_server_exceptions=False) as cliente:
    for metodo, modelo, rota in operacoes:
        caminho = preencher(modelo)
        permitidos = papeis_de(rota)
        registro = {"metodo": metodo, "rota": modelo, "papeis_permitidos": list(permitidos) if permitidos else None}
        if MODO == "local":
            sem = chamar(cliente, metodo, caminho)
            if permitidos is None:
                registro.update(sem_token=sem, veredito="sem require_roles (público por desenho)" if sem not in (401, 403) else "anomalia")
            else:
                certo = next((t for t in ORDEM_LOCAL if set(TOKEN_ROLES[t]) & set(permitidos)), "demo-admin")
                errado = next((t for t in ORDEM_LOCAL if not (set(TOKEN_ROLES[t]) & set(permitidos))), None)
                s_errado = chamar(cliente, metodo, caminho, errado) if errado else None
                s_certo = chamar(cliente, metodo, caminho, certo)
                s_admin = chamar(cliente, metodo, caminho, "demo-admin")
                ok = sem == 401 and s_errado == 403 and s_certo not in (401, 403) and s_admin not in (401, 403)
                registro.update(sem_token=sem, papel_errado=f"{errado}:{s_errado}", papel_certo=f"{certo}:{s_certo}",
                                demo_admin=s_admin, veredito="ok" if ok else "divergente")
        else:
            sem = chamar(cliente, metodo, caminho)
            s_suporte = chamar(cliente, metodo, caminho, "demo-support")
            s_admin_local = chamar(cliente, metodo, caminho, "demo-admin")
            s_publico = chamar(cliente, metodo, caminho, TOKEN_PUBLICO)
            if permitidos is None:
                ok = sem not in (401, 403)
                registro.update(sem_token=sem, veredito="sem require_roles (público por desenho)" if ok else "anomalia")
            else:
                ok = sem == 401 and s_suporte == 401 and s_admin_local == 401 and s_publico not in (401, 403)
                registro.update(sem_token=sem, demo_support_local=s_suporte, demo_admin_local=s_admin_local,
                                token_publico=s_publico, veredito="ok" if ok else "divergente")
        linhas.append(registro)

protegidas = [r for r in linhas if r["papeis_permitidos"]]
publicas = [r for r in linhas if not r["papeis_permitidos"]]
divergentes = [r for r in linhas if r["veredito"] not in ("ok",) and not r["veredito"].startswith("sem require_roles")]
cincoxx = [r for r in linhas if any(str(v).startswith("5") for k, v in r.items() if k in ("sem_token", "demo_admin", "token_publico", "demo_admin_local") or k.startswith("papel_"))]
resumo = {
    "modo": MODO,
    "operacoes_api_total": len(linhas),
    "com_require_roles": len(protegidas),
    "sem_require_roles": [f"{r['metodo']} {r['rota']}" for r in publicas],
    "divergentes": [f"{r['metodo']} {r['rota']}: {r['veredito']}" for r in divergentes],
    "respostas_5xx": [f"{r['metodo']} {r['rota']}" for r in cincoxx],
    "papeis_distintos": sorted({tuple(r["papeis_permitidos"]) for r in protegidas}),
    "rota_sem_papel_com_token_invalido": None,
}
with open(os.path.join(LOGS, f"e09_matriz_{MODO}.json"), "w", encoding="utf-8") as arq:
    json.dump({"resumo": resumo, "linhas": linhas}, arq, ensure_ascii=False, indent=1)
with open(os.path.join(LOGS, f"e09_matriz_{MODO}.tsv"), "w", encoding="utf-8") as arq:
    colunas = ["metodo", "rota", "papeis_permitidos", "sem_token", "papel_errado", "papel_certo", "demo_admin",
               "demo_support_local", "demo_admin_local", "token_publico", "veredito"]
    arq.write("\t".join(colunas) + "\n")
    for r in linhas:
        arq.write("\t".join(str(r.get(c, "")) if r.get(c) is not None else "" for c in colunas) + "\n")
print("modo:", MODO, "| operações de API:", len(linhas), "| com require_roles:", len(protegidas))
print("sem require_roles:", resumo["sem_require_roles"])
print("divergentes:", len(divergentes), resumo["divergentes"][:20])
print("respostas 5xx:", resumo["respostas_5xx"])
print("papéis distintos:", resumo["papeis_distintos"])
