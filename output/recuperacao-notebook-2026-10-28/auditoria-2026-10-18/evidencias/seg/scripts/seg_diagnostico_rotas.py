# -*- coding: utf-8 -*-
"""F-SEG, diagnóstico da enumeração de app.routes usada pela matriz E-09 (somente leitura).

No FastAPI 0.143 as rotas de include_router ficam em objetos _IncludedRouter (original_router).
Este script descreve caminhos efetivos, prefixos e candidatos, para que a matriz enumere todas
as operações com o caminho completo e as dependências corretas.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ISO = r"C:\Users\roger\.claude\jobs\f5019419\tmp\iso-seg"
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(ISO, "tmp", "diagnostico_rotas.db").replace("\\", "/")
for variavel in ("PUBLIC_DEMO", "DEMO_ACCESS_TOKEN", "RABBITMQ_URL"):
    os.environ.pop(variavel, None)
sys.path.insert(0, os.path.join(ISO, "src"))

from archcorp.main import app  # noqa: E402

incluidos = [r for r in app.routes if type(r).__name__ == "_IncludedRouter"]
primeiro = incluidos[0]
ctx = primeiro.include_context
print("include_context tipo:", type(ctx).__name__, "| atributos:", sorted(a for a in vars(ctx).keys())[:20] if hasattr(ctx, "__dict__") else dir(ctx)[:20])
print("original_router.prefix:", getattr(primeiro.original_router, "prefix", None))
print("rotas em original_router:", len(primeiro.original_router.routes))
print("primeiras (path, metodos):", [(getattr(x, "path", None), sorted(getattr(x, "methods", []) or [])) for x in primeiro.original_router.routes[:3]])
cand = getattr(primeiro, "_effective_candidates", None)
print("_effective_candidates tipo:", type(cand).__name__, "| len:", len(cand) if cand is not None else None)
if cand:
    item = cand[0] if isinstance(cand, (list, tuple)) else next(iter(cand.values()))
    print("item candidato tipo:", type(item).__name__, "| atributos:", sorted(vars(item).keys())[:25] if hasattr(item, "__dict__") else None)
print("app.openapi paths (amostra):", list(app.openapi()["paths"].keys())[:5])
