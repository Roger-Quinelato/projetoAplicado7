"""Revisão cruzada de QUA-04 (independente): a validação AsyncAPI com e sem FormatChecker aceita data sem fuso?"""
import re

import yaml

from dad_common import ISO, setup

setup("rev_qua04.db")
from jsonschema import Draft202012Validator, FormatChecker  # noqa: E402
from referencing import Registry, Resource  # noqa: E402
from referencing.jsonschema import DRAFT202012  # noqa: E402

doc = yaml.safe_load((ISO / "docs/events/asyncapi.yaml").read_text(encoding="utf-8"))
base = doc["components"]["messages"]["TicketOpened"]["examples"][0]["payload"]
registry = Registry().with_resource("urn:aa", Resource(contents=doc, specification=DRAFT202012))


def erros(envelope, com_formato):
    validador = Draft202012Validator({"$ref": "urn:aa#/components/messages/TicketOpened/payload"},
                                     registry=registry, format_checker=FormatChecker() if com_formato else None)
    return [e.message[:70] for e in validador.iter_errors(envelope)]


caso_occurred = {**base, "occurredAt": "2026-10-01T10:00:00"}
caso_due = {**base, "payload": {**base["payload"], "dueAt": "2026-10-01T18:10:00"}}
for rotulo, env in [("occurredAt sem fuso", caso_occurred), ("dueAt sem fuso", caso_due)]:
    print(f"{rotulo}: sem FormatChecker={erros(env, False) or 'aceito'} | com FormatChecker={erros(env, True) or 'aceito'}")
teste = (ISO / "tests/test_contracts_and_architecture.py").read_text(encoding="utf-8")
print("teste de envelope cita dueAt:", "dueAt" in teste, "| assert endswith('Z') presente:", bool(re.search(r"endswith\(\"Z\"\)", teste)))
print("validador do teste usa format_checker:", "format_checker" in teste)
