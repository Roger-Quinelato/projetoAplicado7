import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from archcorp.config import settings
from archcorp.main import app
from archcorp.security import current_principal


@pytest.mark.parametrize("token", [None, "short", "demo-" + "x" * 30])
def test_demo_publica_recusa_configuracao_insegura(monkeypatch, token):
    monkeypatch.setattr(settings, "public_demo", True)
    monkeypatch.setattr(settings, "demo_access_token", token)
    with pytest.raises(RuntimeError, match="PUBLIC_DEMO exige"):
        with TestClient(app):
            pass


def test_credencial_unicode_invalida_retorna_401(monkeypatch):
    monkeypatch.setattr(settings, "public_demo", True)
    monkeypatch.setattr(settings, "demo_access_token", "synthetic-token-for-test-only-123")
    with pytest.raises(HTTPException) as caught:
        current_principal(HTTPAuthorizationCredentials(scheme="Bearer", credentials="inválido"))
    assert caught.value.status_code == 401
