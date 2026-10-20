"""Prontidão: banco obrigatório e listener AMQP informativo (plano de conclusão, pacote F; #62)."""
import time

from archcorp.config import settings


def test_sem_broker_configurado_a_prontidao_nao_menciona_broker(client, monkeypatch):
    monkeypatch.setattr(settings, "rabbitmq_url", None)
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "UP", "database": "UP"}


def test_broker_inalcancavel_aparece_como_down_sem_derrubar_a_api(client, monkeypatch):
    # Porta fechada: o listener AMQP não aceita conexão, como no RabbitMQ que ainda está subindo.
    monkeypatch.setattr(settings, "rabbitmq_url", "amqp://guest:guest@127.0.0.1:1/%2F")
    started = time.monotonic()
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "UP", "database": "UP", "broker": "DOWN"}
    assert time.monotonic() - started < settings.rabbitmq_health_timeout_seconds + 2
