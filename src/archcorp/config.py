from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./archcorp.db"
    rabbitmq_url: str | None = None
    # Limites da cópia no broker: o despacho segura o bloqueio do evento enquanto publica.
    rabbitmq_blocked_timeout_seconds: float = 10.0
    rabbitmq_socket_timeout_seconds: float = 5.0
    rabbitmq_heartbeat_seconds: int = 30
    rabbitmq_queue_max_length: int = 10000
    contract_adapter_available: bool = True
    # Simulação local: permite data de referência futura na verificação de vencimento (T12).
    finance_allow_future_as_of: bool = False
    retry_limit: int = 3
    public_demo: bool = False
    demo_access_token: str | None = None


settings = Settings()
