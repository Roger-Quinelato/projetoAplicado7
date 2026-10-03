import ast, pathlib, collections
root = pathlib.Path("src/archcorp")
CTX = {"crm","contracts","finance","support","workflow","integration","infrastructure"}
def ctx_of(mod):
    parts = mod.split(".")
    if parts[0] != "archcorp": return None
    return parts[1] if len(parts)>1 else "archcorp"
edges = collections.defaultdict(set)
detail = []
for f in sorted(root.rglob("*.py")):
    if "migrations" in f.parts: continue
    rel = f.relative_to("src").with_suffix("")
    mod = ".".join(rel.parts)
    src_ctx = ctx_of(mod)
    tree = ast.parse(f.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("archcorp"):
            names = [a.name for a in node.names]
            tgt = node.module
            detail.append((mod, tgt, names, node.lineno))
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith("archcorp"): detail.append((mod, a.name, [], node.lineno))
        elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            pass
for mod, tgt, names, ln in detail:
    s, t = ctx_of(mod), ctx_of(tgt)
    if s != t:
        flag = ""
        if t in CTX and s in CTX and t not in ("infrastructure",) :
            flag = " <== CROSS-CONTEXT"
            if tgt.endswith(".models"): flag += " (MODELS)"
        if s in ("main","archcorp") and tgt.endswith(".models"): flag += " <== COMPOSICAO LE MODELS"
        print(f"{mod}:{ln} -> {tgt} {names}{flag}")
# framework deps
print("\n== dependencias de framework por arquivo ==")
for f in sorted(root.rglob("*.py")):
    if "migrations" in f.parts: continue
    t = f.read_text()
    deps = [d for d in ("fastapi","sqlalchemy","pika","pydantic") if f"from {d}" in t or f"import {d}" in t]
    print(f, deps)
