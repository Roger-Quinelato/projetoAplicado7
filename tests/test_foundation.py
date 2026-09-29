import importlib.util
from io import StringIO
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from archcorp.infrastructure.migrate import BASELINE_REVISION, alembic_config, load_models, upgrade_to_head

PROBLEM_FIELDS = {"type", "title", "status", "detail", "instance", "code", "correlationId"}


def assert_problem(response, status: int, code: str) -> dict:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert PROBLEM_FIELDS.issubset(body)
    assert body["status"] == status
    assert body["code"] == code
    assert body["type"] == "urn:archcorp:problem:" + code.lower().replace("_", "-")
    assert body["correlationId"] == response.headers["X-Correlation-ID"]
    return body


def test_contrato_de_erro_problem_json_para_status_comuns(client, admin_headers):
    bad_header = client.get("/api/v1/crm/customers", headers={**admin_headers, "X-Correlation-ID": "nao-uuid"})
    assert_problem(bad_header, 400, "BAD_REQUEST")

    assert_problem(client.get("/api/v1/crm/customers"), 401, "UNAUTHORIZED")
    assert_problem(client.post("/api/v1/integration/outbox/dispatch", headers={"Authorization": "Bearer demo-commercial"}), 403, "FORBIDDEN")

    missing = client.post(f"/api/v1/contracts/{'b' * 8}-bbbb-4bbb-8bbb-{'b' * 12}/activate",
                          headers={**admin_headers, "Idempotency-Key": "missing"})
    body = assert_problem(missing, 404, "NOT_FOUND")
    assert body["detail"] == "Contrato não encontrado"
    assert body["correlationId"] == admin_headers["X-Correlation-ID"]
    assert body["instance"].endswith("/activate")

    invalid = client.post("/api/v1/crm/customers", headers=admin_headers, json={"name": "X", "email": "inválido"})
    body = assert_problem(invalid, 422, "VALIDATION_ERROR")
    assert body["errors"] == body["detail"]
    assert {tuple(error["loc"]) for error in body["errors"]} == {("body", "name"), ("body", "email")}


def test_conflitos_de_unicidade_retornam_409_e_nao_500(client, admin_headers):
    first = client.post("/api/v1/crm/customers", headers=admin_headers,
                        json={"name": "Empresa Única", "email": "unica@example.com", "legacyId": "SINT-1"})
    assert first.status_code == 201
    duplicate_email = client.post("/api/v1/crm/customers", headers=admin_headers,
                                  json={"name": "Outra Empresa", "email": "unica@example.com"})
    assert assert_problem(duplicate_email, 409, "CONFLICT")["detail"] == "E-mail já cadastrado no CRM"
    duplicate_legacy = client.post("/api/v1/crm/customers", headers=admin_headers,
                                   json={"name": "Outra Empresa", "email": "outra@example.com", "legacyId": "SINT-1"})
    assert_problem(duplicate_legacy, 409, "CONFLICT")

    other = client.post("/api/v1/crm/customers", headers=admin_headers,
                        json={"name": "Terceira Empresa", "email": "terceira@example.com"}).json()
    patch = client.patch(f"/api/v1/crm/customers/{other['customerId']}", headers=admin_headers, json={"email": "unica@example.com"})
    assert_problem(patch, 409, "CONFLICT")


def test_idempotency_key_reutilizada_retorna_codigo_especifico(client, admin_headers, integrated_contract):
    customer, _ = integrated_contract
    response = client.post("/api/v1/contracts/drafts", headers={**admin_headers, "Idempotency-Key": "draft-1"}, json={
        "customerId": customer["customerId"], "serviceCode": "RENTAL-FLEX", "startsOn": "2026-11-01",
        "billing": {"amount": 2500, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8,
    })
    assert_problem(response, 409, "IDEMPOTENCY_CONFLICT")


def test_identificador_legado_resolve_uuid_global(client, admin_headers, integrated_contract):
    customer, _ = integrated_contract
    assert customer["legacyId"] == "CRM-1"
    resolved = client.get("/api/v1/integration/legacy-ids/CRM/CRM-1", headers=admin_headers)
    assert resolved.status_code == 200
    assert resolved.json() == {"entityType": "customer", "globalId": customer["customerId"], "sourceSystem": "CRM", "legacyId": "CRM-1"}
    assert client.get(f"/api/v1/crm/customers/{customer['customerId']}", headers=admin_headers).json()["legacyId"] == "CRM-1"
    assert_problem(client.get("/api/v1/integration/legacy-ids/CRM/CRM-404", headers=admin_headers), 404, "NOT_FOUND")
    assert client.get("/api/v1/integration/legacy-ids/CRM/CRM-1", headers={"Authorization": "Bearer demo-finance"}).status_code == 403


def test_migracoes_criam_esquema_sem_divergencia_dos_modelos(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'migracao.db'}")
    with engine.begin() as connection:
        upgrade_to_head(connection)
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), load_models().metadata)
        tables = set(inspect(connection).get_table_names())
    assert diff == []
    assert {"alembic_version", "crm_customers", "contracts_contracts", "integration_outbox"}.issubset(tables)


def test_banco_criado_por_create_all_recebe_carimbo_de_head(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'atual.db'}")
    load_models().metadata.create_all(engine)
    with engine.begin() as connection:
        upgrade_to_head(connection)
    with engine.connect() as connection:
        revision = MigrationContext.configure(connection).get_current_revision()
    assert revision == ScriptDirectory.from_config(alembic_config()).get_current_head()


def test_banco_com_esquema_antigo_recebe_migracoes_seguintes(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'antigo.db'}")
    with engine.begin() as connection:
        command.upgrade(alembic_config(connection), BASELINE_REVISION)
        connection.exec_driver_sql("DROP TABLE alembic_version")
    with engine.begin() as connection:
        upgrade_to_head(connection)
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), load_models().metadata)
        columns = {column["name"] for column in inspect(connection).get_columns("crm_customers")}
    assert diff == []
    assert "active" in columns


def test_migracoes_geram_sql_valido_para_postgresql():
    config = alembic_config()
    config.set_main_option("sqlalchemy.url", "postgresql+psycopg://migracao@localhost/archcorp")
    config.output_buffer = StringIO()
    command.upgrade(config, "head", sql=True)
    sql = config.output_buffer.getvalue()
    assert "CREATE TABLE crm_customers" in sql
    assert "ALTER TABLE crm_customers ADD COLUMN active BOOLEAN DEFAULT true NOT NULL" in sql


def test_migracoes_sao_aditivas():
    versions = Path("src/archcorp/infrastructure/migrations/versions")
    forbidden = ("drop_table", "drop_column", "alter_column(", "rename_table")
    for file in versions.glob("*.py"):
        upgrade = file.read_text(encoding="utf-8").split("def downgrade", 1)[0]
        assert not any(term in upgrade for term in forbidden), f"{file.name} contém operação destrutiva no upgrade"


def test_carga_sintetica_e_idempotente(client):
    spec = importlib.util.spec_from_file_location("seed_sintetico", "scripts/seed_sintetico.py")
    seed_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed_module)
    first = seed_module.seed(client, "demo-admin")
    second = seed_module.seed(client, "demo-admin")
    assert first["customersCreated"] == 3
    assert second["customersCreated"] == 0
    assert first["customers"] == second["customers"]
    assert first["contracts"] == second["contracts"]
    emails = [item["email"] for item in seed_module.CUSTOMERS]
    assert all(email.split("@")[1].split(".")[-2] == "example" for email in emails)
