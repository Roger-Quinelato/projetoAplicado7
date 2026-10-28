"""F-CFG, itens 3 a 9 e 11 do checklist: análise estática de Dockerfile, compose, render.yaml, CI,
ignores, web/ e Alembic. Sem Docker: tudo é leitura de arquivos e parse de YAML/JSON.

Uso (PowerShell, com PY = venv-auditoria):
    PY -I analise_estatica.py <WT> <ISO>

<WT> é o worktree (fonte dos arquivos versionados); <ISO> é a cópia usada apenas para os
arquivos de web/ (idênticos ao SHA). Credenciais e URLs com userinfo são reportadas só como
presença ("credencial embutida na URL: sim"), nunca com o valor.
"""
import json
import re
import sys
from pathlib import Path

import yaml

WT = Path(sys.argv[1]).resolve()
ISO = Path(sys.argv[2]).resolve()
saida = []


def p(texto: str = "") -> None:
    saida.append(texto)


def ler(rel: str) -> str:
    return (WT / rel).read_text(encoding="utf-8")


def tem_userinfo(url: str) -> bool:
    return bool(re.match(r"^[a-z+]+://[^/@]+@", url))


def secao(titulo: str) -> None:
    p("")
    p("## " + titulo)


# ---------------------------------------------------------------- Dockerfile (S-05, item 4)
secao("Dockerfile (estático)")
dockerfile = ler("Dockerfile").splitlines()
for n, linha in enumerate(dockerfile, 1):
    if re.match(r"^\s*(FROM|USER|HEALTHCHECK|EXPOSE|CMD|ENTRYPOINT|COPY|RUN|ENV|WORKDIR)\b", linha):
        p(f"Dockerfile:{n}: {linha.strip()}")
