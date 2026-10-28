"""F-QUA - o teste de contrato de eventos enxerga violacao de formato (date-time, uuid)?

Uso: python -I teste_cegueira_formato.py <ISO>
Usa docs/events/asyncapi.yaml da copia iso-qua. Replica o construtor de validador de
tests/test_contracts_and_architecture.py (asyncapi_validator, sem format_checker) e compara com
o mesmo payload validado com FormatChecker. Dois casos sinteticos: occurredAt sem 'Z' (AUD-41)
e occurredAt em formato invalido.
"""
import copy
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

root = Path(sys.argv[1])
document = yaml.safe_load((root / "docs" / "events" / "asyncapi.yaml").read_text(encoding="utf-8"))
URI = "urn:archcorp:asyncapi"
messages = {m["name"]: key for key, m in document["components"]["messages"].items()}
name = "ContractActivated.v1"
base = copy.deepcopy(document["components"]["messages"][messages[name]]["examples"][0]["payload"])
print(f"mensagem: {name}; occurredAt de exemplo: {base.get('occurredAt')}")


def validator(format_checker=None) -> Draft202012Validator:
    registry = Registry().with_resource(URI, Resource(contents=document, specification=DRAFT202012))
    schema = {"$ref": f"{URI}#/components/messages/{messages[name]}/payload"}
    return Draft202012Validator(schema, registry=registry, format_checker=format_checker)


cases = {
    "sem Z (AUD-41)": "2026-10-01T10:00:00",
    "data invalida": "nao-e-uma-data",
}
for label, value in cases.items():
    payload = copy.deepcopy(base)
    payload["occurredAt"] = value
    plain = [e.message for e in validator().iter_errors(payload)]
    checked = [e.message for e in validator(FormatChecker()).iter_errors(payload)]
    print(f"caso '{label}' ({value!r}):")
    print(f"  sem format_checker (como o teste): {len(plain)} erro(s) {plain[:2]}")
    print(f"  com FormatChecker: {len(checked)} erro(s) {checked[:2]}")
