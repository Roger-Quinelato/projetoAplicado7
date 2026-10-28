# -*- coding: utf-8 -*-
"""F-SEG, item 11: triagem dos achados de segredos com saída mascarada (nunca imprime valores).

Lê os relatórios redigidos (árvore e histórico), busca a linha no conteúdo (árvore de trabalho ou
versão do commit) e imprime a linha com credenciais e atribuições mascaradas. Só tipos de
detector que podem indicar credencial (Basic Auth, Secret Keyword e os padrões do histórico) são
triados linha a linha; os de alta entropia são contados como ruído e amostrados por arquivo.
"""
import collections
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
ISO = r"C:\Users\roger\.claude\jobs\f5019419\tmp\iso-seg"
LOGS = r"C:\Users\roger\projetoAplicado7\.claude\worktrees\auditoria-2026-10-18\output\auditoria\2026-10-18T2018Z\evidencias\seg\logs"
WT = r"C:\Users\roger\projetoAplicado7\.claude\worktrees\auditoria-2026-10-18"
TIPOS_CREDENCIAL = {"Basic Auth Credentials", "Secret Keyword", "Credencial em URL", "Atribuição de credencial",
                    "AWS access key id", "GitHub token", "Slack token", "Chave privada", "JWT",
                    "Chave de API estilo sk-", "Chave Google API"}


def mascarar(linha):
    s = linha.strip()
    s = re.sub(r"(://)[^\s/@]+@", r"\1<REDACTED>@", s)
    s = re.sub(r"(?i)(password|passwd|secret|api[_-]?key|access[_-]?key|token|guest|archcorp)(\s*[:=]\s*)(['\"]?)[^\s'\",)]+",
               r"\1\2\3<REDACTED>", s)
    s = re.sub(r"(?<=[:=] )(['\"]?)[A-Za-z0-9+/=_.-]{20,}", r"\1<REDACTED-LONGO>", s)
    s = re.sub(r"\b[A-Fa-f0-9]{32,}\b", "<REDACTED-HEX>", s)
    return s[:220]


def linha_da_arvore(arquivo, numero):
    caminho = os.path.join(ISO, arquivo.replace("/", os.sep))
    try:
        with open(caminho, encoding="utf-8", errors="replace") as arq:
            for i, texto in enumerate(arq, 1):
                if i == numero:
                    return texto
    except OSError:
        return "<arquivo indisponível>"
    return "<linha inexistente>"


def linha_do_commit(commit, arquivo, numero):
    proc = subprocess.run(["git", "-C", WT, "show", f"{commit}:{arquivo}"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        return "<versão do commit indisponível>"
    linhas = proc.stdout.splitlines()
    return linhas[numero - 1] if 0 < numero <= len(linhas) else "<linha inexistente>"


saida = []
arvore = json.load(open(os.path.join(LOGS, "detect_secrets_arvore_redigido.json"), encoding="utf-8"))
saida.append("== ÁRVORE DE TRABALHO (cópia iso-seg, commit 44b8325)")
ruido = collections.Counter()
for item in arvore["achados"]:
    if item["tipo"] in TIPOS_CREDENCIAL:
        saida.append(f"{item['tipo']} | {item['arquivo']}:{item['linha']} | {mascarar(linha_da_arvore(item['arquivo'], item['linha']))}")
    else:
        ruido[(item["tipo"], item["arquivo"])] += 1
saida.append("ruído de alta entropia na árvore (tipo, arquivo): " + str(sorted(ruido.items())))

hist = json.load(open(os.path.join(LOGS, "historico_segredos_redigido.json"), encoding="utf-8"))
saida.append("== HISTÓRICO (git log -p --all; somente linhas adicionadas)")
vistos = set()
for reg in hist["registros"]:
    if reg["tipo"] in TIPOS_CREDENCIAL and (reg["tipo"], reg["arquivo"], reg["commit"]) not in vistos:
        vistos.add((reg["tipo"], reg["arquivo"], reg["commit"]))
        saida.append(f"{reg['tipo']} | commit {reg['commit']} | {reg['arquivo']}:{reg['linha']} | "
                     f"{mascarar(linha_do_commit(reg['commit'], reg['arquivo'], reg['linha']))}")
contagem_hist = collections.Counter(reg["tipo"] for reg in hist["registros"])
saida.append("contagem por tipo no histórico (inclui ruído): " + str(contagem_hist.most_common()))
saida.append("registros de credencial distintos no histórico: " + str(len(vistos)))

with open(os.path.join(LOGS, "triagem_segredos_mascarado.txt"), "w", encoding="utf-8") as arq:
    arq.write("\n".join(saida) + "\n")
print("\n".join(saida))
