"""E-03 (Q-05 = AUD-20, Q-04 = AUD-21, AUD-41, baseline v1): valida os exemplos do OpenAPI e do AsyncAPI contra os
próprios esquemas (jsonschema 4.26 com FormatChecker), valida o envelope com causationId e confere valores monetários.
Não usa banco. Os YAML são lidos com timestamp tratado como texto (sem conversão automática para date)."""
import json
from datetime import date, datetime, timezone
from uuid import uuid4

from dad_common import CID, ISO, setup

setup("e03.db")
import yaml  # noqa: E402
from jsonschema import Draft202012Validator, FormatChecker  # noqa: E402
from referencing import Registry, Resource  # noqa: E402
from referencing.jsonschema import DRAFT202012  # noqa: E402

from archcorp.integration.models import OutboxEvent  # noqa: E402
from archcorp.main import app  # noqa: E402


def normaliza(valor):
    """Converte date/datetime (YAML sem aspas) de volta para texto ISO, como o contrato publica."""
    if isinstance(valor, dict):
        return {k: normaliza(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [normaliza(v) for v in valor]
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return valor


def load(path):
    return normaliza(yaml.safe_load((ISO / path).read_text(encoding="utf-8")))


def errors(doc, schema, uri, value):
    registry = Registry().with_resource(uri, Resource(contents=doc, specification=DRAFT202012))
    fixed = json.loads(json.dumps(schema).replace('"#/components', f'"{uri}#/components'))
    validator = Draft202012Validator(fixed, registry=registry, format_checker=FormatChecker())
    return [f"{'/'.join(str(p) for p in e.absolute_path)}: {e.message[:110]}" for e in validator.iter_errors(value)]


# ---------- OpenAPI ----------
oa = load("docs/api/openapi.yaml")
print("OpenAPI", oa["openapi"], "| artefato igual ao gerado pela aplicação:", oa == app.openapi())
checked, invalid = 0, []


def check(label, schema, value):
    global checked
    checked += 1
    errs = errors(oa, schema, "urn:oa", value)
    if errs:
        invalid.append((label, errs[:2]))


for path, ops in oa["paths"].items():
    for method, op in ops.items():
        if not isinstance(op, dict) or "responses" not in op:
            continue
        medias = [("req", mt, m) for mt, m in op.get("requestBody", {}).get("content", {}).items()]
        for status, resp in op["responses"].items():
            medias += [(status, mt, m) for mt, m in resp.get("content", {}).items()]
        for where, mt, media in medias:
            schema = media.get("schema")
            if not schema:
                continue
            exemplos = [("example", media["example"])] if "example" in media else []
            exemplos += [(nome, ex["value"]) for nome, ex in (media.get("examples") or {}).items()
                         if isinstance(ex, dict) and "value" in ex]
            for nome, value in exemplos:
                check(f"{method.upper()} {path} [{where} {mt}] {nome}", schema, value)
for nome, sch in oa["components"]["schemas"].items():
    for i, ex in enumerate(sch.get("examples") or []):
        check(f"componente {nome}.examples[{i}]", {"$ref": f"#/components/schemas/{nome}"}, ex)
print(f"OpenAPI: exemplos verificados={checked} invalidos={len(invalid)}")
for label, errs in invalid:
    print("  INVALIDO", label, errs)

# ---------- AsyncAPI ----------
aa = load("docs/events/asyncapi.yaml")
checked_a, invalid_a = 0, []
for nome, msg in aa["components"]["messages"].items():
    for ex in msg.get("examples", []):
        checked_a += 1
        errs = errors(aa, {"$ref": f"#/components/messages/{nome}/payload"}, "urn:aa", ex["payload"])
        if errs:
            invalid_a.append((f"{nome}/{ex['name']}", errs[:2]))
print(f"AsyncAPI: exemplos verificados={checked_a} invalidos={len(invalid_a)}", invalid_a)

payload_ex = aa["components"]["messages"]["ContractActivated"]["examples"][0]["payload"]["payload"]
for rotulo, causa in [("causationId=null", None), ("causationId=uuid", str(uuid4()))]:
    ev = OutboxEvent(event_id=str(uuid4()), event_type="ContractActivated.v1", event_version=1,
                     occurred_at=datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc), correlation_id=CID,
                     causation_id=causa, producer="contracts", payload=payload_ex)
    print("envelope", rotulo, "->",
          errors(aa, {"$ref": "#/components/messages/ContractActivated/payload"}, "urn:aa", ev.envelope()) or "válido")
for valor in [0.07, 19.99, 1234567.89, 2500.0, 100.1]:
    print(f"Money.amount={valor!r} ->",
          errors(aa, {"$ref": "#/components/schemas/Money"}, "urn:aa",
                 {"amount": valor, "currency": "BRL", "cycle": "ONCE"}) or "válido")

# ---------- Testes: uso de FormatChecker ----------
for arq in ["tests/test_contracts_and_architecture.py", "tests/test_t15_atendimento.py"]:
    txt = (ISO / arq).read_text(encoding="utf-8")
    print(arq, "| usa FormatChecker:", ("FormatChecker" in txt) or ("format_checker" in txt))

# ---------- Baseline v1: exceções e ADR ----------
base = json.loads((ISO / "tests/fixtures/api_v1_baseline.json").read_text(encoding="utf-8"))
adrs = {p.name: p.read_text(encoding="utf-8") for p in (ISO / "docs/adr").glob("ADR-*.md")}
marcas = {"InvoiceResponse.status": "PARTIALLY_PAID", "PaymentInput.amount": "duas casas"}
for chave in base["approved_ADR003"]:
    onde = [n for n, t in adrs.items() if marcas.get(chave, "\u0000") in t]
    print(f"baseline approved_ADR003 {chave}: ADR que registra a exceção = {onde or 'NENHUM'}")
for chave in base["approved_security"]:
    if chave.startswith("_"):
        continue
    caminho = chave.split(" ")[-1]
    onde = [n for n, t in adrs.items() if caminho in t]
    print(f"baseline approved_security {chave}: ADR que cita o caminho = {onde or 'NENHUM'}")
print("motivo registrado no baseline:", base["approved_security"].get("_motivo", "")[:120])
