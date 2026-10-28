# -*- coding: utf-8 -*-
"""F-SEG, item 11: varredura do histórico (git log -p --all) com os detectores do detect-secrets.

Analisa somente linhas adicionadas. O relatório guarda commit (7 caracteres), arquivo, linha e
tipo; nunca o valor do segredo. Se a API interna do detect-secrets não estiver disponível,
usa o conjunto de regex abaixo (fallback), e o relatório registra qual modo foi usado.
"""
import contextlib
import collections
import json
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
WT = r"C:\Users\roger\projetoAplicado7\.claude\worktrees\auditoria-2026-10-18"
SAIDA = r"C:\Users\roger\projetoAplicado7\.claude\worktrees\auditoria-2026-10-18\output\auditoria\2026-10-18T2018Z\evidencias\seg\logs\historico_segredos_redigido.json"

REGEX = [
    ("AWS access key id", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    ("GitHub token", r"\b(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{22,255})\b"),
    ("Slack token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    ("Chave privada", r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY"),
    ("JWT", r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    ("Chave de API estilo sk-", r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}"),
    ("Chave Google API", r"\bAIza[0-9A-Za-z_-]{35}\b"),
    ("Credencial em URL", r"\b[a-z][a-z0-9+.-]*://[^\s:/@]+:[^\s/@]+@"),
    ("Atribuição de credencial", r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?key|token)\b\s*[:=]\s*['\"]?[^\s'\"#]{8,}"),
]


def detectar_regex(linha):
    return [nome for nome, padrao in REGEX if re.search(padrao, linha)]


try:
    from detect_secrets.core.scan import scan_line
    from detect_secrets.settings import default_settings
    usar_ds = True
    MODO = "detect-secrets: core.scan.scan_line com settings.default_settings"
except Exception as exc:  # pragma: no cover - depende da versão instalada
    scan_line = None
    default_settings = None
    usar_ds = False
    MODO = f"regex de fallback (motivo: {type(exc).__name__}: {exc})"


def coletar(com_ds):
    registros = set()
    linhas_analisadas = 0
    commits = set()
    comando = ["git", "-C", WT, "log", "-p", "--all", "--no-color", "--no-ext-diff", "--format=COMMIT %H"]
    proc = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8", errors="replace")
    commit = arquivo = nova = None
    for bruta in proc.stdout:
        linha = bruta.rstrip("\r\n")
        if linha.startswith("COMMIT "):
            commit = linha[7:14]
            commits.add(commit)
            arquivo = nova = None
            continue
        if linha.startswith("diff --git "):
            m = re.match(r"diff --git a/(.+?) b/(.+)$", linha)
            arquivo = m.group(2) if m else None
            nova = None
            continue
        if linha.startswith("@@"):
            m = re.search(r"\+(\d+)", linha)
            nova = int(m.group(1)) if m else None
            continue
        if nova is None:
            continue
        if linha.startswith("+"):
            linhas_analisadas += 1
            tipos = [s.type for s in scan_line(linha[1:])] if com_ds else detectar_regex(linha[1:])
            for tipo in tipos:
                registros.add((commit, arquivo, nova, tipo))
            nova += 1
        elif linha.startswith(" "):
            nova += 1
    erro = proc.stderr.read()
    proc.wait()
    return registros, linhas_analisadas, commits, proc.returncode, erro


if usar_ds:
    try:
        with default_settings():
            registros, linhas, commits, rc, erro = coletar(True)
    except Exception as exc:
        MODO = f"regex de fallback (falha na API do detect-secrets: {type(exc).__name__}: {exc})"
        usar_ds = False
if not usar_ds:
    registros, linhas, commits, rc, erro = coletar(False)

por_tipo = collections.Counter(tipo for _, _, _, tipo in registros)
por_arquivo = collections.Counter(arq for _, arq, _, _ in registros)
relatorio = {
    "modo": MODO,
    "commits_no_historico_all": len(commits),
    "linhas_adicionadas_analisadas": linhas,
    "git_rc": rc,
    "git_stderr_bytes": len(erro or ""),
    "total_registros": len(registros),
    "por_tipo": por_tipo.most_common(),
    "registros": sorted(
        [{"commit": c, "arquivo": a, "linha": n, "tipo": t} for c, a, n, t in registros],
        key=lambda r: (r["tipo"], str(r["arquivo"]), r["commit"] or ""),
    ),
}
with open(SAIDA, "w", encoding="utf-8") as f:
    json.dump(relatorio, f, ensure_ascii=False, indent=1)
print("modo:", MODO)
print("commits:", len(commits), "| linhas adicionadas analisadas:", linhas, "| git rc:", rc)
print("registros (tipo, commit, arquivo, linha) sem valor:", len(registros))
print("por tipo:", por_tipo.most_common())
print("arquivos distintos:", len(por_arquivo))
for arq, n in por_arquivo.most_common(30):
    print("  ", n, arq)
