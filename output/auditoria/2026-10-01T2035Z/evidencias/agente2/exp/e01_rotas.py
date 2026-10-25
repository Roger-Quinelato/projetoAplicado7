import yaml, json
from harness import *
from fastapi.routing import APIRoute
doc = yaml.safe_load(open(SP/"iso/docs/api/openapi.yaml"))
real = {}
for r in app.routes:
    if isinstance(r, APIRoute) and r.include_in_schema:
        for m in r.methods:
            real[(m.lower(), r.path)] = r.status_code
docops = {(m, p) for p, ops in doc["paths"].items() for m in ops if m in ("get","post","put","patch","delete")}
print("rotas reais:", len(real), "operacoes no openapi.yaml:", len(docops))
print("so no codigo:", sorted(set(real) - docops))
print("so no doc:", sorted(docops - set(real)))
gen = app.openapi()
print("openapi gerado == salvo:", gen == doc)
# rotas sem Idempotency-Key entre comandos POST/PATCH/DELETE
for (m,p),sc in sorted(real.items()):
    if m in ("post","patch","delete"):
        params = [x["name"] for x in gen["paths"][p][m].get("parameters",[])]
        idem = [x for x in params if x=="Idempotency-Key"]
        req = [x.get("required") for x in gen["paths"][p][m].get("parameters",[]) if x["name"]=="Idempotency-Key"]
        print(f"{m.upper():6} {p:60} status={sc} Idempotency-Key={'sim' if idem else 'nao'} required={req} responses={sorted(gen['paths'][p][m]['responses'])}")
