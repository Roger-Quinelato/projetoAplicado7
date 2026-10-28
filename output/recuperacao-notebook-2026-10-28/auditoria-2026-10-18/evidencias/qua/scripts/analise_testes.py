"""F-QUA - analise estatica da qualidade dos testes (sem executar nenhum teste).

Uso: python -I analise_testes.py <ISO>\\tests
Classifica, por funcao test_*:
  - sem asserção (nem pytest.raises);
  - so asserções de status HTTP (todas as asserções mencionam status_code e nenhuma inspeciona corpo/cabecalho);
  - asserção tautologica (lado esquerdo igual ao direito, ou assert True);
  - asserção fraca (somente 'is not None' ou apenas truthiness);
  - atribuicao direta a settings (sem monkeypatch), e se ha try/finally na funcao (restauracao heuristica);
  - concorrencia real (ThreadPoolExecutor, Barrier, threading) ou nome que sugere concorrencia sem threads;
  - skip/skipif e o motivo declarado.
"""
import ast
import sys
from pathlib import Path

TESTS = Path(sys.argv[1])
# Marcadores de inspeção da RESPOSTA (não do kwarg headers= da requisição).
BODY_MARKERS = (".json()", ".text", ".headers", ".content", "len(")


def is_pytest_raises(node: ast.AST) -> bool:
    return isinstance(node, ast.With) and any(
        isinstance(item.context_expr, ast.Call) and "raises" in ast.dump(item.context_expr.func)
        for item in node.items
    )


def tautological(test: ast.expr) -> bool:
    if isinstance(test, ast.Constant) and test.value is True:
        return True
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
        return ast.dump(test.left) == ast.dump(test.comparators[0])
    return False


def weak(test: ast.expr) -> bool:
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.IsNot):
        return isinstance(test.comparators[0], ast.Constant) and test.comparators[0].value is None
    return isinstance(test, (ast.Name, ast.Attribute, ast.Subscript))


def settings_targets(function: ast.FunctionDef) -> list[tuple[int, str]]:
    found = []
    for node in ast.walk(function):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AugAssign) else []
        for target in targets:
            for sub in ast.walk(target):
                if isinstance(sub, ast.Attribute) and "settings" in ast.unparse(sub.value):
                    found.append((node.lineno, ast.unparse(sub)))
    return found


rows = []
totals = {"tests": 0, "sem_assercao": 0, "so_status": 0, "tautologica": 0, "fraca": 0,
          "settings_direto": 0, "concorrencia_threads": 0, "nome_concorrencia_sem_threads": 0,
          "skip": 0}
skip_reasons = []
settings_lines = []
concurrency_lines = []

for path in sorted(TESTS.glob("test_*.py")):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for function in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]:
        totals["tests"] += 1
        segment_text = ast.get_source_segment(source, function) or ""
        asserts = [n for n in ast.walk(function) if isinstance(n, ast.Assert)]
        raises = [n for n in ast.walk(function) if is_pytest_raises(n)]
        # Helpers assert_* (ex.: assert_problem) contem as asserções: contam como asserção da função.
        helpers = [n for n in ast.walk(function) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                   and getattr(n.value.func, "id", "").startswith("assert_")]
        assertion_count = len(asserts) + len(raises) + len(helpers)
        flags = []
        if assertion_count == 0:
            flags.append("sem_assercao")
            totals["sem_assercao"] += 1
        elif asserts and not raises and not helpers and all(
            "status_code" in (ast.get_source_segment(source, a) or "")
            and not any(marker in (ast.get_source_segment(source, a) or "") for marker in BODY_MARKERS)
            for a in asserts
        ):
            flags.append("so_status")
            totals["so_status"] += 1
        if any(tautological(a.test) for a in asserts):
            flags.append("tautologica")
            totals["tautologica"] += 1
        # Fraca: so 'is not None' ou truthiness de nome/atributo. Chamadas (any(...), detector(...)) nao contam.
        if asserts and not helpers and all(weak(a.test) for a in asserts) and not any(
            isinstance(a.test, (ast.Compare, ast.Call)) for a in asserts):
            flags.append("fraca")
            totals["fraca"] += 1
        targets = settings_targets(function)
        if targets:
            restored = any(isinstance(n, ast.Try) and n.finalbody for n in ast.walk(function))
            flags.append(f"settings_direto({'com' if restored else 'sem'}_finally)")
            totals["settings_direto"] += 1
            settings_lines += [f"{path.name}:{line} {target} ({'try/finally na funcao' if restored else 'sem try/finally'})" for line, target in targets]
        uses_threads = any(token in segment_text for token in ("ThreadPoolExecutor", "Barrier", "threading", "Thread("))
        if uses_threads:
            flags.append("concorrencia_threads")
            totals["concorrencia_threads"] += 1
            concurrency_lines.append(f"{path.name}:{function.lineno} {function.name}")
        elif any(word in function.name for word in ("concorr", "paralel", "simult")):
            flags.append("nome_concorrencia_sem_threads")
            totals["nome_concorrencia_sem_threads"] += 1
        skip_flags = [ast.unparse(d) for d in function.decorator_list if "skip" in ast.unparse(d)]
        skip_flags += [ast.get_source_segment(source, n) for n in ast.walk(function)
                       if isinstance(n, ast.Call) and "skip" in ast.unparse(n.func)]
        if skip_flags:
            totals["skip"] += 1
            skip_reasons.append(f"{path.name}:{function.lineno} {function.name} -> {skip_flags[0]}")
        rows.append((path.name, function.lineno, function.name, assertion_count, ",".join(flags) or "-"))

print("TOTAIS")
for key, value in totals.items():
    print(f"  {key}: {value}")
print("\nFUNCOES COM ALGUMA MARCA (arquivo:linha funcao asserções marcas)")
for name, line, func, count, flags in rows:
    if flags != "-":
        print(f"  {name}:{line} {func} asserções={count} marcas={flags}")
print("\nATRIBUICOES DIRETAS A settings")
for line in settings_lines:
    print("  " + line)
print("\nTESTES COM CONCORRENCIA REAL (threads)")
for line in concurrency_lines:
    print("  " + line)
print("\nSKIPS DECLARADOS")
for line in skip_reasons:
    print("  " + line)
