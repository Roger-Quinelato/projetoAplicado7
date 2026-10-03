"""Replica a logica de deteccao dos testes de arquitetura (tests/test_contracts_and_architecture.py:90-115)
sobre trechos sinteticos, para mostrar o que passa sem ser detectado. Nao executa a suite."""
import ast
contexts = {"crm", "contracts", "finance", "support", "workflow"}
def main_rule(src):  # test_composicao_da_aplicacao_nao_le_modelos_dos_contextos
    tree = ast.parse(src)
    return [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("archcorp.") and n.module.endswith(".models") and n.module.split(".")[1] in contexts]
def ctx_rule(src, context):  # test_modulos_de_negocio_nao_importam_models_de_outro_contexto
    v = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            if len(parts) >= 3 and parts[0] == "archcorp" and parts[1] in contexts - {context} and parts[2] == "models":
                v.append(node.module)
    return v
casos = {
  "from archcorp.crm.models import Customer": "detectado esperado",
  "from archcorp.crm import models": "forma alternativa",
  "import archcorp.crm.models": "import absoluto",
  "import archcorp.crm.models as m": "import com alias",
  "from archcorp.integration.models import OutboxEvent": "modelo interno de Integration",
  "from archcorp.crm.service import CustomerService\nCustomerService().require(s, 'x').email": "classe interna (service) de outro contexto",
  "from sqlalchemy import text\ns.execute(text('select * from crm_customers'))": "SQL direto na tabela de outro contexto",
  "from archcorp.infrastructure.db import Base\nBase.metadata.tables['crm_customers']": "tabela via metadata",
}
for src, desc in casos.items():
    print(f"{desc:45} | main.py -> {'VIOLACAO' if main_rule(src) else 'passa'} | contracts/*.py -> {'VIOLACAO' if ctx_rule(src, 'contracts') else 'passa'}")
