"""F-QUA - revisao cruzada da F-CFG: verificacoes baratas e independentes, em SQLite, sem Docker,
PostgreSQL ou RabbitMQ. Um processo por caso; as variaveis de ambiente sao definidas antes do import.

Uso: python -I revisao_cfg_checks.py <ISO>\\src <ISO>\\tmp <CASO>
Casos: crm-timeout-neg, crm-delay-neg, crm-attempts-zero, crm-default, retry-zero,
       settings-assign, public-sqlite, dev-default.
Os bancos sao arquivos SQLite em <ISO>\\tmp (cópia descartável), nunca o banco persistente.
"""
import os
import sys
import time
from pathlib import Path

SRC, TMP, CASE = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
sys.path.insert(0, SRC)

db_file = TMP / f"revisao_cfg_{CASE}.db"
for suffix in ("", "-journal"):
    leftover = Path(str(db_file) + suffix)
    if leftover.exists():
        leftover.unlink()
os.environ["DATABASE_URL"] = "sqlite:///" + db_file.as_posix()

ENV = {
    "crm-timeout-neg": {"CRM_READER_TIMEOUT_SECONDS": "-1"},
    "crm-delay-neg": {"CRM_READER_BASE_DELAY_SECONDS": "-1"},
    "crm-attempts-zero": {"CRM_READER_MAX_ATTEMPTS": "0"},
    "crm-default": {},
    "retry-zero": {"RETRY_LIMIT": "0"},
    "settings-assign": {},
    "public-sqlite": {"PUBLIC_DEMO": "true", "DEMO_ACCESS_TOKEN": "segredo-sintetico-revisao-0123456789"},
    "dev-default": {},
}
os.environ.update(ENV[CASE])

from archcorp.config import settings  # noqa: E402  (import depois do ambiente, como na aplicacao)

if CASE in ("crm-timeout-neg", "crm-delay-neg", "crm-attempts-zero", "crm-default"):
    from archcorp.contracts.adapters import ResilientCustomerReader

    class Inner:
        calls = 0

        def get(self, session, customer_id):
            Inner.calls += 1
            raise TimeoutError("falha transitoria sintetica")

    sleeps: list[float] = []

    def recording_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        time.sleep(seconds)  # o time.sleep real, como em main.py (sleep padrao)

    try:
        reader = ResilientCustomerReader(
            Inner(), timeout_seconds=settings.crm_reader_timeout_seconds,
            max_attempts=settings.crm_reader_max_attempts,
            base_delay_seconds=settings.crm_reader_base_delay_seconds, sleep=recording_sleep)
        reader.get(None, "cliente-sintetico")
        outcome = "retornou"
    except Exception as exc:  # noqa: BLE001 - o caso registra o tipo que sobe
        outcome = f"{type(exc).__name__}: {str(exc)[:100]}"
    print(f"caso={CASE} timeout={settings.crm_reader_timeout_seconds} max_attempts={settings.crm_reader_max_attempts} "
          f"base_delay={settings.crm_reader_base_delay_seconds}")
    print(f"  chamadas_ao_crm={Inner.calls} esperas={[round(s, 3) for s in sleeps]} resultado={outcome}")

elif CASE == "retry-zero":
    from archcorp.integration.service import EventDispatcher

    class Event:
        attempts = 0
        last_error = None
        status = "PENDING"

    event = Event()
    EventDispatcher._register_failure(event)  # metodo real do despachante (service.py:92-96)
    print(f"caso=retry-zero RETRY_LIMIT={settings.retry_limit} apos_1_falha: attempts={event.attempts} status={event.status}")

elif CASE == "settings-assign":
    try:
        settings.retry_limit = "abc"
        outcome = f"aceito; valor guardado={settings.retry_limit!r}"
    except Exception as exc:  # noqa: BLE001
        outcome = f"{type(exc).__name__}: {exc}"
    print(f"caso=settings-assign retry_limit='abc': {outcome}")
    print(f"  validate_assignment={settings.model_config.get('validate_assignment')}")

elif CASE == "public-sqlite":
    import archcorp.main as main_module
    from fastapi.testclient import TestClient

    calls: list[str] = []
    original = main_module.protect_public_demo_tables

    def spy(connection):
        calls.append(connection.dialect.name)
        return original(connection)

    main_module.protect_public_demo_tables = spy  # o lifespan chama o nome do modulo
    with TestClient(main_module.app) as client:
        live = client.get("/health/live").status_code
        ready = client.get("/health/ready").status_code
        public_token = client.get("/api/v1/demo/state",
                                  headers={"Authorization": f"Bearer {ENV[CASE]['DEMO_ACCESS_TOKEN']}"}).status_code
    print(f"caso=public-sqlite public_demo={settings.public_demo} dialeto={main_module.engine.dialect.name}")
    print(f"  startup concluido; /health/live={live} /health/ready={ready}; token publico em /api/v1/demo/state={public_token}")
    print(f"  protect_public_demo_tables chamada {len(calls)}x com dialetos={calls}")

elif CASE == "dev-default":
    import archcorp.main as main_module
    from fastapi.testclient import TestClient

    with TestClient(main_module.app) as client:
        admin_state = client.get("/api/v1/demo/state", headers={"Authorization": "Bearer demo-admin"}).status_code
        admin_metrics = client.get("/metrics", headers={"Authorization": "Bearer demo-admin"}).status_code
        anon_state = client.get("/api/v1/demo/state").status_code
        anon_metrics = client.get("/metrics").status_code
    print(f"caso=dev-default public_demo={settings.public_demo} sem variaveis de demonstracao")
    print(f"  demo-admin: /api/v1/demo/state={admin_state} /metrics={admin_metrics}; "
          f"sem token: /api/v1/demo/state={anon_state} /metrics={anon_metrics}")
