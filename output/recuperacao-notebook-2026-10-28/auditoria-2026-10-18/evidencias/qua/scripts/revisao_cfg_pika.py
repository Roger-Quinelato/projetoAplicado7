"""F-QUA - revisao da CFG-01: os limites RABBITMQ_* negativos sao recusados pelo pika na atribuicao?

Uso: python -I revisao_cfg_pika.py <ISO>\\src
Atribui os valores de integration/service.py:117-120 a URLParameters, sem abrir conexao (nenhum broker).
"""
import sys

sys.path.insert(0, sys.argv[1])
import pika  # noqa: E402  (dependencia ja instalada no venv-auditoria; nada e instalado)

for name, value in [("socket_timeout", -1), ("blocked_connection_timeout", -1), ("heartbeat", -1),
                    ("socket_timeout", 0), ("heartbeat", 0)]:
    parameters = pika.URLParameters("amqp://guest:guest@127.0.0.1:1/%2F")
    try:
        setattr(parameters, name, value)
        outcome = f"aceito, valor={getattr(parameters, name)!r}"
    except Exception as exc:  # noqa: BLE001
        outcome = f"{type(exc).__name__}: {exc}"
    print(f"{name}={value!r}: {outcome}")
