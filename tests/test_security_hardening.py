"""Endurecimento de métricas e exposição, sempre com dados sintéticos."""
import re
from uuid import uuid4

from archcorp.observability import COUNTERS, LATENCY_SUM, escape_label

SAMPLE = re.compile(r'^archcorp_[a-z_]+(\{([a-zA-Z_]+="(?:[^"\\\n]|\\.)*",?)*\})? -?[0-9.e+-]+$')
OPERATIONS = {"Authorization": "Bearer demo-operations"}


def test_caminhos_distintos_nao_criam_series_novas(client, admin_headers):
    client.get("/api/v1/crm/customers/00000000-0000-4000-8000-000000000000", headers=admin_headers)
    before = (len(COUNTERS), len(LATENCY_SUM))
    for _ in range(1000):
        client.get(f"/api/v1/crm/customers/{uuid4()}", headers=admin_headers)
        client.get(f"/sintetico/{uuid4()}")
    after = (len(COUNTERS), len(LATENCY_SUM))
    # Só as séries novas do template da rota inexistente/fallback, não uma por URL.
    assert after[0] - before[0] <= 3
    assert after[1] - before[1] <= 2
    text = client.get("/metrics", headers=OPERATIONS).text
    assert "GET_/api/v1/crm/customers/{customer_id}" in text
    assert "00000000-0000-4000-8000-000000000000" not in text


def test_metricas_exigem_papel_de_operacao(client):
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"Authorization": "Bearer demo-support"}).status_code == 403
    assert client.get("/metrics", headers=OPERATIONS).status_code == 200


def test_saida_de_metricas_valida_com_aspas_e_metodo_desconhecido(client):
    client.get('/api/v1/sintetico/"aspas"\\barra')
    client.request("SINTETICO", "/api/v1/crm/customers")
    response = client.get("/metrics", headers=OPERATIONS)
    lines = [line for line in response.text.splitlines() if line and not line.startswith("#")]
    assert lines
    assert all(SAMPLE.match(line) for line in lines), [line for line in lines if not SAMPLE.match(line)]
    assert "SINTETICO" not in response.text
    assert "aspas" not in response.text


def test_escape_de_rotulo_prometheus():
    assert escape_label('a"b\\c\nd') == 'a\\"b\\\\c\\nd'


def test_validacao_422_nao_ecoa_entrada_nem_contexto(client, admin_headers):
    marker = "sintetico-segredo-privado"
    response = client.post("/api/v1/crm/customers", headers=admin_headers,
                           json={"email": marker, "token": marker})
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["detail"] == body["errors"]
    assert marker not in response.text
    assert all(set(error) == {"type", "loc", "msg"} for error in body["errors"])
