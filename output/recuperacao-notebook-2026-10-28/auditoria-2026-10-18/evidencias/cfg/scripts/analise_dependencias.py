"""F-CFG, item 8: fixação das dependências diretas e fechamento transitivo, sem instalar nada.

Uso (PowerShell, com PY = venv-auditoria):
    PY -I analise_dependencias.py <WT>

Lê os metadados já instalados no venv-auditoria (importlib.metadata) e calcula, a partir das
dependências de execução de requirements.txt, o conjunto de pacotes que o pip resolveria.
Compara com os pins de requirements.txt. Limitação: o fechamento é avaliado neste Windows com
Python 3.12.10; marcadores de plataforma podem diferir na CI (Linux). Não substitui pip-audit.
"""
import sys
from pathlib import Path
from importlib import metadata

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

WT = Path(sys.argv[1]).resolve()
SAIDA = WT / "output/auditoria/2026-10-18T2018Z/evidencias/cfg/logs/dependencias_fechamento.txt"
linhas = []


def p(texto: str = "") -> None:
    linhas.append(texto)


def ler_pins(caminho: Path) -> dict:
    pins = {}
    for bruta in caminho.read_text(encoding="utf-8").splitlines():
        linha = bruta.split("#", 1)[0].strip()
        if not linha or linha.startswith("-r"):
            continue
        req = Requirement(linha)
        pins[canonicalize_name(req.name)] = (req.name, req.specifier, tuple(sorted(req.extras)))
    return pins


def fechamento(raizes: list) -> dict:
    resultado = {}
    fila = [(chave, extras) for chave, (_, _, extras) in raizes]
    vistos = set()
    while fila:
        nome, extras = fila.pop()
        if (nome, extras) in vistos:
            continue
        vistos.add((nome, extras))
        try:
            dist = metadata.distribution(nome)
        except metadata.PackageNotFoundError:
            resultado.setdefault(nome, ("NAO INSTALADO", set()))
            continue
        versao_anterior = resultado.get(nome, (None, set()))[1]
        resultado[nome] = (dist.version, versao_anterior | set(extras))
        for texto in dist.requires or []:
            req = Requirement(texto)
            if req.marker is None:
                entra = True
            else:
                entra = any(req.marker.evaluate({"extra": e}) for e in ("",) + tuple(extras))
            if entra:
                fila.append((canonicalize_name(req.name), tuple(sorted(req.extras))))
    return resultado


runtime = ler_pins(WT / "requirements.txt")
dev = ler_pins(WT / "requirements-dev.txt")
p("## Pins diretos de requirements.txt (versao exigida x instalada no venv)")
for chave, (nome, especificador, extras) in runtime.items():
    try:
        instalada = metadata.version(nome)
    except metadata.PackageNotFoundError:
        instalada = "NAO INSTALADA"
    ok = str(especificador) == "==" + instalada
    p(f"{nome}{'[' + ','.join(extras) + ']' if extras else ''} {especificador} | instalada={instalada} | igual={ok}")
p("")
raizes_runtime = [(chave, (nome, espec, extras)) for chave, (nome, espec, extras) in runtime.items()]
fech_runtime = fechamento(raizes_runtime)
diretos = set(runtime.keys())
transitivos = {k: v for k, v in fech_runtime.items() if k not in diretos}
p(f"## Fechamento de execucao: diretos={len(diretos)}; transitivos={len(transitivos)} (todos sem pin em requirements.txt)")
for nome in sorted(transitivos):
    versao, extras = transitivos[nome]
    p(f"  {nome}=={versao}" + (f" [extras usados: {','.join(sorted(extras))}]" if extras else ""))
p("")
raizes_dev = [(chave, (nome, espec, extras)) for chave, (nome, espec, extras) in dev.items()]
fech_total = fechamento(raizes_dev)
so_dev = {k: v for k, v in fech_total.items() if k not in fech_runtime}
p(f"## Pacotes so de desenvolvimento (requirements-dev.txt, fora da imagem): {len(so_dev)}")
for nome in sorted(so_dev):
    p(f"  {nome}=={so_dev[nome][0]}")
SAIDA.write_text("\n".join(linhas) + "\n", encoding="utf-8")
print(f"diretos={len(diretos)} transitivos={len(transitivos)} so_dev={len(so_dev)}")
