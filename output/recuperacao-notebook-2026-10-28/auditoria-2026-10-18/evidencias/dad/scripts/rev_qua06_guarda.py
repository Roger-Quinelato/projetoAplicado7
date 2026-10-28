"""Revisão cruzada de QUA-06 (independente): a guarda de inicialização do modo público (main.py:69-70) dispara?"""
from dad_common import setup

setup("rev_qua06.db")
from fastapi.testclient import TestClient  # noqa: E402

from archcorp.config import settings  # noqa: E402
from archcorp.main import app  # noqa: E402

publico_original, token_original = settings.public_demo, settings.demo_access_token
casos = {
    "PUBLIC_DEMO sem token": (True, None),
    "token curto (17 caracteres)": (True, "curto-0123456789"),
    "token com prefixo demo-": (True, "demo-" + "x" * 30),
    "token válido (>= 24, sem demo-)": (True, "segredo-aleatorio-0123456789ABCDEF"),
}
try:
    for nome, (publico, token) in casos.items():
        settings.public_demo, settings.demo_access_token = publico, token
        try:
            with TestClient(app) as c:
                resultado = f"inicia, /health/live={c.get('/health/live').status_code}"
        except RuntimeError as exc:
            resultado = f"RuntimeError: {str(exc)[:60]}"
        print(f"{nome}: {resultado}")
finally:
    settings.public_demo, settings.demo_access_token = publico_original, token_original
