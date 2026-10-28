# -*- coding: utf-8 -*-
"""F-SEG, item 11: varredura da árvore da cópia isolada com o detect-secrets (CLI, cwd = cópia).

A saída bruta traz hashes dos achados; ela fica em tmp/ da cópia e é apagada ao final.
O relatório gravado na pasta da frente contém somente tipo, arquivo, linha e plugins.
"""
import collections
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
ISO = r"C:\Users\roger\.claude\jobs\f5019419\tmp\iso-seg"
DS = r"C:\Users\roger\.claude\jobs\f5019419\tmp\venv-auditoria\Scripts\detect-secrets.exe"
SAIDA = r"C:\Users\roger\projetoAplicado7\.claude\worktrees\auditoria-2026-10-18\output\auditoria\2026-10-18T2018Z\evidencias\seg\logs\detect_secrets_arvore_redigido.json"
RAW = os.path.join(ISO, "tmp", "ds_raw.json")
EXCLUIR = r"node_modules|(^|[\\/])dist[\\/]|__pycache__|\.pytest_cache|(^|[\\/])tmp[\\/]"

proc = subprocess.run(
    [DS, "scan", "--all-files", "--exclude-files", EXCLUIR],
    cwd=ISO, capture_output=True, text=True, encoding="utf-8", errors="replace",
)
print("rc detect-secrets:", proc.returncode, "| bytes stdout:", len(proc.stdout), "| bytes stderr:", len(proc.stderr))
with open(RAW, "w", encoding="utf-8") as f:
    f.write(proc.stdout)
dados = json.loads(proc.stdout)
os.remove(RAW)

achados = []
for arquivo, itens in dados.get("results", {}).items():
    for item in itens:
        achados.append({"arquivo": arquivo.replace("\\", "/"), "linha": item.get("line_number"), "tipo": item.get("type")})
por_tipo = collections.Counter(a["tipo"] for a in achados)
por_arquivo = collections.Counter(a["arquivo"] for a in achados)
relatorio = {
    "ferramenta": "detect-secrets CLI: scan --all-files (cwd = iso-seg)",
    "excluir_regex": EXCLUIR,
    "plugins": [p.get("name") for p in dados.get("plugins_used", [])],
    "total": len(achados),
    "por_tipo": por_tipo.most_common(),
    "por_arquivo": por_arquivo.most_common(),
    "achados": achados,
}
with open(SAIDA, "w", encoding="utf-8") as f:
    json.dump(relatorio, f, ensure_ascii=False, indent=1)
print("total de achados:", len(achados))
print("por tipo:", por_tipo.most_common())
print("arquivos com achados:", len(por_arquivo))
for arq, n in por_arquivo.most_common(25):
    print("  ", n, arq)
