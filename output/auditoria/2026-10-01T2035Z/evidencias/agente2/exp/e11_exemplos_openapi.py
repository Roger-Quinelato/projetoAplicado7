import yaml, json
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
SP="/tmp/claude-0/-home-user-projetoAplicado7/ec00d59b-c354-5d1f-b4d6-080b88ac1d06/scratchpad"
doc = yaml.safe_load(open(SP+"/iso/docs/api/openapi.yaml"))
print("openapi version:", doc["openapi"])
reg = Registry().with_resource("urn:o", Resource(contents=doc, specification=DRAFT202012))
def fix(schema):
    return json.loads(json.dumps(schema).replace('"#/components', '"urn:o#/components'))
bad = 0; total = 0
for path, ops in doc["paths"].items():
    for m, op in ops.items():
        items = []
        rb = op.get("requestBody", {}).get("content", {})
        for mt, media in rb.items():
            items.append(("request", mt, media))
        for st, resp in op.get("responses", {}).items():
            for mt, media in resp.get("content", {}).items():
                items.append((st, mt, media))
        for where, mt, media in items:
            sch = media.get("schema")
            if not sch: continue
            exs = []
            if "example" in media: exs.append(("example", media["example"]))
            for k, e in media.get("examples", {}).items(): exs.append((k, e.get("value")))
            # exemplos de componentes
            ref = sch.get("$ref") or sch.get("items", {}).get("$ref")
            if not exs and ref:
                comp = doc["components"]["schemas"][ref.split("/")[-1]]
                for i, e in enumerate(comp.get("examples", [])):
                    exs.append((f"component[{i}]", [e] if "items" in sch else e))
            v = Draft202012Validator(fix(sch), registry=reg)
            for name, val in exs:
                total += 1
                errs = [f"{'/'.join(map(str, e.absolute_path))}: {e.message[:90]}" for e in v.iter_errors(val)]
                if errs:
                    bad += 1
                    print(f"INVALIDO {m.upper()} {path} [{where} {mt}] exemplo={name}: {errs[:3]}")
print(f"exemplos verificados={total} invalidos={bad}")
