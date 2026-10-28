"""Grafo de imports do pacote `archcorp` (F-MOD, auditoria de 18/10/2026).

Evolui `evidencias/agente2/imports_ast.py` (auditoria de 01/10) para cobrir todas as formas:
`import x`, `import x as y`, `from x import y`, `from pacote import submodulo`, import relativo,
`importlib.import_module`/`__import__` (literal ou por constante do arquivo) e import dentro de
função. Calcula regras de fronteira, dependências de framework (diretas e transitivas), ciclos
(módulo e pacote) e acoplamento aferente/eferente por pacote.

Uso (somente leitura do código analisado):
    python grafo_imports.py <raiz_src> <dir_saida>
"""
import ast
import collections
import sys
from pathlib import Path

BUSINESS = ("crm", "contracts", "finance", "support", "workflow")
CONTEXTS = BUSINESS + ("integration",)
PACKAGES = CONTEXTS + ("infrastructure",)
FRAMEWORKS = ("fastapi", "starlette", "sqlalchemy", "pika", "pydantic", "pydantic_settings", "alembic")
HTTP = ("fastapi", "starlette")


def module_name(src_root: Path, path: Path) -> tuple[str, bool]:
    parts = list(path.relative_to(src_root).with_suffix("").parts)
    is_pkg = parts[-1] == "__init__"
    if is_pkg:
        parts = parts[:-1]
    return ".".join(parts), is_pkg


def package_of(mod: str) -> str:
    parts = mod.split(".")
    if parts[0] != "archcorp":
        return "ext:" + parts[0]
    if len(parts) > 1 and parts[1] in PACKAGES:
        return parts[1]
    return "raiz"


def kind_of(mod: str) -> str:
    parts = mod.split(".")
    if parts[0] != "archcorp":
        return "externo"
    if len(parts) >= 3:
        return parts[2]
    if len(parts) == 2:
        return "__init__" if parts[1] in PACKAGES else parts[1]
    return "__init__"


def resolve_relative(current: str, is_pkg: bool, level: int, module: str | None) -> str:
    base = current.split(".")
    if not is_pkg:
        base = base[:-1]
    if level > 1:
        base = base[: len(base) - (level - 1)]
    return ".".join(base + ([module] if module else []))


class Collector(ast.NodeVisitor):
    """Coleta imports com escopo (módulo/função) e guarda TYPE_CHECKING."""

    def __init__(self, current: str, is_pkg: bool, known: set[str]):
        self.current, self.is_pkg, self.known = current, is_pkg, known
        self.depth = 0
        self.type_checking = 0
        self.edges: list[dict] = []
        self.unresolved_dynamic: list[int] = []
        self.string_constants: set[str] = set()

    def _scope(self) -> str:
        scope = "função" if self.depth else "módulo"
        return scope + (" (TYPE_CHECKING)" if self.type_checking else "")

    def _add(self, line: int, form: str, target: str, symbols: list[str]):
        self.edges.append({"line": line, "form": form, "scope": self._scope(), "target": target, "symbols": symbols})

    def visit_FunctionDef(self, node):
        self.depth += 1
        self.generic_visit(node)
        self.depth -= 1

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_If(self, node):
        guard = isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING" or (
            isinstance(node.test, ast.Attribute) and node.test.attr == "TYPE_CHECKING")
        if guard:
            self.type_checking += 1
        self.generic_visit(node)
        if guard:
            self.type_checking -= 1

    def visit_Import(self, node):
        for alias in node.names:
            form = "import as" if alias.asname else "import"
            self._add(node.lineno, form, alias.name, [alias.asname] if alias.asname else [])

    def visit_ImportFrom(self, node):
        if node.level:
            module = resolve_relative(self.current, self.is_pkg, node.level, node.module)
            form = f"from relativo (nível {node.level})"
        else:
            module = node.module or ""
            form = "from"
        plain = []
        for alias in node.names:
            candidate = f"{module}.{alias.name}"
            if candidate in self.known:
                self._add(node.lineno, form + " pacote-submódulo", candidate, [alias.asname or alias.name])
            else:
                plain.append(alias.name + (f" as {alias.asname}" if alias.asname else ""))
        if plain:
            self._add(node.lineno, form, module, plain)

    def visit_Call(self, node):
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""
        if name in ("import_module", "__import__") and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                self._add(node.lineno, f"{name}(literal)", arg.value, [])
            else:
                self.unresolved_dynamic.append(node.lineno)
        self.generic_visit(node)

    def visit_Constant(self, node):
        if isinstance(node.value, str) and node.value.startswith("archcorp."):
            self.string_constants.add(node.value)


def tarjan(graph: dict[str, set[str]]) -> list[list[str]]:
    index, low, stack, on_stack, result = {}, {}, [], set(), []
    counter = [0]
    sys.setrecursionlimit(10000)

    def strong(v):
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in graph.get(v, ()):
            if w not in index:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                result.append(sorted(comp))

    for v in sorted(graph):
        if v not in index:
            strong(v)
    return result