froms = [linha for linha in dockerfile if linha.strip().startswith("FROM ")]
p(f"imagens-base: {len(froms)}; com digest (@sha256): {sum('@sha256' in f for f in froms)}")
p(f"diretiva USER presente: {any(l.strip().startswith('USER ') for l in dockerfile)}")
p(f"diretiva HEALTHCHECK presente: {any(l.strip().startswith('HEALTHCHECK') for l in dockerfile)}")
p(f"pip install com --require-hashes: {any('--require-hashes' in l for l in dockerfile)}")
p(f"CMD em forma shell (sh -c): {any(re.search(r'^CMD\s*\[\s*\"sh\"', l.strip()) for l in dockerfile)}")
usos_vite = []
for arq in ["web/src", "web/index.html", "web/vite.config.ts"]:
    base = ISO / arq
    arquivos = [base] if base.is_file() else [q for q in base.rglob("*") if q.is_file()] if base.exists() else []
    for q in arquivos:
        if "node_modules" in q.parts or "tests" in q.parts:
            continue
        for n, linha in enumerate(q.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for chave in re.findall(r"import\.meta\.env\.(\w+)", linha):
                usos_vite.append((q.relative_to(ISO).as_posix(), n, chave))
p("import.meta.env no código do web/ (arquivo:linha, chave):")
for arq, n, chave in usos_vite:
    p(f"  {arq}:{n} -> {chave}")
p(f"variaveis VITE_* embutidas no bundle: {sum(1 for _, _, c in usos_vite if c.startswith('VITE_'))}")

# ---------------------------------------------------------------- docker-compose (item 5)
secao("docker-compose.yml (estático)")
compose = yaml.safe_load(ler("docker-compose.yml"))
p("chaves de topo: " + ", ".join(compose.keys()))
for nome, svc in compose["services"].items():
    chaves = sorted(svc.keys())
    p(f"servico {nome}: chaves={chaves}")
    p(f"  restart presente: {'restart' in svc}; healthcheck presente: {'healthcheck' in svc}; "
      f"limites de recurso (deploy/mem_limit/cpus): {'deploy' in svc or 'mem_limit' in svc or 'cpus' in svc}")
    for porta in svc.get("ports", []):
        p(f"  porta publicada: {porta} -> ligada em 127.0.0.1: {str(porta).startswith('127.0.0.1:')}")
    if "depends_on" in svc:
        for dep, cond in svc["depends_on"].items():
            p(f"  depends_on {dep}: condicao={cond.get('condition')}")
    ambiente = svc.get("environment", {})
    if isinstance(ambiente, dict):
        for chave, valor in ambiente.items():
            if isinstance(valor, str) and "://" in valor:
                p(f"  env {chave}: URL; credencial embutida: {tem_userinfo(valor)}")
            else:
                p(f"  env {chave}: definido (valor nao registrado)")
    if "POSTGRES_PASSWORD" in (ambiente or {}):
        usuario = (ambiente or {}).get("POSTGRES_USER")
        senha = (ambiente or {}).get("POSTGRES_PASSWORD")
        p(f"  POSTGRES_PASSWORD igual a POSTGRES_USER: {usuario == senha}; comprimento={len(str(senha))}")
p("volumes de topo: " + str(list(compose.get("volumes", {}).keys())))

# ---------------------------------------------------------------- render.yaml (item 6)
secao("render.yaml (estático)")
render = yaml.safe_load(ler("render.yaml"))
svc = render["services"][0]
p("chaves do servico: " + ", ".join(sorted(svc.keys())))
p(f"plan={svc.get('plan')} runtime={svc.get('runtime')} healthCheckPath={svc.get('healthCheckPath')}")
p(f"autoDeploy declarado: {'autoDeploy' in svc}; region declarado: {'region' in svc}; "
  f"disk declarado: {'disk' in svc}; numInstances declarado: {'numInstances' in svc}")
for var in svc.get("envVars", []):
    if var.get("sync") is False:
        p(f"  envVar {var['key']}: sync=false (valor fora do repositorio)")
    else:
        p(f"  envVar {var['key']}: valor fixo={var.get('value')}")
p("RABBITMQ_URL, FINANCE_ALLOW_FUTURE_AS_OF, CONTRACT_ADAPTER_AVAILABLE declarados: "
  + str(any(v.get("key") in ("RABBITMQ_URL", "FINANCE_ALLOW_FUTURE_AS_OF") for v in svc.get("envVars", []))))

# ---------------------------------------------------------------- verify.yml (item 7, S-04)
secao("verify.yml (estático)")
ci = yaml.safe_load(ler(".github/workflows/verify.yml"))
gatilhos = ci.get(True, ci.get("on"))
p("gatilhos: " + json.dumps(gatilhos, ensure_ascii=False))
p(f"permissions de topo: {ci.get('permissions')}")
p(f"concurrency de topo presente: {'concurrency' in ci}")
todas_uses = []
for nome, job in ci["jobs"].items():
    p(f"job {nome}: runs-on={job.get('runs-on')}; timeout-minutes={'timeout-minutes' in job}; "
      f"permissions={'permissions' in job}; concurrency={'concurrency' in job}")
    for servico, cfg in (job.get("services") or {}).items():
        p(f"  service {servico}: imagem={cfg.get('image')}")
    for chave, valor in (job.get("env") or {}).items():
        if "://" in str(valor):
            p(f"  env {chave}: URL; credencial embutida: {tem_userinfo(str(valor))}")
        else:
            p(f"  env {chave}: definido")
    for passo in job["steps"]:
        if "uses" in passo:
            uso = passo["uses"]
            todas_uses.append(uso)
            ref = uso.split("@", 1)[1] if "@" in uso else ""
            tipo = "SHA" if re.fullmatch(r"[0-9a-f]{40}", ref) else "tag"
            p(f"  uses {uso} (referencia por {tipo})")
        if "run" in passo:
            p(f"  run: {passo['run'][:150]}")
    p(f"  setup-python com cache de pip: {any('cache' in (s.get('with') or {}) for s in job['steps'] if 'uses' in s and 'setup-python' in s['uses'])}")
p(f"actions referenciadas por tag: {sum(1 for u in todas_uses if not re.search(r'@[0-9a-f]{40}$', u))} de {len(todas_uses)}")
texto_ci = ler(".github/workflows/verify.yml")
for ferramenta in ["ruff", "mypy", "bandit", "semgrep", "detect-secrets", "gitleaks", "trivy", "codeql", "dependabot"]:
    p(f"ferramenta '{ferramenta}' citada no verify.yml: {ferramenta in texto_ci.lower()}")
p(f"pip install ocorrencias no verify.yml: {texto_ci.count('pip install')}")

# ---------------------------------------------------------------- ignores e segredos (item 3, S-02, S-06)
secao(".dockerignore e .gitignore (estático)")
dockerignore = [l.strip() for l in ler(".dockerignore").splitlines() if l.strip()]
p("dockerignore: " + ", ".join(dockerignore))
p(f".dockerignore exclui .env: {'.env' in dockerignore}; exclui .git: {'.git' in dockerignore}")
gitignore = ler(".gitignore").splitlines()
for padrao in [".env", ".envrc", "*.log", ".claude", ".claude/worktrees", "tmp/", ".codex-finalizer/", ".codex-remote-attachments/", "*.db"]:
    ocorr = [f"{n}:{l}" for n, l in enumerate(gitignore, 1) if l.strip() == padrao]
    p(f"gitignore contem '{padrao}': {ocorr if ocorr else 'NAO'}")
p("arquivos .env* ou *.example versionados: " + str(sorted(
    l for l in __import__("subprocess").run(["git", "-C", str(WT), "ls-files"], capture_output=True, text=True, encoding="utf-8").stdout.splitlines()
    if re.search(r"(^|/)\.env|\.example$", l))))

# ---------------------------------------------------------------- web/ (item 9)
secao("web/ (estático)")
pacote = json.loads((ISO / "web/package.json").read_text(encoding="utf-8"))
p(f"package.json: scripts={pacote.get('scripts')}")
p(f"package.json: engines declarado={'engines' in pacote}; packageManager declarado={'packageManager' in pacote}; private={pacote.get('private')}")
p(f"package.json: dependencias={pacote.get('dependencies')}; devDependencies={pacote.get('devDependencies')}")
tsconfig = json.loads((ISO / "web/tsconfig.json").read_text(encoding="utf-8"))
p(f"tsconfig: strict={tsconfig['compilerOptions'].get('strict')}; noUnusedLocals={tsconfig['compilerOptions'].get('noUnusedLocals')}; "
  f"noUnusedParameters={tsconfig['compilerOptions'].get('noUnusedParameters')}; include={tsconfig.get('include')}; "
  f"noFallthroughCasesInSwitch={tsconfig['compilerOptions'].get('noFallthroughCasesInSwitch')}; "
  f"noUncheckedIndexedAccess={tsconfig['compilerOptions'].get('noUncheckedIndexedAccess')}")
p("vite.config.ts (texto):")
for linha in (ISO / "web/vite.config.ts").read_text(encoding="utf-8").splitlines():
    p("  " + linha)
arquivos_tests = sorted(q.relative_to(ISO).as_posix() for q in (ISO / "web/tests").rglob("*") if q.is_file())
p(f"arquivos de teste do web/ fora do include do tsconfig: {arquivos_tests}")

# ---------------------------------------------------------------- Alembic (item 11)
secao("Alembic (estático)")
ini = ler("alembic.ini")
p(f"alembic.ini tem sqlalchemy.url: {'sqlalchemy.url' in ini}")
env_py = ler("src/archcorp/infrastructure/migrations/env.py")
p(f"env.py usa settings.database_url como fallback: {'settings.database_url' in env_py}")

(WT / "output/auditoria/2026-10-18T2018Z/evidencias/cfg/logs/analise_estatica.txt").write_text(
    "\n".join(saida) + "\n", encoding="utf-8")
print(f"linhas: {len(saida)}")
