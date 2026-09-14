import os

os.environ["DATABASE_URL"] = "sqlite:///./tmp/test-archcorp.db"
os.environ.pop("RABBITMQ_URL", None)

import pytest
from fastapi.testclient import TestClient

from archcorp.infrastructure.db import Base, engine
from archcorp.main import app


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_headers():
    return {"Authorization": "Bearer demo-admin", "X-Correlation-ID": "11111111-1111-4111-8111-111111111111"}


@pytest.fixture
def integrated_contract(client, admin_headers):
    customer = client.post("/api/v1/crm/customers", headers=admin_headers, json={"name": "Empresa Teste", "email": "teste@example.com", "legacyId": "CRM-1"}).json()
    headers = {**admin_headers, "Idempotency-Key": "draft-1"}
    contract = client.post("/api/v1/contracts/drafts", headers=headers, json={
        "customerId": customer["customerId"], "serviceCode": "SUPPORT-PREMIUM", "startsOn": "2026-10-01",
        "billing": {"amount": 2500, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8,
    }).json()
    return customer, contract