def shortest_path(graph: dict[str, set[str]], start: str, goal_prefix: str) -> list[str] | None:
    queue, seen = collections.deque([[start]]), {start}
    while queue:
        path = queue.popleft()
        for nxt in sorted(graph.get(path[-1], ())):
            if nxt == goal_prefix or nxt.startswith(goal_prefix + "."):
                return path + [nxt]
            if nxt not in seen and nxt.startswith("archcorp"):
                seen.add(nxt)
                queue.append(path + [nxt])
    return None


def main(src_root: Path, out_dir: Path) -> None:
    files = sorted(p for p in (src_root / "archcorp").rglob("*.py") if "__pycache__" not in p.parts)
    known = {module_name(src_root, f)[0] for f in files}
    edges, dynamic_notes = [], []
    for file in files:
        mod, is_pkg = module_name(src_root, file)
        collector = Collector(mod, is_pkg, known)
        collector.visit(ast.parse(file.read_text(encoding="utf-8"), filename=str(file)))
        for e in collector.edges:
            edges.append({"src": mod, **e})
        if collector.unresolved_dynamic:
            resolved = sorted(c for c in collector.string_constants if c in known)
            dynamic_notes.append((mod, collector.unresolved_dynamic, resolved))
            for target in resolved:
                edges.append({"src": mod, "line": collector.unresolved_dynamic[0], "form": "import_module(por constante)",
                              "scope": "função", "target": target, "symbols": []})

    for e in edges:
        e["src_pkg"], e["dst_pkg"], e["dst_kind"] = package_of(e["src"]), package_of(e["target"]), kind_of(e["target"])
        e["src_kind"] = kind_of(e["src"])

    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "grafo_imports_arestas.tsv").open("w", encoding="utf-8") as fh:
        fh.write("origem\tlinha\tforma\tescopo\tdestino\tpacote_origem\tpacote_destino\tsimbolos\n")
        for e in edges:
            fh.write(f"{e['src']}\t{e['line']}\t{e['form']}\t{e['scope']}\t{e['target']}\t{e['src_pkg']}\t{e['dst_pkg']}\t{', '.join(e['symbols'])}\n")

    internal = [e for e in edges if not e["dst_pkg"].startswith("ext:")]
    lines = ["# Grafo de imports — relatório gerado", "", f"Arquivos analisados: {len(files)}; arestas totais: {len(edges)}; internas: {len(internal)}.", ""]
    forms = collections.Counter(e["form"] for e in edges)
    lines += ["## Formas de import encontradas", "", "| Forma | Ocorrências |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in sorted(forms.items())]
    lines += ["", "Imports dentro de função:"]
    lines += [f"- `{e['src']}:{e['line']}` → `{e['target']}` ({e['form']})" for e in edges if e["scope"].startswith("função")]
    lines += ["", "Imports dinâmicos não literais (resolvidos por constantes do arquivo):"]
    lines += [f"- `{m}` linhas {ls}: {r}" for m, ls, r in dynamic_notes] or ["- nenhum"]

    # Arestas entre pacotes
    pkg_edges = collections.defaultdict(lambda: collections.defaultdict(set))
    for e in internal:
        if e["src_pkg"] != e["dst_pkg"]:
            pkg_edges[(e["src_pkg"], e["dst_pkg"])][e["target"]].add(f"{e['src'].split('.', 1)[-1]}:{e['line']}")
    lines += ["", "## Arestas entre pacotes (origem → destino: módulos-alvo e locais)", "", "| Origem | Destino | Módulos-alvo (locais) |", "|---|---|---|"]
    for (s, d), targets in sorted(pkg_edges.items()):
        detail = "; ".join(f"`{t}` ({', '.join(sorted(locs))})" for t, locs in sorted(targets.items()))
        lines.append(f"| {s} | {d} | {detail} |")

    # Regras
    rules = collections.defaultdict(list)
    for e in internal:
        s, d, sk, dk = e["src_pkg"], e["dst_pkg"], e["src_kind"], e["dst_kind"]
        where = f"`{e['src']}:{e['line']}` → `{e['target']}` [{e['form']}; {e['scope']}] {', '.join(e['symbols'])}"
        if s in BUSINESS and d in BUSINESS and s != d and dk != "public":
            rules["R1 negócio → interno de outro contexto de negócio (só `public` é permitido)"].append(where)
        if s in BUSINESS and d == "integration" and dk != "public":
            rules["R2 negócio → `integration` fora da fachada `integration.public` (ADR-005)"].append(where)
        if s == "integration" and d in BUSINESS:
            rules["R3 `integration` → contexto de negócio (direção invertida)"].append(where)
        if s == "raiz" and e["src"] != "archcorp.main" and d in CONTEXTS:
            rules["R4 núcleo da raiz (exceto `main.py`) → contexto (núcleo depende de contexto)"].append(where)
        if s == "infrastructure" and d in CONTEXTS:
            rules["R5 `infrastructure` → contexto (direção invertida)"].append(where)
        if e["src"] == "archcorp.main" and dk == "models":
            rules["R6 composição (`main.py`) → `models`"].append(where)
        if sk == "domain" and (d in ("infrastructure",) or dk in ("models", "routes", "service")):
            rules["R7 `domain.py` → infraestrutura/modelos/rotas/serviço"].append(where)
    for e in edges:
        if e["dst_pkg"].startswith("ext:") and e["src_kind"] == "domain" and e["dst_pkg"][4:] in FRAMEWORKS:
            rules["R7 `domain.py` → framework"].append(f"`{e['src']}:{e['line']}` → `{e['target']}`")
        if e["dst_pkg"].startswith("ext:") and e["src_kind"] == "service" and e["dst_pkg"][4:] in HTTP:
            rules["R8 `service.py` → HTTP (fastapi/starlette) direto"].append(f"`{e['src']}:{e['line']}` → `{e['target']}`")
    lines += ["", "## Regras de fronteira avaliadas", ""]
    for name in ["R1 negócio → interno de outro contexto de negócio (só `public` é permitido)",
                 "R2 negócio → `integration` fora da fachada `integration.public` (ADR-005)",
                 "R3 `integration` → contexto de negócio (direção invertida)",
                 "R4 núcleo da raiz (exceto `main.py`) → contexto (núcleo depende de contexto)",
                 "R5 `infrastructure` → contexto (direção invertida)",
                 "R6 composição (`main.py`) → `models`",
                 "R7 `domain.py` → infraestrutura/modelos/rotas/serviço", "R7 `domain.py` → framework",
                 "R8 `service.py` → HTTP (fastapi/starlette) direto"]:
        found = rules.get(name, [])
        lines.append(f"### {name}: {len(found)}")
        lines += [f"- {w}" for w in found] or ["- nenhuma"]
        lines.append("")

    # Framework direto por arquivo
    lines += ["## Dependências diretas de framework por módulo", "", "| Módulo | Frameworks |", "|---|---|"]
    per_mod = collections.defaultdict(set)
    for e in edges:
        if e["dst_pkg"].startswith("ext:") and e["dst_pkg"][4:] in FRAMEWORKS:
            per_mod[e["src"]].add(e["dst_pkg"][4:] + ("*" if e["scope"].startswith("função") else ""))
    for mod in sorted(known):
        lines.append(f"| `{mod}` | {', '.join(sorted(per_mod.get(mod, []))) or '—'} |")
    lines.append("\n`*` = import dentro de função.")

    # Grafo de módulos e transitividade
    graph = collections.defaultdict(set)
    for e in edges:
        if e["target"].startswith("archcorp"):
            target = e["target"]
            while target not in known and "." in target:
                target = target.rsplit(".", 1)[0]
            graph[e["src"]].add(target)
        else:
            graph[e["src"]].add(e["target"].split(".")[0])
    lines += ["", "## Dependências transitivas de framework (caminho mais curto) em `domain`, `service`, `public` e `adapters`", "",
              "| Módulo | fastapi | sqlalchemy | pika |", "|---|---|---|---|"]
    for mod in sorted(m for m in known if kind_of(m) in ("domain", "service", "public", "adapters")):
        cells = []
        for fw in ("fastapi", "sqlalchemy", "pika"):
            path = shortest_path(graph, mod, fw)
            cells.append(" → ".join(p.replace("archcorp.", "") for p in path) if path else "—")
        lines.append(f"| `{mod}` | {' | '.join(cells)} |")

    # Ciclos
    internal_graph = {m: {t for t in graph[m] if t.startswith("archcorp")} for m in known}
    module_cycles = tarjan(internal_graph)
    pkg_graph = collections.defaultdict(set)
    for m, targets in internal_graph.items():
        for t in targets:
            if package_of(m) != package_of(t):
                pkg_graph[package_of(m)].add(package_of(t))
    pkg_cycles = tarjan(dict(pkg_graph))
    lines += ["", "## Ciclos", "", f"Ciclos entre módulos (componentes fortemente conexos com mais de um módulo): {module_cycles or 'nenhum'}",
              "", f"Ciclos entre pacotes (raiz = arquivos de `src/archcorp/*.py`): {pkg_cycles or 'nenhum'}"]
    for comp in pkg_cycles:
        for a in comp:
            for b in comp:
                if b in pkg_graph.get(a, ()):
                    lines.append(f"- {a} → {b}")

    # Ca / Ce / I por pacote
    lines += ["", "## Acoplamento por pacote (Ca aferente, Ce eferente, I = Ce/(Ca+Ce))", "", "| Pacote | Ca | Ce | I |", "|---|---|---|---|"]
    for pkg in ("raiz",) + PACKAGES:
        ce = len({d for (s, d) in pkg_edges if s == pkg})
        ca = len({s for (s, d) in pkg_edges if d == pkg})
        inst = f"{ce / (ca + ce):.2f}" if ca + ce else "—"
        lines.append(f"| {pkg} | {ca} | {ce} | {inst} |")

    (out_dir / "grafo_imports_relatorio.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
