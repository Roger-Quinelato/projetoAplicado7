"""F-QUA - resume o relatorio JSON do coverage (com ramos) por modulo e por pacote de src/.

Uso: python -I resumo_cobertura.py <logs>\\coverage_src.json
Gerado por: coverage json --include="src/*" (apos coverage run --branch -m pytest ...).
Cobertura de linhas = linhas executadas / instrucoes; de ramos = ramos executados / ramos;
combinada = (linhas executadas + ramos executados) / (instrucoes + ramos), como o relatorio do coverage.
"""
import json
import sys
from collections import defaultdict

data = json.load(open(sys.argv[1], encoding="utf-8"))


def pct(covered: int, total: int) -> str:
    return f"{100 * covered / total:.1f}%" if total else "n/a"


def package_of(path: str) -> str:
    parts = path.replace("\\", "/").split("/")
    index = parts.index("archcorp") if "archcorp" in parts else -1
    if index < 0:
        return path
    rest = parts[index + 1:]
    return rest[0] if len(rest) > 1 else "(raiz de archcorp)"


totals = data["totals"]
print("TOTAL GERAL")
print(f"  instrucoes={totals['num_statements']} executadas={totals['covered_lines']} "
      f"linhas={pct(totals['covered_lines'], totals['num_statements'])}")
print(f"  ramos={totals['num_branches']} executados={totals['covered_branches']} "
      f"ramos={pct(totals['covered_branches'], totals['num_branches'])}")
print(f"  combinada={totals['percent_covered']:.1f}%")

packages: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
for path, info in data["files"].items():
    summary = info["summary"]
    bucket = packages[package_of(path)]
    for key in ("num_statements", "covered_lines", "num_branches", "covered_branches"):
        bucket[key] += summary[key]
    bucket["files"] += 1

print("\nPOR PACOTE (linhas / ramos)")
for name in sorted(packages):
    b = packages[name]
    print(f"  {name:<22} arquivos={b['files']:<3} linhas={pct(b['covered_lines'], b['num_statements']):>6} "
          f"({b['covered_lines']}/{b['num_statements']})  ramos={pct(b['covered_branches'], b['num_branches']):>6} "
          f"({b['covered_branches']}/{b['num_branches']})")

print("\nARQUIVOS COM COBERTURA DE LINHAS ABAIXO DE 80%")
for path, info in sorted(data["files"].items()):
    s = info["summary"]
    if s["num_statements"] and s["covered_lines"] / s["num_statements"] < 0.80:
        print(f"  {path}: linhas {pct(s['covered_lines'], s['num_statements'])} "
              f"({s['covered_lines']}/{s['num_statements']}), linhas ausentes={info['missing_lines']}")
