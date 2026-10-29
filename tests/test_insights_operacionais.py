"""Informação operacional a partir de logs, métricas e auditoria, sempre com dados sintéticos."""
import logging
import re

from archcorp.observability import LATENCY_BUCKETS

OPERATIONS = {"Authorization": "Bearer demo-operations"}


def activate_and_dispatch(client, admin_headers, integrated_contract):
    _customer, contract = integrated_contract
    client.post(f"/api/v1/contracts/{contract['contractId']}/activate", headers={**admin_headers, "Idempotency-Key": "insights-activate"})
    client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers)
    return contract


def test_insights_consolidam_eventos_atraso_e_auditoria(client, admin_headers, integrated_contract):
    activate_and_dispatch(client, admin_headers, integrated_contract)
    response = client.get("/api/v1/integration/insights", headers=OPERATIONS)
    assert response.status_code == 200, response.text
    body = response.json()

    events = {item["eventType"]: item for item in body["events"]}
    activated = events["ContractActivated.v1"]
    assert (activated["total"], activated["published"], activated["pending"], activated["failed"]) == (1, 1, 0, 0)
    assert activated["retried"] == 0

    lag = {item["consumer"]: item for item in body["dispatchLag"]}
    for consumer in ("finance", "workflow-preparacao-retirada"):
        assert lag[consumer]["processed"] == 1
        assert 0 <= lag[consumer]["p50Seconds"] <= lag[consumer]["p95Seconds"] <= lag[consumer]["maxSeconds"]

    modules = {item["module"] for item in body["audit"]}
    assert {"crm", "contracts"} <= modules
    assert all(item["count"] >= 1 for item in body["audit"])
    assert body["idempotencyKeys"]


def test_insights_exigem_papel_de_operacao(client):
    assert client.get("/api/v1/integration/insights").status_code == 401
    assert client.get("/api/v1/integration/insights", headers={"Authorization": "Bearer demo-support"}).status_code == 403


def sample(text: str, series: str) -> int:
    """Valor de uma série do /metrics; 0 se ainda não existir (as métricas são do processo)."""
    match = re.search(rf"^{re.escape(series)} (\d+)$", text, re.MULTILINE)
    return int(match.group(1)) if match else 0


def test_metricas_trazem_histograma_codigos_de_erro_e_replays(client, admin_headers, integrated_contract):
    _customer, contract = integrated_contract
    operation = 'operation="POST_/api/v1/contracts/{contract_id}/activate"'
    count = f"archcorp_request_latency_seconds_count{{{operation}}}"
    infinite = f'archcorp_request_latency_seconds_bucket{{{operation},le="+Inf"}}'
    not_found = 'archcorp_problems_total{status="404",code="NOT_FOUND"}'
    replays = 'archcorp_idempotency_replays_total{operation="activate_contract"}'
    before = client.get("/metrics", headers=OPERATIONS).text

    headers = {**admin_headers, "Idempotency-Key": "insights-replay"}
    client.post(f"/api/v1/contracts/{contract['contractId']}/activate", headers=headers)
    assert client.post(f"/api/v1/contracts/{contract['contractId']}/activate", headers=headers).headers["Idempotency-Replayed"] == "true"
    client.get("/api/v1/contracts/99999999-9999-4999-8999-999999999999", headers=admin_headers)

    after = client.get("/metrics", headers=OPERATIONS).text
    assert sample(after, count) - sample(before, count) == 2
    assert sample(after, infinite) == sample(after, count)
    assert len([line for line in after.splitlines() if line.startswith("archcorp_request_latency_seconds_bucket{" + operation)]) == len(LATENCY_BUCKETS) + 1
    assert sample(after, not_found) - sample(before, not_found) == 1
    assert sample(after, replays) - sample(before, replays) == 1


def test_log_de_requisicao_usa_o_template_da_rota(client, admin_headers, caplog):
    with caplog.at_level(logging.INFO, logger="archcorp"):
        client.get("/api/v1/crm/customers/00000000-0000-4000-8000-000000000000", headers=admin_headers)
    operations = [getattr(record, "operation", "") for record in caplog.records if record.getMessage() == "Requisição concluída"]
    assert "GET_/api/v1/crm/customers/{customer_id}" in operations
    assert all("00000000-0000-4000-8000-000000000000" not in operation for operation in operations)
